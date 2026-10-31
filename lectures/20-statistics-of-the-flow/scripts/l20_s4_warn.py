"""Lecture 20 Section 4: the early-warning table (results/hypotheses.md, rule fixed 2026-10-31). Per minute on all 45 days, each indicator of
Lecture 19 (depth in the best 10 levels, spread, refill chains, publish delay) and of this lecture (OFI, TI, VPIN, Hawkes n per 15 min, Kyle's
lambda, pull rate, synchronised pulls). A flag = beyond the 99th percentile of the in-sample days' minutes (below the 1st for depth) for 5 minutes
in a row; it is raised at the end of the fifth minute. Lead time = post time - first flag on 10 Oct in the 6 hours before the post; false alarms =
flag episodes per day on the other 44 days (in sample and out of sample reported apart, since the thresholds come from the in-sample days).
Choices the rule did not fix, made before looking at 10 October: signed flows (OFI, TI) enter as absolute values; every indicator is causal (a
minute uses data up to its end only): VPIN = its last value at a bucket end, Hawkes n = the fit on the last complete 15-minute block, Kyle's lambda =
slope of the mid change on TI over the 10-second intervals of the last 15 minutes; publish delay = 99th percentile of (ts - cts) in the minute;
pull = 5 or more of the best 20 levels on one side lose size beyond trades in one update (Lecture 18), synchronised = on both sides.
Output: L20_OUT/s4/minutes.parquet (and minutes_casc.parquet, 10 October only), L20_OUT/s4/warn.json."""
import json, sys, time
from pathlib import Path
import numpy as np, polars as pl

OUT = L20.S4; L19 = L20.S3_19
from l20_s3_hawkes import fit
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l20 as L20
DAYS = L20.days(); CASC = "2025-10-10"
POST = int(np.datetime64("2025-10-10T20:50:01.702", "ms").astype(np.int64)); M, Q15 = 60_000, 900_000
IND = {"depth": "low", "spread": "high", "chains": "high", "delay": "high", "ofi": "high", "ti": "high", "vpin": "high", "hawkes": "high",
       "kyle": "high", "kyle_sqrt": "high", "kyle_hasb": "high", "pulls": "high", "sync": "high"}

