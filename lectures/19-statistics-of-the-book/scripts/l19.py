"""Settings shared by the Lecture 19 scripts. Environment variables: BYBIT_ROOT, the Bybit data folder of Lecture 18 (default: data/bybit at the
top of the repository), whose parquet/ holds the converted book and trades; BINANCE_ROOT, the Binance archive (default: data/binance), used in §4; L18_OUT, where Lecture 18 wrote its
results (default: BYBIT_ROOT/interim/l18), whose pulls §3.7 uses;
L19_OUT, where results are written (default: BYBIT_ROOT/interim/l19); L19_PREFIX, put before the names of the figures (the notebook uses nb_, so
that the lecture's own figures are never overwritten). Results are read from L19_OUT if there, otherwise from results/ next to this folder: the
45-day results shipped with the lecture."""
import os, sys
from pathlib import Path

LECTURE = Path(__file__).resolve().parents[1]; REPO = LECTURE.parents[1]
sys.path.insert(0, str(REPO))
SYM = "BTCUSDT"
ROOT = Path(os.environ.get("BYBIT_ROOT", REPO / "data" / "bybit"))
PARQUET = ROOT / "parquet"; TRADES = PARQUET / "trades" / SYM
BN_RAW = Path(os.environ.get("BINANCE_ROOT", REPO / "data" / "binance")) / "raw" / "aggTrades" / SYM
PULLS = Path(os.environ.get("L18_OUT", ROOT / "interim" / "l18")) / "pulls"                 # Lecture 18's pulls, for §3.7
OUT = Path(os.environ.get("L19_OUT", ROOT / "interim" / "l19"))
STATE, S3, BN = OUT / "state", OUT / "s3", OUT / "binance"
for p in (STATE, S3, BN): p.mkdir(parents=True, exist_ok=True)
RESULTS, FIG = LECTURE / "results", LECTURE / "figures"
L18_RESULTS = LECTURE.parent / "18-the-order-book" / "results"
PREFIX = os.environ.get("L19_PREFIX", "")
CASC = "2025-10-10"                                                                # the day of the cascade
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8")


def result_path(name):
    """A result file: the one computed here if it exists, otherwise the one shipped with the lecture."""
    return OUT / name if (OUT / name).exists() else RESULTS / name


def minute_path(day):
    """The per-minute frame of a day (depth and best prices), computed here or shipped for the days of figure 19_15."""
    p = S3 / f"b2_min_{day}.parquet"
    return p if p.exists() else RESULTS / f"b2_min_{day}.parquet"


def days():
    return sorted(p.stem for p in (PARQUET / "orderbook" / SYM).glob("*.parquet"))
