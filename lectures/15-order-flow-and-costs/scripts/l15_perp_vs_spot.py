"""Lecture 15 §7: a long perpetual against long spot, October 2021 to September 2026. Spot: Binance BTCUSDT daily closes (data/raw/binance/spot_klines_1d).
Perpetual: the close of our tape at the same moment (00:00 UTC). A long perpetual earns the perpetual's price change and pays funding at each settlement;
its capital beyond the margin can earn the 3-month T-bill rate (FRED DTB3); long spot earns only the spot price change."""
import io, json, sys, zipfile
from datetime import timedelta
from pathlib import Path
import numpy as np, polars as pl
import os, sys
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # tables print on any console; Jupyter handles its own
HERE = Path(__file__).resolve().parent                                     # lectures/15-.../scripts
sys.path[:0] = [str(HERE), str(HERE.parents[1] / "13-bars-not-cut-by-time" / "scripts"), str(HERE.parents[1] / "12-tick-data-the-tape"), str(HERE.parents[2])]
import tape
L15_RESULTS = tape.ROOT / "interim" / "l15"; L15_RESULTS.mkdir(parents=True, exist_ok=True)          # results: in the data folder, never committed
FIG = Path(os.environ.get("L15_FIG", HERE.parent / "figures")); FIG.mkdir(parents=True, exist_ok=True)
PREFIX = os.environ.get("L15_PREFIX", "nb_")                               # "nb_": the lecture's own figures are never overwritten
import tape

D = tape.ROOT / "interim" / "tape" / "BTCUSDT"
SPOT = tape.ROOT / "raw" / "binance" / "spot_klines_1d" / "BTCUSDT"; SPOT.mkdir(parents=True, exist_ok=True)
for ym in [f"{y}-{m:02d}" for y in range(2021, 2027) for m in range(1, 13) if "2021-10" <= f"{y}-{m:02d}" <= "2026-09"]:   # monthly zips of daily candles
    f = SPOT / f"BTCUSDT-1d-{ym}.zip"
    if not f.exists():
        import urllib.request
        f.write_bytes(urllib.request.urlopen(f"https://data.binance.vision/data/spot/monthly/klines/BTCUSDT/1d/BTCUSDT-1d-{ym}.zip", timeout=60).read())
fr_ = []
for f in sorted(SPOT.glob("*.zip")):
    z = zipfile.ZipFile(f); fr_.append(pl.read_csv(io.BytesIO(z.read(z.namelist()[0])), has_header=False, infer_schema_length=0, new_columns=[f"c{i}" for i in range(12)])
               .select(pl.col("c0").cast(pl.Int64).alias("open_time"), pl.col("c4").cast(pl.Float64).alias("close")))
S = pl.concat(fr_).with_columns(pl.when(pl.col("open_time") > 10 ** 14).then(pl.col("open_time") // 1000).otherwise(pl.col("open_time")).alias("ms"))   # microseconds from 2025
S = S.with_columns(pl.from_epoch(pl.col("ms") + 86_400_000, time_unit="ms").cast(pl.Datetime("us")).alias("t")).select("t", pl.col("close").alias("spot")).sort("t")   # close = price at the next 00:00
m1 = pl.scan_parquet(sorted(D.glob("*/m1.parquet"))).select("time", "close").collect().sort("time")
P = m1.with_columns((pl.col("time") + pl.duration(minutes=1)).alias("t")).select("t", pl.col("close").alias("perp"))
X = S.join(P, on="t", how="inner").sort("t")
fr = pl.read_parquet(tape.ROOT / "raw" / "binance" / "um" / "fundingRate" / "BTCUSDT-fundingRate.parquet").select(pl.col("time").cast(pl.Datetime("us")).alias("ft"), "fundingRate")
fr = fr.with_columns(pl.col("ft").dt.truncate("1d").alias("d")).group_by("d").agg(pl.col("fundingRate").sum().alias("f")).sort("d")
X = X.with_columns((pl.col("t") - pl.duration(days=1)).alias("d")).join(fr, on="d", how="left").with_columns(pl.col("f").fill_null(0.0))     # funding during the day ending at t
tb = pl.read_csv(tape.ROOT / "raw" / "fred_DTB3.csv", infer_schema_length=0)
tb = tb.select(pl.col(tb.columns[0]).str.to_date().cast(pl.Datetime("us")).alias("d"), pl.col(tb.columns[1]).cast(pl.Float64, strict=False).alias("bill")).sort("d")
X = X.sort("d").join_asof(tb.drop_nulls(), on="d", strategy="backward").with_columns((pl.col("bill") / 100 / 365).alias("cash"))
X = X.with_columns((pl.col("spot") / pl.col("spot").shift(1) - 1).alias("r_spot"), (pl.col("perp") / pl.col("perp").shift(1) - 1).alias("r_perp_px")).drop_nulls(["r_spot", "r_perp_px"])
X = X.with_columns((pl.col("r_perp_px") - pl.col("f")).alias("r_perp"), (pl.col("r_perp_px") - pl.col("f") + pl.col("cash")).alias("r_perp_cash"))
w = {k: float((1 + X[k]).product()) for k in ("r_spot", "r_perp_px", "r_perp", "r_perp_cash")}
yrs = (X["t"][-1] - X["t"][0]).total_seconds() / (365.25 * 86400)
res = dict(start=str(X["t"][0]), end=str(X["t"][-1]), years=round(yrs, 2), growth=w, cagr={k: round(v ** (1 / yrs) - 1, 4) for k, v in w.items()},
           funding_total=round(float(X["f"].sum()), 4), cash_total=round(float(X["cash"].sum()), 4),
           basis_start_bp=round(float((X["perp"][0] / X["spot"][0] - 1) * 1e4), 1), basis_end_bp=round(float((X["perp"][-1] / X["spot"][-1] - 1) * 1e4), 1),
           basis_abs_median_bp=round(float(((X["perp"] / X["spot"] - 1).abs() * 1e4).median()), 1))
by = X.group_by(pl.col("t").dt.year().alias("year")).agg(((1 + pl.col("r_spot")).product() - 1).alias("spot"), ((1 + pl.col("r_perp")).product() - 1).alias("perp"),
                                                       ((1 + pl.col("r_perp_cash")).product() - 1).alias("perp_cash"), pl.col("f").sum().alias("funding"), pl.col("cash").sum().alias("cash")).sort("year")
res["by_year"] = by.with_columns(pl.col(pl.Float64).round(4)).to_dicts()
X.select("t", "r_spot", "r_perp", "r_perp_cash", "f", "cash").write_parquet(tape.ROOT / "interim" / "l15_perp_vs_spot.parquet")
(L15_RESULTS / "l15_perp_vs_spot.json").write_text(json.dumps(res, indent=1, default=str))
print(json.dumps({k: v for k, v in res.items() if k != "by_year"}, indent=1, default=str)); print(by.with_columns(pl.col(pl.Float64).round(4)))
