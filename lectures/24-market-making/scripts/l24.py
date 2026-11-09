"""Settings shared by the Lecture 24 scripts. Lecture 21's replay (its settings, data folders and fill rules) is used unchanged; environment variables as there
(BYBIT_ROOT, L19_OUT, L21_OUT) and BINANCE_ROOT for Lecture 20's Binance archive. L24_OUT: where results are written (default BYBIT_ROOT/interim/l24);
L24_RESULTS: where summaries are read and written (default results/ next to this folder); L24_PREFIX is put before the names of the figures."""
import os, sys
from pathlib import Path

LECTURE = Path(__file__).resolve().parents[1]; L21_SCRIPTS = LECTURE.parent / "21-replaying-the-exchange" / "scripts"
sys.path.insert(0, str(L21_SCRIPTS)); import l21 as L21
if not L21.STATE.exists() and L21.STATE.parent.exists(): L21.STATE = L21.STATE.parent                 # the book state written directly in L19_OUT
RESULTS = Path(os.environ.get("L24_RESULTS", LECTURE / "results")); FIG = LECTURE / "figures"; RESULTS.mkdir(parents=True, exist_ok=True)
OUT = Path(os.environ.get("L24_OUT", L21.ROOT / "interim" / "l24")); OUT.mkdir(parents=True, exist_ok=True)
PREFIX = os.environ.get("L24_PREFIX", "")
BN_RAW = Path(os.environ.get("BINANCE_ROOT", L21.REPO / "data" / "binance")) / "raw" / "aggTrades" / L21.SYM
IN_SAMPLE = ("2025-09-20", "2025-10-09"); OUT_SAMPLE = ("2025-10-11", "2025-11-03"); CASCADE_DAY = "2025-10-10"
SIZE, LIMIT, LAT, A = 0.001, 10, 50, 1.0                                             # BTC per order, lots either way, ms, the queue rule's a
