"""Lecture 15 §3: after a sweep, does the price recover? From data/interim/l15_sweeps.parquet (l15_sweeps.py).
Recovery at horizon h: the move after the sweep against its direction, as a share of the sweep's own move (from the price before it to its last fill):
1 = back where it started, 0 = stays where the sweep left it, negative = keeps going. Conditions known at the sweep (the minute before it):
the slower trend (past three days' return over its typical size, +-0.5; the sweep against it, with it, or no clear trend) and the volatility regime
(last hour's realised variance vs its 28-day median, thirds). Medians per cell; the mean continuation in bp with days as clusters."""
import json, sys
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
t0ms = int(np.datetime64(t0, "ms").astype(np.int64))
i = (S["time_ms"].to_numpy() - t0ms) // 60_000 - 1                           # the minute before the sweep
ok = (i >= 3 * 1440) & (i < n)
S = S.filter(pl.Series(ok)); i = i[ok]
trend = (lp[i] - lp[i - 3 * 1440]) / np.sqrt(dvar[i] * 3); reg = rv60[i] / med[i]
S = S.with_columns(pl.Series("trend", trend), pl.Series("reg", reg), (pl.col("time_ms") // 86_400_000).alias("day")).drop_nulls(["trend", "reg"]).filter(pl.col("reg").is_finite() & pl.col("trend").is_finite())
t1, t2 = np.quantile(S["reg"].to_numpy(), [1 / 3, 2 / 3])
S = S.with_columns(pl.when(pl.col("trend").abs() < 0.5).then(pl.lit("no clear trend"))
                     .when(pl.col("trend").sign() == pl.col("side")).then(pl.lit("with the trend")).otherwise(pl.lit("against the trend")).alias("rel"),
                   pl.when(pl.col("reg") < t1).then(pl.lit("calm")).when(pl.col("reg") < t2).then(pl.lit("normal")).otherwise(pl.lit("volatile")).alias("vol"))
for h in ("10s", "1m", "10m", "1h"):
    S = S.with_columns((pl.col("side") * (pl.col(f"p_{h}") / pl.col("p_last")).log() * 1e4).alias(f"cont_{h}"),
                       ((pl.col(f"p_{h}") - pl.col("p_last")) / (pl.col("p_before") - pl.col("p_last"))).alias(f"rec_{h}"))
R = {"n_sweeps": {}}
for MIN in (5, 10, 20):
    X = S.filter(pl.col("move_bp") >= MIN); R["n_sweeps"][MIN] = X.height; res = {}
    for rl in ("against the trend", "no clear trend", "with the trend"):
        for vl in ("calm", "normal", "volatile"):
            c = X.filter((pl.col("rel") == rl) & (pl.col("vol") == vl)); cell = dict(n=c.height, move_bp=round(float(c["move_bp"].median()), 1))
            for h in ("10s", "1m", "10m", "1h"):
                d = c.drop_nulls(f"cont_{h}").group_by("day").agg(pl.col(f"cont_{h}").mean())[f"cont_{h}"].to_numpy()
                cell[h] = dict(recovery_median=round(float(c[f"rec_{h}"].drop_nulls().median()), 2), cont_bp=round(float(c[f"cont_{h}"].drop_nulls().mean()), 2),
                               t=round(float(d.mean() / (d.std() / np.sqrt(len(d)))), 1) if len(d) > 2 else None)
            res[f"{rl} | {vl}"] = cell
    R[f">= {MIN} bp"] = res
(L15_RESULTS / "l15_sweeps_matrix.json").write_text(json.dumps(R, indent=1))
if __name__ == "__main__":
    print("sweeps:", R["n_sweeps"])
    for k, c in R[">= 10 bp"].items():
        print(f"{k:32} n {c['n']:6} move {c['move_bp']:5} | " + " | ".join(f"{h}: rec {c[h]['recovery_median']:+.2f}, cont {c[h]['cont_bp']:+6.1f} bp (t {c[h]['t']})" for h in ("10s", "1m", "1h")))
