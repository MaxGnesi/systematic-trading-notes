"""Lecture 15 §3: checks on the sweep matrix. The measure: the return in the slower trend's direction after a sweep, from its last fill, over 10 min and 1 h,
for independent sweeps (the first of at least MIN bp in each block of B minutes), against the same return at moments without a sweep (every 10th minute
with a clear trend, same volatility regime). Per cell: sweep mean minus baseline mean, days as clusters, BH over the 12 tests of each variant.
Variants: MIN 5 / 10 / 20 bp with 10-minute blocks; MIN 10 bp with 60-minute blocks. Then MIN 10 bp, 10-minute blocks, year by year."""
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

D = tape.ROOT / "interim" / "tape" / "BTCUSDT"
S = pl.read_parquet(tape.ROOT / "interim" / "l15_sweeps.parquet")
m1 = pl.scan_parquet(sorted(D.glob("*/m1.parquet"))).select("time", "close").collect().sort("time")
t0 = m1["time"][0]; n = int((m1["time"][-1] - t0).total_seconds() // 60) + 1
g = pl.DataFrame({"time": pl.datetime_range(t0, t0 + timedelta(minutes=n - 1), "1m", eager=True)}).join(m1, on="time", how="left").sort("time").with_columns(pl.col("close").forward_fill())
lp = np.log(g["close"].to_numpy()); r1 = np.r_[0.0, np.diff(lp)]
rv60 = np.convolve(r1 ** 2, np.ones(60), "full")[:n]; med = pl.Series(rv60).rolling_median(28 * 1440, min_samples=7 * 1440).shift(1).to_numpy()
dvar = pl.Series(r1 ** 2).rolling_sum(1440).rolling_median(28 * 1440, min_samples=7 * 1440).shift(1).to_numpy()
trend_all = np.full(n, np.nan); trend_all[3 * 1440:] = (lp[3 * 1440:] - lp[:-3 * 1440]) / np.sqrt(dvar[3 * 1440:] * 3)
reg_all = rv60 / med
t0ms = int(np.datetime64(t0, "ms").astype(np.int64))

i = (S["time_ms"].to_numpy() - t0ms) // 60_000 - 1                             # the minute before the sweep
ok = (i >= 3 * 1440) & (i < n); S = S.filter(pl.Series(ok)); i = i[ok]
S = S.with_columns(pl.Series("trend", trend_all[i]), pl.Series("reg", reg_all[i]), (pl.col("time_ms") // 86_400_000).alias("day"),
                   pl.from_epoch("time_ms", time_unit="ms").dt.year().alias("year")).filter(pl.col("reg").is_finite() & pl.col("trend").is_finite())
t1, t2 = np.quantile(S["reg"].to_numpy(), [1 / 3, 2 / 3])                     # the same regime cut-offs as l15_sweeps_matrix.py
VOL = pl.when(pl.col("reg") < t1).then(pl.lit("calm")).when(pl.col("reg") < t2).then(pl.lit("normal")).otherwise(pl.lit("volatile"))
S = S.filter(pl.col("trend").abs() >= 0.5).with_columns(
    pl.when(pl.col("trend").sign() == pl.col("side")).then(pl.lit("with")).otherwise(pl.lit("against")).alias("rel"), VOL.alias("vol"),
    *[(pl.col("trend").sign() * (pl.col(f"p_{h}") / pl.col("p_last")).log() * 1e4).alias(f"r_{h}") for h in ("10m", "1h")])

# baseline: every 10th minute with a clear trend
j = np.arange(3 * 1440, n - 60, 10); j = j[np.isfinite(trend_all[j]) & np.isfinite(reg_all[j]) & (np.abs(np.nan_to_num(trend_all[j])) >= 0.5)]
sg = np.sign(trend_all[j])
B = pl.DataFrame({"trend": trend_all[j], "reg": reg_all[j], "day": (t0ms // 60_000 + j) // 1440,
                  "year": pl.Series(g["time"].to_numpy()[j]).dt.year(), "r_10m": sg * (lp[j + 10] - lp[j]) * 1e4, "r_1h": sg * (lp[j + 60] - lp[j]) * 1e4}).with_columns(VOL.alias("vol"))


def clustered(df, col):
    """Mean and its standard error with days as clusters."""
    x = df.drop_nulls(col).filter(pl.col(col).is_finite())
    if x.height < 3: return float("nan"), float("nan"), x.height
    d = x.group_by("day").agg(pl.col(col).sum().alias("s"), pl.len().alias("k"))
    m = d["s"].sum() / d["k"].sum(); e = d["s"].to_numpy() - m * d["k"].to_numpy(); G = d.height
    return float(m), float(math.sqrt(G / (G - 1) * (e ** 2).sum()) / d["k"].sum()), x.height


def bh(p):
    p = np.asarray(p); o = np.argsort(p); q = p[o] * len(p) / np.arange(1, len(p) + 1)
    q = np.minimum.accumulate(q[::-1])[::-1]; out = np.empty_like(q); out[o] = np.minimum(q, 1); return out


def variant(MIN, BLK):
    X = (S.filter(pl.col("move_bp") >= MIN).sort("time_ms").with_columns((pl.col("time_ms") // (BLK * 60_000)).alias("blk"))
         .unique(subset="blk", keep="first", maintain_order=True))
    rows = []
    for rl in ("against", "with"):
        for vl in ("calm", "normal", "volatile"):
            c = X.filter((pl.col("rel") == rl) & (pl.col("vol") == vl)); b = B.filter(pl.col("vol") == vl)
            for h in ("10m", "1h"):
                ms, ss, ns = clustered(c, f"r_{h}"); mb, sb, _ = clustered(b, f"r_{h}"); t = (ms - mb) / math.sqrt(ss ** 2 + sb ** 2)
                rows.append(dict(rel=rl, vol=vl, h=h, n=ns, median=round(float(c[f"r_{h}"].drop_nulls().median()), 1), mean=round(ms, 1),
                                 base_median=round(float(b[f"r_{h}"].median()), 1), base_mean=round(mb, 1), diff=round(ms - mb, 1), t=round(t, 1),
                                 p=math.erfc(abs(t) / math.sqrt(2))))
    for r, q in zip(rows, bh([r["p"] for r in rows])): r["q_bh"] = round(float(q), 4); r["p"] = round(r["p"], 4)
    return X, rows


R = {}
for MIN, BLK in ((5, 10), (10, 10), (20, 10), (10, 60)):
    X, rows = variant(MIN, BLK); R[f"{MIN}bp_{BLK}min"] = rows
    if (MIN, BLK) == (10, 10): X10 = X
years = []
for y in range(2021, 2027):
    for rl in ("against", "with"):
        for vl in ("calm", "normal", "volatile", "all"):
            c = X10.filter((pl.col("year") == y) & (pl.col("rel") == rl) & ((pl.col("vol") == vl) if vl != "all" else pl.lit(True)))
            b = B.filter((pl.col("year") == y) & ((pl.col("vol") == vl) if vl != "all" else pl.lit(True)))
            r = dict(year=y, rel=rl, vol=vl, n=c.height)
            for h in ("10m", "1h"):
                r[f"med_{h}"] = round(float(c[f"r_{h}"].drop_nulls().median()), 1) if c.height else None
                r[f"base_{h}"] = round(float(b[f"r_{h}"].median()), 1) if b.height else None
            years.append(r)
R["by_year_10bp_10min"] = years
(L15_RESULTS / "l15_sweeps_checks.json").write_text(json.dumps(R, indent=1))

if __name__ == "__main__":
    for k in ("5bp_10min", "10bp_10min", "20bp_10min", "10bp_60min"):
        print(f"\n== {k}")
        for r in R[k]:
            print(f"{r['rel']:8}{r['vol']:9}{r['h']:4} n {r['n']:5}  median {r['median']:+6.1f} (base {r['base_median']:+5.1f})  mean {r['mean']:+6.1f} - base {r['base_mean']:+5.1f} = {r['diff']:+6.1f}  t {r['t']:+5.1f}  q {r['q_bh']:.4f}")
    print("\n== by year, 10 bp, 10-min blocks: median return in the trend's direction (baseline)")
    for r in years:
        if r["vol"] in ("all", "volatile"):
            print(f"{r['year']} {r['rel']:8}{r['vol']:9} n {r['n']:5}  10m {r['med_10m']} ({r['base_10m']})  1h {r['med_1h']} ({r['base_1h']})")

# pooled over regimes: sweep mean minus the regime-matched baseline (baseline mean per regime, weighted by the sweeps' regime mix); day-clustered
pooled = []
for MIN, BLK in ((5, 10), (10, 10), (20, 10), (10, 60)):
    X = (S.filter(pl.col("move_bp") >= MIN).sort("time_ms").with_columns((pl.col("time_ms") // (BLK * 60_000)).alias("blk")).unique(subset="blk", keep="first", maintain_order=True))
    for rl in ("against", "with"):
        c = X.filter(pl.col("rel") == rl)
        for h in ("10m", "1h"):
            bm = {v: clustered(B.filter(pl.col("vol") == v), f"r_{h}") for v in ("calm", "normal", "volatile")}
            w = c.drop_nulls(f"r_{h}").group_by("vol").len(); w = dict(zip(w["vol"], w["len"])); W = sum(w.values())
            base = sum(w[v] / W * bm[v][0] for v in w); sb = math.sqrt(sum((w[v] / W * bm[v][1]) ** 2 for v in w))
            ms, ss, ns = clustered(c, f"r_{h}"); t = (ms - base) / math.sqrt(ss ** 2 + sb ** 2)
            pooled.append(dict(min_bp=MIN, block=BLK, rel=rl, h=h, n=ns, mean=round(ms, 1), base=round(base, 1), diff=round(ms - base, 1), t=round(t, 1), p=math.erfc(abs(t) / math.sqrt(2))))
for r, q in zip(pooled, bh([r["p"] for r in pooled])): r["q_bh"] = round(float(q), 4); r["p"] = round(r["p"], 5)
R["pooled"] = pooled
(L15_RESULTS / "l15_sweeps_checks.json").write_text(json.dumps(R, indent=1))
print("\n== pooled over regimes (regime-matched baseline), BH over all 16")
for r in pooled: print(f"{r['min_bp']:3}bp {r['block']:3}min {r['rel']:8}{r['h']:4} n {r['n']:5} mean {r['mean']:+6.1f} base {r['base']:+5.1f} diff {r['diff']:+6.1f} t {r['t']:+5.1f} q {r['q_bh']:.4f}")
