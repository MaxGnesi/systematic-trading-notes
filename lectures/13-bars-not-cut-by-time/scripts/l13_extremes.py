"""Lecture 13 §3.5: the most extreme moments of the tape. The 20 days with the largest one-minute price range; on each, the busiest second
(trades and different prices) and the largest sweep (one order: trades in the same millisecond on the same side, through how many prices).
Also the second after the Fed decision of 21 September 2022, the example of §3.5."""
import json, sys
from datetime import date, datetime, timezone
from pathlib import Path
import numpy as np, polars as pl
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


def day_trades(d0):
    a = int(datetime(d0.year, d0.month, d0.day, tzinfo=timezone.utc).timestamp() * 1000)
    return (pl.scan_parquet(tape.source(SYM, d0.strftime("%Y-%m"))).filter(pl.col("transact_time").is_between(a, a + 86_400_000, closed="left"))
              .select("transact_time", "price", "quantity", "is_buyer_maker").collect().with_columns((pl.col("price") * pl.col("quantity")).alias("usd")))


def busiest_second(t):
    s = t.group_by(pl.col("transact_time") // 1000).agg(pl.len().alias("trades"), pl.col("price").n_unique().alias("prices")).sort("trades", descending=True).row(0, named=True)
    return dict(second=datetime.fromtimestamp(s["transact_time"], timezone.utc).strftime("%H:%M:%S"), trades=s["trades"], prices=s["prices"])


def sweeps(t, k=3, by="prices"):
    o = (t.group_by("transact_time", "is_buyer_maker").agg(pl.col("price").n_unique().alias("prices"), pl.col("price").min().alias("lo"), pl.col("price").max().alias("hi"),
                                                           pl.col("usd").sum(), pl.col("quantity").sum().alias("btc"))
           .with_columns(((pl.col("hi") / pl.col("lo") - 1) * 100).alias("pct")).sort(by, descending=True).head(k))
    return [dict(time=datetime.fromtimestamp(r["transact_time"] / 1000, timezone.utc).strftime("%H:%M:%S.%f")[:-3], side="sell" if r["is_buyer_maker"] else "buy",
                 prices=r["prices"], low=r["lo"], high=r["hi"], pct=round(r["pct"], 2), usd_m=round(r["usd"] / 1e6, 1), btc=round(r["btc"], 1)) for r in o.iter_rows(named=True)]


R = {}
m1 = pl.scan_parquet(sorted(D.glob("*/m1.parquet"))).select("time", "high", "low").collect()
top = (m1.with_columns(((pl.col("high") / pl.col("low") - 1) * 100).alias("rng"), pl.col("time").dt.date().alias("day"))
         .group_by("day").agg(pl.col("rng").max()).sort("rng", descending=True).head(20))
rows = []
for d0, rng in top.iter_rows():
    tape.wait_for_memory(2.0)
    t = day_trades(d0)
    rows.append(dict(day=d0.isoformat(), range_pct=round(rng, 1), **{f"busiest_{k}": v for k, v in busiest_second(t).items()}, sweeps=sweeps(t), sweeps_by_move=sweeps(t, 1, "pct")))
    print(rows[-1]["day"], rows[-1]["range_pct"], rows[-1]["busiest_second"], rows[-1]["busiest_trades"], rows[-1]["sweeps"][0], flush=True)
R["extreme_days"] = rows
R["largest_sweeps"] = sorted(({"day": r["day"], **s} for r in rows for s in r["sweeps"][:1]), key=lambda x: -x["prices"])

# the example of §3.5: the second 18:00:02 UTC on 21 September 2022
t = day_trades(date(2022, 9, 21)); a = int(datetime(2022, 9, 21, 18, 0, 2, tzinfo=timezone.utc).timestamp() * 1000)
s = t.filter(pl.col("transact_time").is_between(a, a + 1000, closed="left"))
R["fed_second"] = dict(trades=s.height, prices=s["price"].n_unique(), low=s["price"].min(), high=s["price"].max(), most_prices=sweeps(s, 1)[0], largest_move=sweeps(s, 1, "pct")[0])
(L13_RESULTS / "l13_extremes.json").write_text(json.dumps(R, indent=1))
print(json.dumps(R["fed_second"], indent=1)); print(json.dumps(R["largest_sweeps"][:4], indent=1))
