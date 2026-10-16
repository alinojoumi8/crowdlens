"""Request-local wall-clock budget and observed provider usage."""
import threading
import time


class DeadlineExceeded(RuntimeError):
    pass


class DraftBudget:
    def __init__(self, seconds=180, clock=time.monotonic, previous_usage=None):
        self.clock, self.started = clock, clock()
        self.deadline = self.started + seconds
        self.calls = list((previous_usage or {}).get('calls', []))
        self.previous_elapsed_ms = (previous_usage or {}).get('elapsed_ms', 0)
        self.lock = threading.Lock()

    def remaining(self):
        return max(0.0, self.deadline - self.clock())

    def check(self):
        if not self.remaining():
            raise DeadlineExceeded('deadline_exceeded')

    def record_usage(self, provider, model, usage, elapsed_ms):
        usage = usage or {}
        def count(*keys):
            for key in keys:
                value = usage.get(key)
                if type(value) is int and value >= 0:
                    return value
            return None
        with self.lock:
            self.calls.append(dict(provider=provider, model=model, attempt_count=1,
                                   input_tokens=count('input_tokens', 'prompt_tokens'),
                                   output_tokens=count('output_tokens', 'completion_tokens'),
                                   elapsed_ms=round(elapsed_ms, 2)))

    def snapshot(self):
        with self.lock:
            return {'calls': list(self.calls), 'elapsed_ms': self.previous_elapsed_ms + round((self.clock() - self.started) * 1000, 2),
                    'remaining_ms': round(self.remaining() * 1000, 2), 'cost': None}
