"""Portable acceptance entry point used by CI and local launch instructions."""

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent
raise SystemExit(subprocess.call([sys.executable, "-m", "unittest", "discover", "-s", str(ROOT / "tests"), "-v"], cwd=ROOT))
