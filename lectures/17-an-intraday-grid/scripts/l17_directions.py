"""Lecture 17: three directions for the switched grid, all known at the time (values of the last FINISHED hour), no look-ahead.
Base: the volatility switch (off while the last finished hour's volatility > 2 x its 28-day median), ladder about 200 bp each side, stop + restart,
daily close, maker 2 / taker 5 bp. Variants, each on top of the base:
- skew by trend: Lecture 16's trend forecast (EWMAC blend 1-2-3 days, scaled to an average size of 1). "skew, sign": long inventory only when
  the forecast is positive (buy dips, sell the paired exits), short only when negative. "skew, strong": one-sided only when |forecast| > 1,
  symmetric otherwise. "off in strong trend": grid off when |forecast| > 1. A skew turning against the inventory closes it at market.
- channel (user's idea): on only while the price is inside the 10-day channel of hourly closes, or outside it by less than 10% of its width.
- time of day: the grid on only in one 4-hour UTC block (six separate grids).
- fees: the base at maker 1 and 0 bp.
In sample 2021-24, out of sample 2025-26."""
import sys
from pathlib import Path
import numpy as np, polars as pl
import os, sys
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # tables print on any console; Jupyter handles its own
HERE = Path(__file__).resolve().parent                                     # lectures/17-.../scripts
sys.path[:0] = [str(HERE), str(HERE.parents[1] / "16-trend-on-the-tape" / "scripts"), str(HERE.parents[1] / "13-bars-not-cut-by-time" / "scripts"),
                str(HERE.parents[1] / "12-tick-data-the-tape"), str(HERE.parents[2])]
import tape
L17_RESULTS = Path(os.environ.get("L17_RESULTS", tape.ROOT / "interim" / "l17")); L17_RESULTS.mkdir(parents=True, exist_ok=True)   # results: in the data folder, never committed
ONE_YEAR = os.environ.get("L17_ONE_YEAR")                                # a check: run the tape scripts on one year only
FIG = Path(os.environ.get("L17_FIG", HERE.parent / "figures")); FIG.mkdir(parents=True, exist_ok=True)
PREFIX = os.environ.get("L17_PREFIX", "nb_")                               # "nb_": the lecture's own figures are never overwritten
import l17_grid as g
import l16_buildup as L


STEPS = [25, 50, 100, 200]; WIDTH = 200; K = 2.0
YEARS = [(f"{ONE_YEAR}-01", f"{ONE_YEAR}-12")] if ONE_YEAR else [("2021-10", "2021-12"), ("2022-01", "2022-12"), ("2023-01", "2023-12"), ("2024-01", "2024-12"), ("2025-01", "2025-12"), ("2026-01", "2026-09")]

# hourly series known at each hour's close
tc = L.H["t_close"].dt.epoch("s").to_numpy(); fc = np.nan_to_num(L.FC); ph = L.p; rvh = L.rv
med = pl.Series(rvh).shift(1).rolling_median(672, min_samples=336).to_numpy(); vratio = rvh / med
hi = pl.Series(ph).rolling_max(240).to_numpy(); lo = pl.Series(ph).rolling_min(240).to_numpy()

rows = []
for a, b in YEARS:
    data = g.load(a, b); s, last = data[0], data[3]
    i = np.searchsorted(tc, s, side="right") - 1                    # the last finished hour at each second
    ok = i >= 0; i = np.maximum(i, 0)
    vol_on = ~(ok & (vratio[i] >= K))
    f = np.where(ok, fc[i], 0.0)
    w = hi[i] - lo[i]; inside = ~ok | np.isnan(w) | ((last >= lo[i] - 0.1 * w) & (last <= hi[i] + 0.1 * w))
    hour = (s % 86400) // 3600
    for st in STEPS:
        n = max(1, round(WIDTH / st)); N = np.full(len(s), n, dtype=np.int64); Z = np.zeros(len(s), dtype=np.int64)
        V = {"always on": dict(), "vol switch (base)": dict(on=vol_on),
             "skew, sign": dict(on=vol_on, qmax=np.where(f < 0, Z, N), qmin=np.where(f > 0, Z, -N)),
             "skew, strong": dict(on=vol_on, qmax=np.where(f < -1, Z, N), qmin=np.where(f > 1, Z, -N)),
             "off in strong trend": dict(on=vol_on & (np.abs(f) <= 1)),
             "channel": dict(on=vol_on & inside),
             "maker 1 bp": dict(on=vol_on, maker=1e-4), "maker 0 bp": dict(on=vol_on, maker=0.0)}
        for blk in range(6):
            V[f"only {4*blk:02d}-{4*blk+4:02d} UTC"] = dict(on=vol_on & (hour >= 4 * blk) & (hour < 4 * blk + 4))
        for name, kw in V.items():
            rows.append(g.run(data, st, n=n, **kw).with_columns(pl.lit(name).alias("rule"), pl.lit(st).alias("step")))
    print(a[:4], "done", flush=True)
    del data
R = pl.concat(rows).with_columns(pl.from_epoch(pl.col("day").cast(pl.Int64) * 86400).dt.year().alias("year"))
R.write_parquet(L17_RESULTS / "l17_directions.parquet")
R = R.with_columns(pl.when(pl.col("year") <= 2024).then(pl.lit("IS")).otherwise(pl.lit("OOS")).alias("period"))
A = R.group_by("step", "rule", "period").agg(pl.col("gross").mean(), pl.col("net").mean(), (pl.col("net").mean() / pl.col("net").std() * pl.len().sqrt()).alias("t"),
                                            pl.col("net").quantile(0.01).alias("w1"), pl.col("off_share").mean().alias("off"))
P = A.pivot(on="period", index=["step", "rule"], values=["gross", "net", "t", "w1", "off"]).sort("step", "rule")
pl.Config.set_tbl_rows(100); pl.Config.set_tbl_cols(20); pl.Config.set_tbl_width_chars(250); pl.Config.set_float_precision(3)
print(P.select("step", "rule", "gross_IS", "gross_OOS", "net_IS", "net_OOS", "t_IS", "t_OOS", "w1_IS", "w1_OOS", "off_IS"))
