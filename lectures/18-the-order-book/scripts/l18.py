"""Settings shared by the Lecture 18 scripts. Environment variables: BYBIT_ROOT, the data folder (default: data/bybit at the top of the repository),
holding raw/ (the downloads) and parquet/ (the converted tables); L18_OUT, where results are written (default: BYBIT_ROOT/interim/l18);
L18_PREFIX, put before the names of the figures (the notebook uses nb_, so that the lecture's own figures are never overwritten).
Results are read from L18_OUT if there, otherwise from results/ next to this folder: the 45-day results shipped with the lecture."""
import os, sys
from pathlib import Path

LECTURE = Path(__file__).resolve().parents[1]; REPO = LECTURE.parents[1]
sys.path.insert(0, str(REPO))
SYM = "BTCUSDT"
ROOT = Path(os.environ.get("BYBIT_ROOT", REPO / "data" / "bybit"))
RAW, PARQUET = ROOT / "raw", ROOT / "parquet"
BOOK, TRADES = PARQUET / "orderbook" / SYM, PARQUET / "trades" / SYM
GAPS = PARQUET / f"{SYM}_book_gaps.csv"
SAMPLE_DAY = "2024-03-12"                                                          # the 500-level sample day of §1-§3, kept raw
SAMPLE_BOOK = RAW / "orderbook" / "linear" / SYM / f"{SAMPLE_DAY}_{SYM}_ob500.data.zip"
SAMPLE_TRADES = RAW / "trades" / SYM / f"{SYM}{SAMPLE_DAY}.csv.gz"
OUT = Path(os.environ.get("L18_OUT", ROOT / "interim" / "l18")); OUT.mkdir(parents=True, exist_ok=True)
RESULTS, FIG = LECTURE / "results", LECTURE / "figures"
PREFIX = os.environ.get("L18_PREFIX", "")
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8")


def result_path(name):
    """A result file: the one computed here if it exists, otherwise the one shipped with the lecture."""
    return OUT / name if (OUT / name).exists() else RESULTS / name


def gaps_path():
    return GAPS if GAPS.exists() else RESULTS / GAPS.name


def days():
    return sorted(p.stem for p in BOOK.glob("*.parquet"))
