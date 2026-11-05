"""Settings shared by the Lecture 22 scripts. L22_PREFIX is put before the names of the figures (the notebook uses nb_, so that the lecture's own figures are never overwritten)."""
import os, sys
from pathlib import Path

LECTURE = Path(__file__).resolve().parents[1]; REPO = LECTURE.parents[1]
sys.path.insert(0, str(REPO))
RESULTS, FIG = LECTURE / "results", LECTURE / "figures"
PREFIX = os.environ.get("L22_PREFIX", "")
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8")
