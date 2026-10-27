"""Lecture 16 §6: the pure premium, long spot and short the perpetual (cash and carry), October 2021 to September 2026. Daily, at 00:00 UTC: spot close
(Binance BTCUSDT daily candles) and the perpetual's close at the same moment (our tape). Return of the structure per day = funding received by the short
perpetual (sum of the day's settlements) - change in the basis, basis = log(perpetual / spot). Costs: one round trip in each leg (spot 10 bp per side,
perpetual 5 bp per side, regular account), charged once. Against cash: the capital sits in spot, so the excess return subtracts the 3-month T-bill rate."""
import io, json, sys, zipfile
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

D = tape.ROOT / "interim" / "tape" / "BTCUSDT"
fr_ = []
for f in sorted((tape.ROOT / "raw" / "binance" / "spot_klines_1d" / "BTCUSDT").glob("*.zip")):
    z = zipfile.ZipFile(f); fr_.append(pl.read_csv(io.BytesIO(z.read(z.namelist()[0])), has_header=False, infer_schema_length=0, new_columns=[f"c{i}" for i in range(12)])
                                      .select(pl.col("c0").cast(pl.Int64).alias("open_time"), pl.col("c4").cast(pl.Float64).alias("spot")))
S = pl.concat(fr_).with_columns(pl.when(pl.col("open_time") > 10 ** 14).then(pl.col("open_time") // 1000).otherwise(pl.col("open_time")).alias("ms"))
S = S.with_columns(pl.from_epoch(pl.col("ms") + 86_400_000, time_unit="ms").cast(pl.Datetime("us")).alias("t")).select("t", "spot").sort("t")
m1 = pl.scan_parquet(sorted(D.glob("*/m1.parquet"))).select("time", "close").collect().sort("time")
P = m1.with_columns((pl.col("time") + pl.duration(minutes=1)).alias("t")).select("t", pl.col("close").alias("perp"))
X = S.join(P, on="t", how="inner").sort("t")
fr = pl.read_parquet(tape.ROOT / "raw" / "binance" / "um" / "fundingRate" / "BTCUSDT-fundingRate.parquet").select(
    pl.col("fundingTime").cast(pl.Int64).cast(pl.Datetime("ms")).cast(pl.Datetime("us")).alias("ft"), "fundingRate")
# funding settled in (t-1d, t]: the 08:00 and 16:00 settlements of the previous day and the 00:00 one at t
fr = fr.with_columns((pl.col("ft").dt.truncate("1h") - pl.duration(hours=1)).dt.truncate("1d").alias("d")).group_by("d").agg(pl.col("fundingRate").sum().alias("f"))
X = X.with_columns((pl.col("t") - pl.duration(days=1)).alias("d")).join(fr, on="d", how="left").with_columns(pl.col("f").fill_null(0.0))
tb = pl.read_csv(tape.ROOT / "raw" / "fred_DTB3.csv", infer_schema_length=0)
tb = tb.select(pl.col(tb.columns[0]).str.to_date().cast(pl.Datetime("us")).alias("d"), pl.col(tb.columns[1]).cast(pl.Float64, strict=False).alias("bill")).drop_nulls().sort("d")
X = X.sort("d").join_asof(tb, on="d", strategy="backward").with_columns((pl.col("bill") / 100 / 365).alias("cash"))
X = X.with_columns((pl.col("perp") / pl.col("spot")).log().alias("basis")).with_columns((-pl.col("basis").diff()).alias("dbasis")).drop_nulls("dbasis")
X = X.with_columns((pl.col("f") + pl.col("dbasis")).alias("carry"))
COST = (2 * 10 + 2 * 5) / 1e4
yrs = X.height / 365.25
R = dict(start=str(X["t"][0]), end=str(X["t"][-1]), years=round(yrs, 2), funding_total=round(float(X["f"].sum()), 4), basis_change_total=round(float(X["dbasis"].sum()), 4),
         basis_start_bp=round(float(X["basis"][0] * 1e4), 1), basis_end_bp=round(float(X["basis"][-1] * 1e4), 1), costs_once=COST, cash_total=round(float(X["cash"].sum()), 4),
         carry_total=round(float(X["carry"].sum() - COST), 4), excess_total=round(float(X["carry"].sum() - COST - X["cash"].sum()), 4),
         carry_per_year=round(float((X["carry"].sum() - COST) / yrs), 4), excess_per_year=round(float((X["carry"].sum() - COST - X["cash"].sum()) / yrs), 4),
         daily_sharpe_excess=round(float((X["carry"] - X["cash"]).mean() / (X["carry"] - X["cash"]).std() * np.sqrt(365)), 2),
         worst_day_bp=round(float(X["carry"].min() * 1e4), 1), share_days_negative=round(float((X["carry"] < 0).mean()), 3))
by = X.group_by(pl.col("t").dt.year().alias("year")).agg((pl.col("f").sum() * 100).round(2).alias("funding_pct"), (pl.col("dbasis").sum() * 100).round(2).alias("basis_change_pct"),
                                                         (pl.col("cash").sum() * 100).round(2).alias("bill_pct"), ((pl.col("carry") - pl.col("cash")).sum() * 100).round(2).alias("excess_pct")).sort("year")
R["by_year"] = by.to_dicts()
(L16_RESULTS / "l16_carry.json").write_text(json.dumps(R, indent=1, default=str))
print(json.dumps({k: v for k, v in R.items() if k != "by_year"}, indent=1, default=str)); print(by)

# compounded: the structure's value grows day by day by (1 + carry); costs once at the start
growth = float((1 - COST) * (1 + X["carry"]).product()); bills = float((1 + X["cash"]).product())
R["total_return_compounded"] = round(growth - 1, 4); R["total_return_per_year_compounded"] = round(growth ** (1 / yrs) - 1, 4)
R["riskfree_compounded"] = round(bills - 1, 4); R["riskfree_per_year_compounded"] = round(bills ** (1 / yrs) - 1, 4)
R["excess_per_year_compounded"] = round(growth ** (1 / yrs) - bills ** (1 / yrs), 4)
(L16_RESULTS / "l16_carry.json").write_text(json.dumps(R, indent=1, default=str))
print({k: R[k] for k in ("total_return_compounded", "total_return_per_year_compounded", "riskfree_compounded", "riskfree_per_year_compounded", "excess_per_year_compounded")})
