"""Lecture 13 §7.5: after an option expiry, does the price move back towards the settlement average?
Settlement average: the time-weighted average of the one-minute closes from 07:30 to 08:00 UTC (Deribit settles on the 30-minute average of its index).
Gap: the settlement average minus the price at 08:00, in log terms. Move: the return from 08:00 to 08:00 + H minutes.
Moving back: the move has the sign of the gap. Monthly and quarterly expiry Fridays against Thursdays."""
import json, sys
from datetime import date, datetime, timedelta
from pathlib import Path
import numpy as np, polars as pl
from scipy import stats
import os, sys
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # tables print on any console; Jupyter handles its own
HERE = Path(__file__).resolve().parent                                     # lectures/13-.../scripts
sys.path[:0] = [str(HERE), str(HERE.parents[1] / "12-tick-data-the-tape"), str(HERE.parents[2])]   # this folder, tape.py, trading_models
import tape
L13_RESULTS = tape.ROOT / "interim" / "l13"; L13_RESULTS.mkdir(parents=True, exist_ok=True)          # results: in the data folder, never committed
FIG = Path(os.environ.get("L13_FIG", HERE.parent / "figures")); FIG.mkdir(parents=True, exist_ok=True)
PREFIX = os.environ.get("L13_PREFIX", "nb_")                               # "nb_": the lecture's own figures are never overwritten
import tape

SYM = "BTCUSDT"; D = tape.ROOT / "interim" / "tape" / SYM
m1 = (pl.scan_parquet(sorted(D.glob("*/m1.parquet"))).select("time", "close").collect().sort("time")
        .with_columns(pl.col("time").dt.date().alias("day"), (pl.col("time").dt.hour().cast(pl.Int32) * 60 + pl.col("time").dt.minute().cast(pl.Int32)).alias("mod")))
last_fri = lambda d: d.weekday() == 4 and (d + timedelta(days=7)).month != d.month
R = {}
for H in (30, 60):
    w = m1.filter(pl.col("mod").is_between(450, 480 + H))
    g = w.group_by("day").agg(pl.col("close").filter(pl.col("mod") < 480).log().mean().alias("avg"),          # closes of 07:30 ... 07:59
                              pl.col("close").filter(pl.col("mod") == 479).log().first().alias("p8"),           # the close of 07:59 = the price at 08:00
                              pl.col("close").filter(pl.col("mod") == 479 + H).log().first().alias("pH")).drop_nulls()
    g = g.with_columns((pl.col("avg") - pl.col("p8")).alias("gap"), (pl.col("pH") - pl.col("p8")).alias("move"))
    for lab, sel in (("monthly and quarterly expiries", lambda d: last_fri(d)), ("Thursdays", lambda d: d.weekday() == 3)):
        x = g.filter(pl.col("day").map_elements(sel, return_dtype=pl.Boolean))
        gap, mv = x["gap"].to_numpy(), x["move"].to_numpy(); r, p = stats.pearsonr(gap, mv)
        nz = (gap != 0) & (mv != 0); back = np.sign(gap[nz]) == np.sign(mv[nz])
        R[f"{lab}, {H} min"] = dict(n=len(gap), corr=round(float(r), 2), p=round(float(p), 2), moved_back=round(float(back.mean()), 2),
                                     p_back=round(float(stats.binomtest(int(back.sum()), int(nz.sum()), 0.5).pvalue), 2))
(L13_RESULTS / "l13_settlement.json").write_text(json.dumps(R, indent=1))
if __name__ == "__main__":
    for k, v in R.items(): print(k, v)
