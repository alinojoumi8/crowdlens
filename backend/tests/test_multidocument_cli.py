"""Live CLI must reject accidental billing and output reuse before generation."""
from pathlib import Path
import subprocess
import sys
import tempfile
import uuid

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/verify_multidocument_drafts.py'


def test_live_flag_is_required_before_output_creation():
    path = Path(tempfile.gettempdir()) / ('crowdlens-multidoc-' + uuid.uuid4().hex)
    result = subprocess.run([sys.executable, str(SCRIPT), '--model', 'unused', '--output-dir', str(path)], capture_output=True, text=True)
    assert result.returncode == 2
    assert '--live' in result.stderr and not path.exists()


def test_existing_output_is_rejected_without_touching_receipt():
    with tempfile.TemporaryDirectory(prefix='crowdlens-multidoc-') as directory:
        marker = Path(directory) / 'prior-receipt.txt'
        marker.write_text('preserve me')
        result = subprocess.run([sys.executable, str(SCRIPT), '--live', '--model', 'unused', '--output-dir', directory], capture_output=True, text=True)
        assert result.returncode == 2
        assert 'new /tmp/crowdlens-multidoc-' in result.stderr
        assert marker.read_text() == 'preserve me'
