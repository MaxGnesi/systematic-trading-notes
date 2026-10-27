"""Lecture 16 §6: does the premium index line up with funding? 8-hour premium-index candles (Binance archive) against the funding history: open times,
and the funding rebuilt from the interval's premium by Binance's formula, funding = P + clamp(0.01% - P, -0.05%, +0.05%), with P the interval's average
premium, here approximated from the 8-hour candle (mean of open and close) and from the hourly candles (mean of the eight hourly closes)."""
import io, sys, zipfile
from pathlib import Path
import numpy as np, polars as pl
import os, sys
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # tables print on any console; Jupyter handles its own
HERE = Path(__file__).resolve().parent                                     # lectures/16-.../scripts
sys.path[:0] = [str(HERE), str(HERE.parents[1] / "13-bars-not-cut-by-time" / "scripts"), str(HERE.parents[1] / "12-tick-data-the-tape"), str(HERE.parents[2])]
import tape
L16_RESULTS = tape.ROOT / "interim" / "l16"; L16_RESULTS.mkdir(parents=True, exist_ok=True)          # results: in the data folder, never committed
FIG = Path(os.environ.get("L16_FIG", HERE.parent / "figures")); FIG.mkdir(parents=True, exist_ok=True)
PREFIX = os.environ.get("L16_PREFIX", "nb_")                               # "nb_": the lecture's own figures are never overwritten
import tape


def load(folder):
    out = []
    for f in sorted(folder.glob("*.zip")):
        z = zipfile.ZipFile(f); t = z.read(z.namelist()[0]).decode()
        d = pl.read_csv(io.StringIO(t), has_header=t.startswith("open_time"), new_columns=None, infer_schema_length=0)
        d = d.rename(dict(zip(d.columns[:5], ["open_time", "open", "high", "low", "close"]))).select(
            pl.col("open_time").cast(pl.Int64), *[pl.col(c).cast(pl.Float64) for c in ("open", "high", "low", "close")])
        out.append(d)
    d = pl.concat(out).with_columns(pl.when(pl.col("open_time") > 10 ** 14).then(pl.col("open_time") // 1000).otherwise(pl.col("open_time")).alias("ms"))
    return d.with_columns(pl.from_epoch("ms", time_unit="ms").cast(pl.Datetime("us")).alias("t")).sort("t")


R = tape.ROOT / "raw" / "binance" / "um" / "premiumIndexKlines"
P8, P1 = load(R / "BTCUSDT_8h"), load(R / "BTCUSDT")
print("8h candle open hours:", P8["t"].dt.hour().value_counts().sort("t").to_dicts())
P1 = P1.with_columns((pl.col("t") - pl.duration(hours=0)).dt.truncate("8h").alias("iv")).group_by("iv").agg(pl.col("close").mean().alias("p1"), pl.len().alias("k")).sort("iv")
fr = pl.read_parquet(tape.ROOT / "raw" / "binance" / "um" / "fundingRate" / "BTCUSDT-fundingRate.parquet").select(
    pl.col("fundingTime").cast(pl.Int64).cast(pl.Datetime("ms")).cast(pl.Datetime("us")).alias("ft"), "fundingRate")
fr = fr.with_columns(pl.col("ft").dt.truncate("1h").alias("ft")).with_columns((pl.col("ft") - pl.duration(hours=8)).alias("iv"))   # funding at T settles the interval [T-8h, T)
X = (P8.select(pl.col("t").alias("iv"), ((pl.col("open") + pl.col("close")) / 2).alias("p8"), "close").join(P1, on="iv").join(fr, on="iv").drop_nulls())
clamp = lambda p: p + np.clip(0.0001 - p, -0.0005, 0.0005)
for lab, col in (("from the 8-hour candle", "p8"), ("from the hourly candles", "p1")):
    f = clamp(X[col].to_numpy()); a = X["fundingRate"].to_numpy()
    print(f"{lab}: correlation with actual funding {np.corrcoef(f, a)[0, 1]:.3f}, median absolute gap {np.median(np.abs(f - a)) * 1e4:.3f} bp, exact to 0.1 bp: {np.mean(np.abs(f - a) < 1e-5):.1%}")
print("intervals matched:", X.height, X["iv"].min(), X["iv"].max())

# the same with a weighted average of the hourly closes, later hours weighing more (weights 1..8)
H1 = load(R / "BTCUSDT").with_columns(pl.col("t").dt.truncate("8h").alias("iv"), ((pl.col("t").dt.hour() % 8) + 1).alias("w"))
W = H1.group_by("iv").agg(((pl.col("close") * pl.col("w")).sum() / pl.col("w").sum()).alias("pw")).sort("iv")
Y = X.join(W, on="iv")
f = clamp(Y["pw"].to_numpy()); a = Y["fundingRate"].to_numpy()
print(f"weighted towards the end: correlation {np.corrcoef(f, a)[0, 1]:.3f}, median absolute gap {np.median(np.abs(f - a)) * 1e4:.3f} bp, exact to 0.1 bp: {np.mean(np.abs(f - a) < 1e-5):.1%}")
