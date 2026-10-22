"""Launch a fixed OASIS preset after installing managed logical-write accounting."""
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))


def main():
    sys.dont_write_bytecode = True
    if len(sys.argv) < 2:
        raise SystemExit('A simulation preset is required')
    script = Path(sys.argv[1]).resolve()
    if script.parent != ROOT or script.name not in {
            'run_parallel_simulation.py', 'run_twitter_simulation.py', 'run_reddit_simulation.py'}:
        raise SystemExit('Unsupported simulation preset')
    from app.services.quota_subprocess import install
    install()
    sys.argv = sys.argv[1:]
    sys.path.insert(0, str(ROOT))
    runpy.run_path(str(script), run_name='__main__')


if __name__ == '__main__':
    main()
