"""Lecture 22 §4-5: the hypotheses H1-H6, H9 and H20 as fixed in results/hypotheses.md, out of sample (11 October - 3 November 2025), every curve, fit and boundary from the
in-sample days (20 September - 9 October). Statistics are summed day by day; p-values are one-sided, from 2,000 resamples of the out-of-sample days (the share of resampled statistics
on the wrong side of the null). H7 and H8 need the replay and are in l22_s4_replay.py. Output: results/s4_tests.json. --run recomputes."""
import json, sys
from pathlib import Path
import numpy as np, polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l22 as L, l22_s3_response as S3, l22_hybrid as H
OUT = L.RESULTS / "s4_tests.json"; B = 2000; rng = np.random.default_rng(22)
DAYS = sorted(p.stem for p in (L.OUT / "orders").glob("*.parquet")); IS = S3.in_sample_days(); OOS = [d for d in DAYS if L.OUT_SAMPLE[0] <= d <= L.OUT_SAMPLE[1]]


def fits_in_sample():
    """H5's two models and H20's fifths, from the in-sample days only."""
    agg = {"cls": {}, "xb": {}}; pulls, gaps = [], []
    for d in IS:
        X = S3.net_day(d, extra=["pulls5", "bn_gap"])
        for by in ("cls", "xb"):
            for r in X.filter(pl.col(by).is_not_null()).group_by(by).agg(pl.len(), pl.col("n_m10000").sum(), pl.col("S").log().sum(), pl.col("x").log().sum()).iter_rows():
                a = agg[by].setdefault(r[0], np.zeros(4)); a += np.array(r[1:], float)
        pulls += X.filter((pl.col("S") >= 1) & (pl.col("S") < 5))["pulls5"].drop_nans().to_list(); gaps += X.filter(pl.col("S") >= 1)["bn_gap"].abs().drop_nans().to_list()
    fit = {}
    for by, col in (("cls", 2), ("xb", 3)):
        v = np.array([a for a in agg[by].values()]); R, g = v[:, 1] / v[:, 0], v[:, col] / v[:, 0]; ok = R > 0; d, lc = np.polyfit(g[ok], np.log(R[ok]), 1); fit[by] = (float(np.exp(lc)), float(d))
    return dict(S=fit["cls"], x=fit["xb"], pulls_q=np.quantile(pulls, [0.2, 0.8]).tolist(), gap_q=np.quantile(gaps, [0.2, 0.8]).tolist())


def day_stats(d, F, c10):
    """Everything one out-of-sample day contributes to the tests."""
    X = S3.net_day(d, extra=["pulls5", "bn_gap"]); o = {}
    Rf = pl.read_parquet(L.OUT / "refill" / f"{d}.parquet").filter((pl.col("met") > 0) & (pl.col("probe") == 1000))
    o["h1"] = [Rf.height, float((Rf["near"] >= 0.9 * Rf["met"]).sum()), float((Rf["fixed"] >= 0.9 * Rf["met"]).sum())]
    o["h2"] = {r[0]: [r[1], r[2], r[3]] for r in X.group_by("cls").agg(pl.len(), pl.col("n_m10000").sum(), pl.col("S").log().sum()).iter_rows()}
    Y = X.filter(pl.col("S") >= 5); o["h3"] = [Y.height, float((Y["n_m300000"] - Y["n_m60000"]).sum())]
    o["h4"] = {c: [X.filter(pl.col("cls") == c).height, float(X.filter(pl.col("cls") == c)["n_flow"].sum()), float(X.filter(pl.col("cls") == c)["S"].sum())] for c in ("0.1-1", "5-20")}
    Y = X.filter(pl.col("S") >= 0.1); y = Y["n_m10000"].to_numpy()
    o["h5"] = [len(y), float(((y - F["x"][0] * Y["x"].to_numpy() ** F["x"][1]) ** 2).sum()), float(((y - F["S"][0] * Y["S"].to_numpy() ** F["S"][1]) ** 2).sum())]
    Y = X.filter(pl.col("S") >= 1); y = Y["n_m10000"].to_numpy(); pred = c10[0] * Y["S"].to_numpy() ** c10[1]
    o["h6"] = [len(y), float(((y - pred) ** 2).sum()), float((y ** 2).sum()), float(y.sum()), float(pred.sum())]
    Y = X.filter((pl.col("S") >= 1) & (pl.col("S") < 5)); lo, hi = F["pulls_q"]
    o["h20a"] = dict(top=Y.filter(pl.col("pulls5") >= hi)["cost_bp"].to_list(), bottom=Y.filter(pl.col("pulls5") <= lo)["cost_bp"].to_list())
    Y = X.filter(pl.col("S") >= 1).with_columns(pl.col("bn_gap").abs().alias("g")); lo, hi = F["gap_q"]
    o["h20b"] = {k: [Z.height, float(Z["n_m60000"].sum()), float(Z["n_m1000"].sum())] for k, Z in (("top", Y.filter(pl.col("g") >= hi)), ("bottom", Y.filter(pl.col("g") <= lo)))}
    return o


def h9_day(d, F):
    """Actual over predicted 10 s response of orders of 1 BTC or more, 20:50-22:50 UTC, models in S and in x fitted in sample."""
    X = S3.net_day(d, min_S=1.0); a = L.ms(d, "20:50:00") if hasattr(L, "ms") else None
    t0 = int(np.datetime64(f"{d}T20:50:00", "ms").astype(np.int64)); X = X.filter(pl.col("ts").is_between(t0, t0 + 7_200_000))
    if X.is_empty(): return None
    act = X["n_m10000"].mean(); pS = (F["S"][0] * X["S"] ** F["S"][1]).mean(); px = (F["x"][0] * X["x"] ** F["x"][1]).mean()
    return dict(n=X.height, actual=float(act), ratio_S=float(act / pS), ratio_x=float(act / px))


