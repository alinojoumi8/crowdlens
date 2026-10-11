"""Linux process birth identity; PID existence alone cannot establish ownership."""
from pathlib import Path
import os
import sys


def process_identity(pid):
    if sys.platform != 'linux':
        return None
    try:
        pid=int(pid)
        if pid <= 0:return None
        root=Path('/proc')/str(pid)
        fields=(root/'stat').read_text().rsplit(')',1)[1].split()
        if fields[0] in {'Z','X'}:return None
        return {'pid':pid,'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                'start_ticks':fields[19],'pid_namespace':os.readlink(root/'ns/pid')}
    except (OSError,ValueError,IndexError,TypeError):
        return None
