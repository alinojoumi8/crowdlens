"""Bounded process entry point shared by file and URL ingestion."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile

from .ingestion_limits import WORKER_SECONDS, MAX_TEXT_CHARS


def run_ingestion(mode, value):
    worker = Path(__file__).with_name('ingestion_worker.py')
    # Do not inherit provider credentials, proxy settings, Python startup hooks,
    # open DB descriptors or the app's mutable environment into parsing.
    env = {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'OMP_THREAD_LIMIT': '1'}
    limit = MAX_TEXT_CHARS * 12 + 4096
    with tempfile.TemporaryFile() as output_file:
        process = subprocess.Popen([sys.executable, '-I', str(worker)],
            stdin=subprocess.PIPE, stdout=output_file, stderr=subprocess.DEVNULL,
            env=env, close_fds=True, start_new_session=True)
        try:
            process.communicate(json.dumps([mode, value]).encode(), timeout=WORKER_SECONDS)
        except subprocess.TimeoutExpired:
            raise ValueError('Source extraction timed out; split the source and retry.') from None
        finally:
            # Also kill descendants if OCR outlives its immediate parent.
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.communicate()
        output_file.seek(0)
        output = output_file.read(limit + 1)
    if process.returncode or len(output) > limit:
        raise ValueError('Source extraction exceeded its resource limits.')
    try:
        data = json.loads(output)
    except (ValueError, UnicodeError):
        raise ValueError('Source extraction failed safely.') from None
    if data.get('error'):
        raise ValueError(data['error'])
    return data['result']
