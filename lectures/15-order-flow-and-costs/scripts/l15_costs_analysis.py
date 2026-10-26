"""Lecture 15 §5: analysis of data/interim/l15_costs (l15_costs.py). Cost of a market order and what the resting side keeps, by order size, by volatility
regime (the last hour's realised variance against its 28-day median, thirds as in §2, known before the hour), and in the minute after a sweep of 10 bp
or more (§3) against all other times. Means per order in bp; t-statistics with days as clusters. Fees: Binance USD-M, regular account, 2 bp maker, 5 bp taker."""
import json, math, sys
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

D = tape.ROOT / "interim" / "tape" / "BTCUSDT"; C = tape.ROOT / "interim" / "l15_costs"
MAKER, TAKER = 2.0, 5.0; BLAB = ["< $1k", "$1k-10k", "$10k-100k", "$100k-1m", "> $1m"]; HZ = ["1s", "10s", "60s"]
A = pl.concat([pl.read_parquet(f) for f in sorted(C.glob("20??-??-??.parquet"))])
SP = pl.concat([pl.read_parquet(f) for f in sorted(C.glob("*_spread.parquet"))])
SM = pl.concat([pl.read_parquet(f) for f in sorted(C.glob("*_sample.parquet"))])

# volatility regime per hour, known before it (same construction as §2)
m1 = pl.scan_parquet(sorted(D.glob("*/m1.parquet"))).select("time", "close").collect().sort("time")
t0 = m1["time"][0]; n = int((m1["time"][-1] - t0).total_seconds() // 60) + 1
g = pl.DataFrame({"time": pl.datetime_range(t0, t0 + timedelta(minutes=n - 1), "1m", eager=True)}).join(m1, on="time", how="left").sort("time").with_columns(pl.col("close").forward_fill())
r1 = np.r_[0.0, np.diff(np.log(g["close"].to_numpy()))]; c2 = np.r_[0.0, np.cumsum(r1 ** 2)]
rv60 = np.r_[np.full(60, np.nan), c2[60:] - c2[:-60]][:n]; med = pl.Series(rv60).rolling_median(28 * 1440, min_samples=7 * 1440).shift(1).to_numpy()
H = np.arange(28 * 1440, n, 60); reg = rv60[H - 1] / med[H - 1]
t0ms = int(np.datetime64(t0, "ms").astype(np.int64))
R = pl.DataFrame({"hour": t0ms + H * 60_000, "reg": reg}).filter(pl.col("reg").is_finite())
q1, q2 = np.quantile(R["reg"].to_numpy(), [1 / 3, 2 / 3])                       # thirds over the five years, as in §2
R = R.with_columns(pl.when(pl.col("reg") < q1).then(pl.lit("calm")).when(pl.col("reg") < q2).then(pl.lit("normal")).otherwise(pl.lit("volatile")).alias("vol"))
A = A.join(R.select("hour", "vol"), on="hour", how="left").with_columns((pl.col("hour") // 86_400_000).alias("day"))
COLS = ["quoted", "eff"] + [f"{k}_{h}" for k in ("imp", "real") for h in HZ]


def table(by):
    """Mean per order of each measure, and a day-clustered t-statistic for the realised spread."""
    out = []
    for key, grp in A.group_by(by, maintain_order=True):
        row = dict(zip(by, key)); N = grp["n"].sum(); row.update(orders=int(N), usd_bn=round(grp["usd"].sum() / 1e9, 2))
        for c in COLS: row[c] = round(grp[f"s_{c}"].sum() / N, 3); row[f"{c}_usdw"] = round(grp[f"w_{c}"].sum() / grp["usd"].sum(), 3)
        for h in HZ:                                                           # day-level means of the realised spread -> t-statistic
            dd = grp.group_by("day").agg((pl.col(f"s_real_{h}").sum() / pl.col("n").sum()).alias("m"))["m"].to_numpy()
            row[f"t_real_{h}"] = round(float(dd.mean() / (dd.std(ddof=1) / math.sqrt(len(dd)))), 1) if len(dd) > 2 else None
        out.append(row)
    return out


res = dict(days=SP.height, covered_hours=round(float(SP["covered_hours"].sum()), 1), share_matched=round(float(SP["orders_matched"].sum() / SP["orders_total"].sum()), 4),
           time_share_one_tick=round(float(SP["time_share_one_tick"].mean()), 4), time_mean_quoted_bp=round(float(SP["time_mean_quoted"].mean()), 4),
           by_size=table(["bucket"]), by_size_vol=table(["bucket", "vol"]), by_vol=table(["vol"]))
# the minute after a sweep of at least 10 bp, from the 2% sample of orders
SW = pl.read_parquet(tape.ROOT / "interim" / "l15_sweeps.parquet", columns=["time_ms", "move_bp"]).filter(pl.col("move_bp") >= 10).sort("time_ms")
sw = SW["time_ms"].to_numpy(); tt = SM["t"].to_numpy(); k = np.searchsorted(sw, tt, side="left") - 1
after = (k >= 0) & (tt - sw[np.maximum(k, 0)] <= 60_000) & (tt > sw[np.maximum(k, 0)])
SM = SM.with_columns(pl.Series("after_sweep", after), (pl.col("t") // 86_400_000).alias("day"))
res["after_sweep"] = []
for flag, grp in SM.group_by("after_sweep"):
    row = dict(after_sweep=bool(flag[0]), orders_in_sample=grp.height, eff=round(float(grp["eff"].mean()), 3))
    for h in HZ: row[f"real_{h}"] = round(float(grp[f"real_{h}"].mean()), 3); row[f"imp_{h}"] = round(float(grp[f"imp_{h}"].mean()), 3)
    res["after_sweep"].append(row)
(L15_RESULTS / "l15_costs_analysis.json").write_text(json.dumps(res, indent=1))

print(f"days {res['days']}, hours covered {res['covered_hours']}, orders matched {res['share_matched']:.1%}, one tick {res['time_share_one_tick']:.1%} of the time, "
      f"mean quoted half-spread {res['time_mean_quoted_bp']} bp")
print("\nby size: per order | quoted, effective, impact 1s/10s/60s, realised 1s/10s/60s (t)   [taker pays eff + 5; maker keeps real - 2]")
for r in sorted(res["by_size"], key=lambda r: BLAB.index(r["bucket"])):
    print(f"{r['bucket']:10} n {r['orders']:9}  q {r['quoted']:.3f}  eff {r['eff']:6.3f}  imp {r['imp_1s']:6.3f} {r['imp_10s']:6.3f} {r['imp_60s']:6.3f}  "
          f"real {r['real_1s']:+6.3f} {r['real_10s']:+6.3f} {r['real_60s']:+6.3f} (t {r['t_real_10s']})")
print("\nby volatility regime")
for r in res["by_vol"]:
    print(f"{str(r['vol']):9} n {r['orders']:9}  eff {r['eff']:6.3f}  imp_10s {r['imp_10s']:6.3f}  real 1s/10s/60s {r['real_1s']:+6.3f} {r['real_10s']:+6.3f} {r['real_60s']:+6.3f} (t {r['t_real_10s']})")
print("\nafter a sweep (2% sample)")
for r in res["after_sweep"]: print(r)
