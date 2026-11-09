"""Settings shared by the Lecture 22 scripts. Environment variables: BYBIT_ROOT, the Bybit data folder of Lecture 18 (default: data/bybit at the top of the repository), whose
parquet/ holds the converted book and trades; L19_OUT, where Lecture 19 wrote the book state after every update, in state/ or directly (default: BYBIT_ROOT/interim/l19); L18_OUT, where Lecture 18 wrote its
pull flags (default: BYBIT_ROOT/interim/l18); BINANCE_ROOT, the Binance archive of Lecture 20 (default: data/binance); L22_OUT, where results are written (default: BYBIT_ROOT/interim/l22);
L22_PREFIX is put before the names of the figures (the notebook uses nb_, so that the lecture's own figures are never overwritten)."""
import os, sys
from pathlib import Path

LECTURE = Path(__file__).resolve().parents[1]; REPO = LECTURE.parents[1]
sys.path.insert(0, str(REPO))
RESULTS, FIG = LECTURE / "results", LECTURE / "figures"
PREFIX = os.environ.get("L22_PREFIX", "")
SYM = "BTCUSDT"
ROOT = Path(os.environ.get("BYBIT_ROOT", REPO / "data" / "bybit")); PARQUET = ROOT / "parquet"; BOOK, TRADES = PARQUET / "orderbook" / SYM, PARQUET / "trades" / SYM
STATE = Path(os.environ.get("L19_OUT", ROOT / "interim" / "l19")); STATE = STATE / "state" if (STATE / "state").exists() else STATE; PULLS = Path(os.environ.get("L18_OUT", ROOT / "interim" / "l18")) / "pulls"
BN_RAW = Path(os.environ.get("BINANCE_ROOT", REPO / "data" / "binance")) / "raw" / "aggTrades" / SYM
OUT = Path(os.environ.get("L22_OUT", ROOT / "interim" / "l22"))
IN_SAMPLE = ("2025-09-20", "2025-10-09"); OUT_SAMPLE = ("2025-10-11", "2025-11-03"); CASCADE_DAY = "2025-10-10"
TAUS = (100, 1_000, 10_000, 60_000, 300_000)                                       # horizons of the response, ms
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8")