def boot(stat, days):
    """The statistic on all days and its 2,000 resamples over days."""
    k = [rng.integers(0, len(days), len(days)) for _ in range(B)]
    return stat(list(range(len(days)))), np.array([stat(list(i)) for i in k])


def compute():
    F = fits_in_sample(); c10 = H.fit_response()[10_000]; D = {d: day_stats(d, F, c10) for d in OOS}; days = OOS; R = dict(fits=F, c10=c10, oos=OOS, tests={})
    def p_gt0(st, s): return float(np.mean(s <= 0)), st, np.percentile(s, [2.5, 97.5]).tolist()
    sums = lambda key, i: np.sum([D[days[j]][key] for j in i], axis=0)
    st, s = boot(lambda i: (lambda v: (v[1] - v[2]) / v[0])(sums("h1", i)), days); R["tests"]["H1"] = dict(zip(("p", "stat", "ci"), p_gt0(st, s)), what="share near new best minus share at fixed prices, 90% back within 1 s")
    def delta(i):
        a = {}
        for j in i:
            for c, v in D[days[j]]["h2"].items(): a[c] = a.get(c, np.zeros(3)) + np.array(v)
        v = np.array(list(a.values())); R_ = v[:, 1] / v[:, 0]; g = v[:, 2] / v[:, 0]; ok = R_ > 0; return np.polyfit(g[ok], np.log(R_[ok]), 1)[0]
    st, s = boot(delta, days); R["tests"]["H2"] = dict(p=float(np.mean(s >= 1)), stat=st, ci=np.percentile(s, [2.5, 97.5]).tolist(), what="delta of R(10 s) = c S^delta, below 1")
    st, s = boot(lambda i: (lambda v: -v[1] / v[0])(sums("h3", i)), days); R["tests"]["H3"] = dict(zip(("p", "stat", "ci"), p_gt0(st, s)), what="R(60 s) - R(300 s), orders of 5 BTC or more, bp")
    def h4(i):
        a = {c: np.sum([D[days[j]]["h4"][c] for j in i], axis=0) for c in ("0.1-1", "5-20")}; return a["5-20"][1] / a["5-20"][0] - a["0.1-1"][1] / a["0.1-1"][0]
    st, s = boot(h4, days); R["tests"]["H4"] = dict(zip(("p", "stat", "ci"), p_gt0(st, s)), what="excess same-side size in 1 s: 5-20 BTC minus 0.1-1 BTC, BTC")
    st, s = boot(lambda i: (lambda v: (v[2] - v[1]) / v[0])(sums("h5", i)), days); R["tests"]["H5"] = dict(zip(("p", "stat", "ci"), p_gt0(st, s)), what="MSE of the model in S minus MSE of the model in x, bp^2")
    st, s = boot(lambda i: (lambda v: (v[2] - v[1]) / v[0])(sums("h6", i)), days); R["tests"]["H6"] = dict(zip(("p", "stat", "ci"), p_gt0(st, s)), what="MSE of the plain replay minus MSE of the hybrid at 10 s, bp^2")
    v = sums("h6", range(len(days))); R["tests"]["H6"]["actual_over_predicted"] = float(v[3] / v[4])
    def p90(i, g): return np.percentile(np.concatenate([D[days[j]]["h20a"][g] for j in i]), 90)
    st, s = boot(lambda i: p90(i, "top") - p90(i, "bottom"), days); R["tests"]["H20a"] = dict(zip(("p", "stat", "ci"), p_gt0(st, s)), what="90th percentile of cost, top minus bottom fifth of pulls, bp")
    for g in ("top", "bottom"):
        allc = np.concatenate([D[d]["h20a"][g] for d in days]); R["tests"]["H20a"][g] = dict(n=len(allc), p50=float(np.percentile(allc, 50)), p90=float(np.percentile(allc, 90)), p99=float(np.percentile(allc, 99)))
    def keep(i, g): v = np.sum([D[days[j]]["h20b"][g] for j in i], axis=0); return v[1] / v[2]
    st, s = boot(lambda i: keep(i, "top") - keep(i, "bottom"), days); R["tests"]["H20b"] = dict(zip(("p", "stat", "ci"), p_gt0(st, s)), what="share of the 1 s response left at 60 s, top minus bottom fifth of the gap to Binance")
    R["tests"]["H20b"].update({g: float(keep(range(len(days)), g)) for g in ("top", "bottom")})
    W = {d: h9_day(d, F) for d in DAYS}; W = {d: v for d, v in W.items() if v}; rk = sorted(W, key=lambda d: -W[d]["ratio_S"])
    R["tests"]["H9"] = dict(p=(rk.index(L.CASCADE_DAY) + 1) / len(rk), rank=rk.index(L.CASCADE_DAY) + 1, of=len(rk), cascade=W.get(L.CASCADE_DAY), median_other_ratio_S=float(np.median([W[d]["ratio_S"] for d in W if d != L.CASCADE_DAY])),
                           median_other_ratio_x=float(np.median([W[d]["ratio_x"] for d in W if d != L.CASCADE_DAY])), what="actual over predicted response, 20:50-22:50 UTC: rank of 10 October among the days")
    R["h9_days"] = W
    OUT.write_text(json.dumps(R, default=float), encoding="utf-8")
    return R


if __name__ == "__main__":
    R = compute() if "--run" in sys.argv or not OUT.exists() else json.loads(OUT.read_text(encoding="utf-8"))
    print("fits in sample:", R["fits"], "| c10:", R["c10"])
    for k, v in R["tests"].items(): print(k, {a: (round(b, 4) if isinstance(b, float) else b) for a, b in v.items() if a not in ("cascade",)}, v.get("cascade", ""))