VB = pl.read_parquet(L20.S3 / "vpin_buckets.parquet").sort("t_end").with_columns((2 * pl.col("buy_share") - 1).abs().rolling_mean(window_size=50).alias("vpin")).drop_nulls("vpin")
rows = []; t0 = time.time()
for d in DAYS:
    d0 = int(np.datetime64(f"{d}T00:00:00", "ms").astype(np.int64))
    F = pl.DataFrame({"t": np.arange(d0, d0 + 86_400_000, M, dtype=np.int64)})
    b2 = pl.read_parquet(L19 / f"b2_min_{d}.parquet").select(pl.col("t").cast(pl.Int64), (pl.col("depth_b10") + pl.col("depth_a10")).alias("depth"),
                                                                (pl.col("ask") - pl.col("bid")).alias("spread"))
    ice = pl.read_parquet(L19 / f"b3_ice_{d}.parquet").select((pl.col("t").cast(pl.Int64) // M * M).alias("t")).group_by("t").agg(pl.len().alias("chains"))
    lag = pl.read_parquet(L19 / f"b3_lag_{d}.parquet").select((pl.col("cts") // M * M).alias("t"), "lag").group_by("t").agg(pl.col("lag").quantile(0.99).alias("delay"))
    sec = pl.read_parquet(L20.BOOK10 / f"{d}.parquet", columns=["sec", "ofi_1", "mid2", "reset"]).filter((pl.col("sec") * 1000 >= d0) & (pl.col("sec") * 1000 < d0 + 86_400_000))
    ofi = sec.group_by((pl.col("sec") * 1000 // M * M).alias("t")).agg(pl.col("ofi_1").sum().abs().alias("ofi"))
    O = pl.read_parquet(L20.ORD / f"bybit_{d}.parquet", columns=["ts", "side", "size", "tick"])
    ti = O.group_by((pl.col("ts") // M * M).alias("t")).agg((pl.col("side") * pl.col("size")).sum().abs().alias("ti"))
    pu = pl.read_parquet(L20.PULLS / f"{d}.parquet", columns=["ts", "nb", "na", "pull"]).group_by((pl.col("ts") // M * M).alias("t")).agg(
        pl.col("pull").cast(pl.Float64).mean().alias("pulls"), ((pl.col("nb") >= 5) & (pl.col("na") >= 5)).sum().alias("sync"))
    # Kyle's lambda: 10-second intervals, slope over the last 90 intervals, read at each minute's end
    k = sec.with_columns((pl.col("sec") // 10).alias("k")).group_by("k").agg(pl.col("mid2").last(), pl.col("reset").max()).sort("k")
    k = k.with_columns(((pl.col("mid2") - pl.col("mid2").shift(1)) / 2).alias("dm"), ((pl.col("mid2").log() - pl.col("mid2").shift(1).log()) * 1e4).alias("rbp"))
    tk = O.group_by((pl.col("ts") // 10_000).alias("k")).agg((pl.col("side") * pl.col("size")).sum().alias("x"),
                                                              (pl.col("side") * (pl.col("size") * pl.col("tick") / 10).sqrt()).sum().alias("S"))
    k = k.join(tk, on="k", how="left").with_columns(pl.col("x").fill_null(0.0), pl.col("S").fill_null(0.0)).filter(pl.col("dm").is_not_null() & (pl.col("reset") == 0))
    k = k.with_columns(pl.col("x").rolling_mean(90, min_samples=60).alias("mx"), pl.col("dm").rolling_mean(90, min_samples=60).alias("my"),
                       (pl.col("x") * pl.col("dm")).rolling_mean(90, min_samples=60).alias("mxy"), (pl.col("x") ** 2).rolling_mean(90, min_samples=60).alias("mxx"))
    k = k.with_columns(((pl.col("mxy") - pl.col("mx") * pl.col("my")) / (pl.col("mxx") - pl.col("mx") ** 2)).alias("kyle"), ((pl.col("k") + 1) * 10_000).alias("t_end"))
    # follow-up (added after the results): square-root version, slope of the mid change on sign(TI) * sqrt(|TI|)
    k = k.with_columns((pl.col("x").sign() * pl.col("x").abs().sqrt()).alias("z"))
    k = k.with_columns(pl.col("z").rolling_mean(90, min_samples=60).alias("mz"), (pl.col("z") * pl.col("dm")).rolling_mean(90, min_samples=60).alias("mzy"),
                       (pl.col("z") ** 2).rolling_mean(90, min_samples=60).alias("mzz"))
    k = k.with_columns(((pl.col("mzy") - pl.col("mz") * pl.col("my")) / (pl.col("mzz") - pl.col("mz") ** 2)).alias("kyle_sqrt"))
    # follow-up: Hasbrouck (2009) form, log return of the mid in bp on sum of sign * sqrt(dollar volume) per taker order, no intercept
    k = k.with_columns(((pl.col("rbp") * pl.col("S")).rolling_sum(90, min_samples=60) / (pl.col("S") ** 2).rolling_sum(90, min_samples=60)).alias("kyle_hasb"))
    # Hawkes n per 15-minute block, assigned to the minutes of the next block
    ts = np.unique(O["ts"].to_numpy()); hk = []
    for b in range(96):
        b0 = d0 + b * Q15; x = ts[(ts >= b0) & (ts < b0 + Q15)]
        hk.append((b0 + Q15, fit((x - b0) / 1000.0, Q15 / 1000.0)[2] if len(x) >= 100 else np.nan))
    hk = pl.DataFrame(hk, schema=["t_av", "hawkes"], orient="row")
    F = F.join(b2, on="t", how="left").join(ice, on="t", how="left").join(lag, on="t", how="left").join(ofi, on="t", how="left").join(ti, on="t", how="left").join(
        pu, on="t", how="left").with_columns(pl.col("chains").fill_null(0), pl.col("sync").fill_null(0), (pl.col("t") + M).alias("t_end"), pl.lit(d).alias("day"))
    F = F.sort("t_end").join_asof(VB.select(pl.col("t_end").cast(pl.Int64).alias("tv"), "vpin").sort("tv"), left_on="t_end", right_on="tv", strategy="backward")
    F = F.join_asof(k.select(pl.col("t_end").cast(pl.Int64).alias("tk"), "kyle", "kyle_sqrt", "kyle_hasb").sort("tk"), left_on="t_end", right_on="tk", strategy="backward")
    F = F.join_asof(hk.sort("t_av"), left_on="t_end", right_on="t_av", strategy="backward").drop("tv", "tk", "t_av")
    rows.append(F); print(d, f"{time.time() - t0:.0f} s", flush=True)
A = pl.concat(rows, how="diagonal_relaxed").sort("t"); A.write_parquet(OUT / "minutes.parquet")
A.filter(pl.col("day") == CASC).write_parquet(OUT / "minutes_casc.parquet")                # for figure 20_16

INS = A.filter(pl.col("day") < CASC); R = {"thresholds": {}, "ind": {}}
for c, side in IND.items():
    thr = float(INS[c].drop_nulls().quantile(0.01 if side == "low" else 0.99)); R["thresholds"][c] = thr
    beyond = (A[c] < thr) if side == "low" else (A[c] > thr)
    b = beyond.fill_null(False).to_numpy(); t = A["t"].to_numpy()
    run = np.zeros(len(b), int)
    for i in range(len(b)): run[i] = (run[i - 1] + 1 if i and b[i] and t[i] - t[i - 1] == M else (1 if b[i] else 0))
    flag_at = t[run == 5] + M                                                # flag raised at the end of the fifth minute in a row
    days = A["day"].to_numpy()[run == 5]
    pre = flag_at[(flag_at > POST - 6 * 3_600_000) & (flag_at <= POST)]
    post = flag_at[(flag_at > POST) & (flag_at <= POST + 3_600_000)]
    per_day = {dd: int((days == dd).sum()) for dd in DAYS}
    R["ind"][c] = dict(first_pre=int(pre.min()) if len(pre) else None, lead_min=float((POST - pre.min()) / M) if len(pre) else None, n_pre=int(len(pre)),
                       pre_times=[int(x) for x in pre], first_post_min=float((post.min() - POST) / M) if len(post) else None,
                       fa_ins=float(np.mean([per_day[dd] for dd in DAYS if dd < CASC])), fa_oos=float(np.mean([per_day[dd] for dd in DAYS if dd > CASC])),
                       on_casc=per_day[CASC])
    fmt = lambda x: str(np.datetime64(int(x), "ms"))[11:16]
    print(f"{c:7s} thr {thr:10.3f}  first before post {fmt(pre.min()) if len(pre) else '-':>5}  flags before {len(pre):2d}  "
          f"first after post +{R['ind'][c]['first_post_min']} min  false alarms/day in {R['ind'][c]['fa_ins']:.2f} out {R['ind'][c]['fa_oos']:.2f}  "
          f"times {[fmt(x) for x in pre][:6]}", flush=True)
(OUT / "warn.json").write_text(json.dumps(R))
