"""One worker owns background tasks and simulation subprocesses."""
import os

bind = os.environ.get('CROWDLENS_BIND', '127.0.0.1:3000,127.0.0.1:5001').split(',')
workers = 1
worker_class = 'gthread'
threads = 8
preload_app = False
max_requests = 0
timeout = 60
graceful_timeout = 45
accesslog = '-'
errorlog = '-'
capture_output = True


def on_starting(server):
    if server.cfg.workers != 1 or server.cfg.preload_app or server.cfg.max_requests:
        raise RuntimeError('CrowdLens requires one worker, no preload and no request recycling; '
                           'the worker owns background tasks and simulation subprocesses.')
