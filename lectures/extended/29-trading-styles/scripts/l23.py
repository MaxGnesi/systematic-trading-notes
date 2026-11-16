"""Settings shared by the Lecture 29 scripts. Lecture 29 reuses Lecture 28's laboratory market (l22_sim.py), its footprint measures (l22_styles.py) and its tables of real orders
(L22_OUT/orders, controls, book), so Lecture 28's settings are loaded first: BYBIT_ROOT, L19_OUT, BINANCE_ROOT, L22_OUT as there. L23_RESULTS: where results are read and written
(default: results/ next to this folder); L23_PREFIX is put before the names of the figures (the notebook uses nb_)."""
import os, sys
from pathlib import Path

LECTURE = Path(__file__).resolve().parents[1]; L22_SCRIPTS = LECTURE.parent / "28-a-market-that-reacts" / "scripts"
sys.path.insert(0, str(L22_SCRIPTS)); import l22 as L22                             # noqa: E402  Lecture 28's paths and sample
RESULTS = Path(os.environ.get("L23_RESULTS", LECTURE / "results")); FIG = LECTURE / "figures"; RESULTS.mkdir(parents=True, exist_ok=True)
PREFIX = os.environ.get("L23_PREFIX", "")
