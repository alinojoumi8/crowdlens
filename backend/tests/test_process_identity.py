import os
import subprocess
import sys

import pytest
from app.utils.process_identity import process_identity


def test_birth_identity_tracks_one_actual_child_lifetime():
    if sys.platform!='linux':pytest.skip('Linux /proc identity')
    child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'])
    try:
        identity=process_identity(child.pid)
        assert identity and identity['pid']==child.pid
        assert identity==process_identity(child.pid)
        assert identity != process_identity(os.getpid())
    finally:
        child.terminate();child.wait(timeout=5)
    assert process_identity(child.pid) is None
    assert process_identity(-1) is None
