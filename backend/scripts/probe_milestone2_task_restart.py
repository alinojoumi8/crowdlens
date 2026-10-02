"""Reproduce orphaned generic task state using two processes and disposable SQLite.

Exit 1 confirms the unresolved failure; exit 0 means the restored state is honest.
No application services or existing data are used.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--writer', type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    from app.models.task import TaskManager, TaskStatus
    from app.storage.control_db import ControlDatabase
    if args.writer:
        TaskManager.configure_repository(ControlDatabase(args.writer))
        identifier = TaskManager().create_task('graph_build', metadata={'project_id': 'synthetic_project'})
        TaskManager().update_task(identifier, status=TaskStatus.PROCESSING)
        args.writer.with_suffix('.id').write_text(identifier)
        return 0
    with tempfile.TemporaryDirectory(prefix='crowdlens-m2-task-') as directory:
        database = Path(directory) / 'control.db'
        subprocess.run([sys.executable, __file__, '--writer', str(database)], check=True)
        TaskManager.configure_repository(ControlDatabase(database))
        identifier = database.with_suffix('.id').read_text()
        task = TaskManager().get_task(identifier)
        unresolved = task.status == TaskStatus.PROCESSING
        print(json.dumps({'task_id': identifier, 'writer_process_exited': True,
                          'restored_status': task.status.value, 'unresolved': unresolved}))
        return 1 if unresolved else 0


if __name__ == '__main__':
    sys.exit(main())
