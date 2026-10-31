"""Settings shared by the Lecture 20 scripts. Environment variables: BYBIT_ROOT, the Bybit data folder of Lecture 18 (default: data/bybit at the
top of the repository), whose parquet/ holds the converted book and trades; BINANCE_ROOT, the Binance archive (default: data/binance); L18_OUT and
L19_OUT, where Lectures 18 and 19 wrote their results (defaults: BYBIT_ROOT/interim/l18 and /l19), read here: the pulls of Lecture 18, the book
state, the samples, the per-minute depth, the refilling chains, the publish delay and Binance's prices of Lecture 19; L20_OUT, where results are
written (default: BYBIT_ROOT/interim/l20); L20_PREFIX, put before the names of the figures (the notebook uses nb_, so that the lecture's own
figures are never overwritten). Results are read from L20_OUT if there, otherwise from results/ next to this folder: the 45-day results shipped
with the lecture. Scripts that take days as arguments run on those days only and write their results with the prefix check_."""
import os, sys
from pathlib import Path
import numpy as np, polars as pl

LECTURE = Path(__file__).resolve().parents[1]; REPO = LECTURE.parents[1]
sys.path.insert(0, str(REPO))
SYM = "BTCUSDT"
ROOT = Path(os.environ.get("BYBIT_ROOT", REPO / "data" / "bybit"))
PARQUET = ROOT / "parquet"; BOOK, TRADES = PARQUET / "orderbook" / SYM, PARQUET / "trades" / SYM
BN_RAW = Path(os.environ.get("BINANCE_ROOT", REPO / "data" / "binance")) / "raw" / "aggTrades" / SYM
PULLS = Path(os.environ.get("L18_OUT", ROOT / "interim" / "l18")) / "pulls"
L19_OUT = Path(os.environ.get("L19_OUT", ROOT / "interim" / "l19")); STATE, S3_19, BN = L19_OUT / "state", L19_OUT / "s3", L19_OUT / "binance"
OUT = Path(os.environ.get("L20_OUT", ROOT / "interim" / "l20"))
ORD, BOOK10, KEY, S3, S4, FOLLOW = (OUT / s for s in ("orders", "book10", "key", "s3", "s4", "followups"))
for p in (ORD, BOOK10, KEY, S3, S4, FOLLOW): p.mkdir(parents=True, exist_ok=True)
RESULTS, FIG = LECTURE / "results", LECTURE / "figures"
PREFIX = os.environ.get("L20_PREFIX", "")
CASC = "2025-10-10"                                                                # the day of the cascade
POST = int(np.datetime64("2025-10-10T20:50:01.702", "ms").astype(np.int64))        # the tariff post
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8")


def result_path(folder, name):
    """A result file: the one computed here (folder/name) if it exists, otherwise the one shipped with the lecture (results/<folder>/name)."""
    p = folder / name
    return p if p.exists() else RESULTS / folder.name / name


def days():
    return sorted(p.stem for p in BOOK.glob("*.parquet"))


def day_list():
    """The days given as arguments (a check), otherwise every day in the data folder."""
    return sys.argv[1:] or days()


def tag():
    """check_ when the script runs on chosen days only, so that the 45-day results are never overwritten by a check."""
    return "check_" if sys.argv[1:] else ""


class _Tee:
    def __init__(self, *s): self.s = s
    def write(self, x):
        for s in self.s: s.write(x)
    def flush(self):
        for s in self.s: s.flush()


def log(name):
    """Copy what the script prints to L20_OUT/followups/name.txt, for scripts whose result is a printed table."""
    sys.stdout = _Tee(sys.stdout, open(FOLLOW / f"{tag()}{name}.txt", "w", encoding="utf-8"))


# ---- intervals: OFI (best and 10 levels), TI, mid change, depth at the best ----
def intervals(day, D):
    B = pl.read_parquet(BOOK10 / f"{day}.parquet")
    d0 = int(np.datetime64(f"{day}T00:00:00", "s").astype(np.int64))
    B = B.filter((pl.col("sec") >= d0) & (pl.col("sec") < d0 + 86400)).with_columns((pl.col("sec") // D).alias("k"))
    A = B.group_by("k").agg([pl.col(f"ofi_{j}").sum() for j in range(1, 11)] + [pl.col("mid2").last(), pl.col("q_best").mean(), pl.len().alias("ns"),
                                                                                pl.col("reset").max()]).sort("k")
    A = A.with_columns(((pl.col("mid2") - pl.col("mid2").shift(1)) / 2).alias("dm"), (pl.col("k") - pl.col("k").shift(1)).alias("dk"))
    O = pl.read_parquet(ORD / f"bybit_{day}.parquet", columns=["ts", "side", "size"])
    T = O.with_columns((pl.col("ts") // 1000 // D).alias("k")).group_by("k").agg((pl.col("side") * pl.col("size")).sum().alias("ti"))
    A = A.join(T, on="k", how="left").with_columns(pl.col("ti").fill_null(0.0), pl.lit(day).alias("day"))
    # complete intervals only: every second present (a second without a book update has no row, so D seconds = D rows only if the book updated
    # every second), previous interval adjacent, no reset of the book (feed gaps)
    A = A.filter((pl.col("dk") == 1) & (pl.col("reset") == 0) & (pl.col("ns") >= max(1, D // 2)))
    return A.with_columns(pl.col("ofi_1").shift(1).alias("ofi_prev"), (pl.col("k") - pl.col("k").shift(1)).alias("dk2")).with_columns(
        pl.when(pl.col("dk2") == 1).then(pl.col("ofi_prev")).otherwise(None).alias("ofi_prev"))
