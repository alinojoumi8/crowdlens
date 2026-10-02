"""
Task Status Management
Tracks long-running tasks (like graph building)
"""

import os
import uuid
import threading
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

from ..utils.logger import get_logger


logger = get_logger('mirofish.task')


class TaskStatus(str, Enum):
    """Task status enumeration"""
    PENDING = "pending"          # Pending
    PROCESSING = "processing"    # Processing
    COMPLETED = "completed"      # Completed
    FAILED = "failed"            # Failed


@dataclass
class Task:
    """Task data class"""
    task_id: str
    task_type: str
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    progress: int = 0              # Overall progress percentage 0-100
    message: str = ""              # Status message
    result: Optional[Dict] = None  # Task result
    error: Optional[str] = None    # Error message
    metadata: Dict = field(default_factory=dict)  # Additional metadata
    progress_detail: Dict = field(default_factory=dict)  # Detailed progress information
    execution: Optional[Dict] = None
    recovery: Optional[Dict] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "progress": self.progress,
            "message": self.message,
            "progress_detail": self.progress_detail,
            "result": self.result,
            "error": self.error,
            "metadata": self.metadata,
            "execution": self.execution,
            "recovery": self.recovery,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        return cls(
            task_id=data['task_id'],
            task_type=data['task_type'],
            status=TaskStatus(data.get('status', TaskStatus.PENDING.value)),
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at']),
            progress=int(data.get('progress', 0)),
            message=data.get('message', ''),
            result=data.get('result'),
            error=data.get('error'),
            metadata=data.get('metadata') or {},
            progress_detail=data.get('progress_detail') or {},
            execution=data.get('execution'), recovery=data.get('recovery'),
        )


class TaskManager:
    """
    Task Manager
    Thread-safe task status management
    """

    _instance = None
    _lock = threading.Lock()
    _repository = None
    _runtime = None

    @classmethod
    def configure_repository(cls, repository) -> None:
        if cls._runtime:
            cls._runtime.close()
        cls._runtime = None
        cls._repository = repository
        if cls._instance:
            cls._instance._tasks.clear()

    def __new__(cls):
        """Singleton pattern"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._tasks: Dict[str, Task] = {}
                    cls._instance._task_lock = threading.Lock()
        return cls._instance

    @property
    def runtime(self):
        from ..services.task_execution import TaskRuntime
        if (type(self)._runtime is None or type(self)._runtime.repository is not self._repository
                or type(self)._runtime.owner['pid'] != os.getpid()):
            if type(self)._runtime:
                type(self)._runtime.close()
            type(self)._runtime = TaskRuntime(self._repository)
        return type(self)._runtime

    def attempt(self, task_id):
        from ..services.task_execution import current_attempt, OwnershipLost
        current = current_attempt()
        if current and current.task_id == task_id:
            return current
        handle = self.runtime.handles.get(task_id)
        if handle is None:
            raise OwnershipLost('task_not_owned_by_this_worker')
        return handle

    def start_task(self, task_id, target, args=(), *, name=None):
        attempt = self.attempt(task_id)
        return attempt.runtime.start(attempt, target, args, name=name)

    def reconcile(self):
        return self.runtime.reconcile(raise_on_error=False)

    def create_task(self, task_type: str, metadata: Optional[Dict] = None, *, resources=()) -> str:
        """
        Create new task

        Args:
            task_type: Task type
            metadata: Additional metadata

        Returns:
            Task ID
        """
        task_id = str(uuid.uuid4())
        now = datetime.now()

        task = Task(
            task_id=task_id,
            task_type=task_type,
            status=TaskStatus.PENDING,
            created_at=now,
            updated_at=now,
            metadata=metadata or {}
        )

        with self._task_lock:
            self._tasks[task_id] = task
        self.runtime.admit(task.to_dict(), resources)

        metadata_keys = ",".join(sorted((metadata or {}).keys())) or "-"
        logger.info(
            "Task created: task_id=%s task_type=%s metadata_keys=%s",
            task_id,
            task_type,
            metadata_keys,
        )

        return task_id

    def get_task(self, task_id: str) -> Optional[Task]:
        """Read current durable state; another worker may have recovered it."""
        self.runtime.reconcile(raise_on_error=False)
        payload = self.runtime.get(task_id)
        return Task.from_dict(payload) if payload else None

    def update_task(
        self, task_id: str, status: Optional[TaskStatus] = None,
        progress: Optional[int] = None, message: Optional[str] = None,
        result: Optional[Dict] = None, error: Optional[str] = None,
        progress_detail: Optional[Dict] = None,
    ):
        from ..services.task_execution import current_attempt
        bound = current_attempt()
        runtime = bound.runtime if bound and bound.task_id == task_id else self.runtime
        current = runtime.get(task_id)
        if current is None and task_id not in runtime.handles:
            logger.warning("Task update skipped: task_id=%s not found requested_status=%s progress=%s error=%s",
                           task_id, getattr(status, 'value', status), progress, error)
            return
        attempt = self.attempt(task_id)
        changes = {key:value for key,value in dict(
            status=status.value if isinstance(status, TaskStatus) else status,
            progress=progress, message=message, result=result, error=error,
            progress_detail=progress_detail).items() if value is not None}
        payload = attempt.runtime.update(attempt, changes)
        if current and payload['status'] != current['status']:
            logger.info("Task status changed: task_id=%s %s -> %s progress=%s message=%s",
                        task_id, current['status'], payload['status'], payload.get('progress',0),
                        payload.get('message') or '-')
        with self._task_lock:
            self._tasks[task_id] = Task.from_dict(payload)

    def complete_task(self, task_id: str, result: Dict):
        """Mark task as completed"""
        self.update_task(
            task_id,
            status=TaskStatus.COMPLETED,
            progress=100,
            message="Task completed",
            result=result
        )
        result_keys = ",".join(sorted((result or {}).keys())) or "-"
        logger.info("Task completed: task_id=%s result_keys=%s", task_id, result_keys)

    def fail_task(self, task_id: str, error: str):
        """Mark task as failed"""
        self.update_task(
            task_id,
            status=TaskStatus.FAILED,
            message="Task failed",
            error=error
        )
        logger.error("Task failed: task_id=%s error=%s", task_id, error)

    def list_tasks(self, task_type: Optional[str] = None) -> list:
        self.runtime.reconcile(raise_on_error=False)
        tasks = self.runtime.records()
        return sorted((task for task in tasks if not task_type or task['task_type'] == task_type),
                      key=lambda task:task['created_at'], reverse=True)

    def cleanup_old_tasks(self, max_age_hours: int = 24):
        """Clean up old tasks"""
        from datetime import timedelta
        cutoff = datetime.now() - timedelta(hours=max_age_hours)

        with self._task_lock:
            old_ids = [
                tid for tid, task in self._tasks.items()
                if task.created_at < cutoff and task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]
            ]
            for tid in old_ids:
                del self._tasks[tid]
                if self._repository is not None:
                    self._repository.delete_task(tid)
