"""Lecture 19 §3, tests H6, H7, H9-H11 and icebergs (results/hypotheses.md) from the heavy pass (L19_OUT/s3/b2_*), plus the smoothed imbalance from
l19_state, the AUC of I1 by time to the next change (L19_OUT/s3/dt_*), and Benjamini-Hochberg over H1-H13 with l19_s3_stats.json.
Output: l19_s3_stats2.json."""
import json, math, sys
from math import comb
from pathlib import Path
import numpy as np, polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l19 as L19
D = L19.S3
DAYS = sorted(p.stem.replace("b2_", "") for p in D.glob("b2_2*.json"))
INS = [d for d in DAYS if d <= "2025-10-09"]; OOS = [d for d in DAYS if d >= "2025-10-11"]; CASC = "2025-10-10"
LAMS = [0.5, 1, 1.5, 3, 5]; TAUS = [0.25, 0.5, 1, 2, 5]; HLS = [0.2, 0.5, 1, 2, 5]
NB, NBOOT = 4000, 2000; rng = np.random.default_rng(1919)
R1 = json.loads((L19.result_path("l19_s3_stats.json")).read_text())


def hist(score, up, lo=-1, hi=1):
    k = np.clip(((score - lo) / (hi - lo) * NB).astype(int), 0, NB - 1)
    return np.bincount(k[up], minlength=NB), np.bincount(k[~up], minlength=NB)


def auc(hu, hd):
    below = np.cumsum(hd) - hd
    return float((hu * below).sum() + 0.5 * (hu * hd).sum()) / (hu.sum() * hd.sum())


def auc_days(H, ds): return auc(sum(H[d][0] for d in ds), sum(H[d][1] for d in ds))
def boot(ds, f): return np.array([f(list(rng.choice(ds, len(ds)))) for _ in range(NBOOT)])
def sign_p(k, n): return sum(comb(n, j) for j in range(k, n + 1)) / 2 ** n


def logit_fit(X, y, it=30):
    X = np.column_stack([np.ones(len(X)), X]); b = np.zeros(X.shape[1])
    for _ in range(it):
        p = 1 / (1 + np.exp(-X @ b)); W = p * (1 - p)
        b += np.linalg.solve(X.T @ (X * W[:, None]) + 1e-9 * np.eye(len(b)), X.T @ (y - p))
    return b


# one table per day: samples + heavy-pass measures + smoothed I5 + time to the next change
T = {}
for d in DAYS:
    S = pl.read_parquet(D / f"samples_{d}.parquet").join(pl.read_parquet(D / f"b2_samples_{d}.parquet"), on="ts").join(pl.read_parquet(D / f"dt_{d}.parquet"), on="ts", how="left")
    X = pl.read_parquet(L19.STATE / f"{d}.parquet", columns=["ts", "q_bid5", "q_ask5"]).sort("ts").with_columns(
        ((pl.col("q_bid5") - pl.col("q_ask5")) / (pl.col("q_bid5") + pl.col("q_ask5"))).alias("I5"), pl.from_epoch("ts", time_unit="ms").alias("dt"))
    X = X.unique("dt", keep="last").sort("dt")
    X = X.with_columns([pl.col("I5").ewm_mean_by("dt", half_life=f"{int(h * 1000)}ms").alias(f"I5_s{h}") for h in HLS]).select(["ts"] + [f"I5_s{h}" for h in HLS])
    T[d] = S.join(X, on="ts", how="left")
R = {"days": DAYS}
# H6: non-inferiority of each version against plain I5, out of sample
H = {"I5": {d: hist(T[d]["I5"].to_numpy(), T[d]["up"].to_numpy()) for d in DAYS}}
fam = {"distance": [f"I5_l{l}" for l in LAMS], "age": [f"I5_a{t}" for t in TAUS], "smoothed": [f"I5_s{h}" for h in HLS]}
R["H6"] = {}
for f, cols in fam.items():
    out = []
    for c in cols:
        H[c] = {d: hist(T[d][c].fill_null(0).to_numpy(), T[d]["up"].to_numpy()) for d in DAYS}
        bs = boot(OOS, lambda ds: auc_days(H[c], ds) - auc_days(H["I5"], ds))
        out.append({"col": c, "auc_oos": auc_days(H[c], OOS), "auc_in": auc_days(H[c], INS), "auc_casc": auc_days(H[c], [CASC]),
                    "diff_ci": np.quantile(bs, [0.025, 0.975]).tolist(), "p": float(np.mean(bs <= -0.01))})
    R["H6"][f] = {"grid": out, "p": max(o["p"] for o in out)}
R["auc_I5"] = {"oos": auc_days(H["I5"], OOS), "in": auc_days(H["I5"], INS), "casc": auc_days(H["I5"], [CASC])}
# AUC of I1 by number of book updates until the change (how far ahead the forecast is)
R["auc_by_ahead"] = []
for lo, hi in ((1, 2), (2, 3), (3, 6), (6, 20), (20, 10**9)):
    Hh = {d: hist(T[d]["I1"].to_numpy()[m], T[d]["up"].to_numpy()[m]) for d in OOS for m in [((T[d]["n_upd"].fill_null(0).to_numpy() >= lo) & (T[d]["n_upd"].fill_null(0).to_numpy() < hi))]}
    R["auc_by_ahead"].append({"lo": lo, "hi": hi, "auc_oos": auc_days(Hh, OOS), "share": float(sum(Hh[d][0].sum() + Hh[d][1].sum() for d in OOS) / sum(T[d].height for d in OOS))})
# H7: spoof candidates
C = {d: pl.read_parquet(D / f"b2_cand_{d}.parquet") for d in DAYS}
R["H7"] = {"grid": []}
for Q in (2, 5, 10):
    for TT in (1, 2, 5):
        per = []
        for d in DAYS:
            c = C[d].filter((pl.col("add") >= Q) & pl.col("removed") & ~pl.col("traded") & (pl.col("life") <= TT * 1000) & pl.col("d_plain").is_not_nan())
            per.append({"day": d, "n": c.height, "plain": float(c["d_plain"].abs().mean() or 0), "dist": float(c["d_dist"].abs().mean() or 0)})
        k = sum(1 for r in per if r["n"] and r["plain"] > 0); n = sum(1 for r in per if r["n"])
        kd = sum(1 for r in per if r["n"] and r["plain"] > r["dist"])
        R["H7"]["grid"].append({"Q": Q, "T": TT, "per_day": per, "days_age_smaller": k, "days_dist_smaller": kd, "days": n, "p_age": sign_p(k, n), "p_dist": sign_p(kd, n)})
R["H7"]["p"] = max(g["p_age"] for g in R["H7"]["grid"])
R["H7"]["all_large_adds"] = {d: {"n": C[d].height, "removed_no_trade": int(C[d].filter(pl.col("removed") & ~pl.col("traded")).height)} for d in DAYS}
# H9: depth and the next 5 minutes
def partial_spearman(x, y, z):
    rk = lambda a: np.argsort(np.argsort(a)).astype(float)
    x, y, z = rk(x), rk(y), rk(z); Z = np.column_stack([np.ones_like(z), z])
    ex = x - Z @ np.linalg.lstsq(Z, x, rcond=None)[0]; ey = y - Z @ np.linalg.lstsq(Z, y, rcond=None)[0]
    return float(np.corrcoef(ex, ey)[0, 1])
M = {}
for d in DAYS:
    m = pl.read_parquet(D / f"b2_min_{d}.parquet").sort("t").with_columns(((pl.col("bid") + pl.col("ask")) / 2).alias("mid"), (pl.col("depth_b10") + pl.col("depth_a10")).alias("depth"))
    m = m.with_columns((pl.col("mid").shift(-5) - pl.col("mid")).abs().alias("next5"), (pl.col("mid") - pl.col("mid").shift(5)).abs().alias("prev5")).drop_nulls()
    M[d] = m
R["H9_daily"] = {d: partial_spearman(*(M[d][c].to_numpy() for c in ("depth", "next5", "prev5"))) for d in DAYS}
A = pl.concat([M[d] for d in DAYS]); R["H9_pooled"] = partial_spearman(*(A[c].to_numpy() for c in ("depth", "next5", "prev5")))
bs = boot(DAYS, lambda ds: (lambda B: partial_spearman(*(B[c].to_numpy() for c in ("depth", "next5", "prev5"))))(pl.concat([M[d] for d in ds])))
k = sum(1 for v in R["H9_daily"].values() if v < 0)
R["H9_days_neg"] = k; R["H9_p"] = max(float(np.mean(bs >= 0)), sign_p(k, len(DAYS))); R["H9_ci"] = np.quantile(bs, [0.025, 0.975]).tolist()
dec = A.with_columns(pl.col("depth").qcut(10, labels=[str(i) for i in range(10)]).alias("dq")).group_by("dq").agg(pl.col("depth").median(), pl.col("next5").mean(), pl.col("prev5").mean()).sort("depth")
R["H9_deciles"] = dec.to_dicts()
# H10: cancelled vs traded at the best
J = {d: json.loads((D / f"b2_{d}.json").read_text()) for d in DAYS}
R["H10_daily"] = {d: {k: J[d]["queues"]["1"][k] + J[d]["queues"]["-1"][k] for k in ("added", "traded", "cancelled")} for d in DAYS}
k = sum(1 for v in R["H10_daily"].values() if v["cancelled"] > v["traded"]); R["H10_days"] = k; R["H10_p"] = sign_p(k, len(DAYS))
# H11: queue race. Finite by construction: u = ttr_b / (ttr_b + ttr_a), a monotone transform of log(ttr_b / ttr_a); both infinite: 0.5
def u_of(df):
    b, a = df["ttr_b"].to_numpy(), df["ttr_a"].to_numpy(); u = np.full(len(b), 0.5)
    fb, fa = np.isfinite(b), np.isfinite(a)
    u[fb & fa] = b[fb & fa] / (b[fb & fa] + a[fb & fa]); u[~fb & fa] = 1.0; u[fb & ~fa] = 0.0
    return u
Xi = np.concatenate([np.column_stack([T[d]["I1"].to_numpy(), u_of(T[d]) - 0.5]) for d in INS]).astype(float); yi = np.concatenate([T[d]["up"].to_numpy() for d in INS]).astype(float)
b = logit_fit(Xi, yi); lim = abs(b[1]) + abs(b[2]) * 0.5
H11 = {d: hist(b[1] * T[d]["I1"].to_numpy() + b[2] * (u_of(T[d]) - 0.5), T[d]["up"].to_numpy(), -lim, lim) for d in DAYS}
HI1 = {d: hist(T[d]["I1"].to_numpy(), T[d]["up"].to_numpy()) for d in DAYS}
bs = boot(OOS, lambda ds: auc_days(H11, ds) - auc_days(HI1, ds))
R["H11"] = {"coef": b.tolist(), "auc_oos": auc_days(H11, OOS), "auc_I1_oos": auc_days(HI1, OOS), "diff_ci": np.quantile(bs, [0.025, 0.975]).tolist(), "p": float(np.mean(bs <= 0)),
            "share_both_inf": float(np.mean(np.concatenate([u_of(T[d]) == 0.5 for d in OOS])))}
R["icebergs"] = {d: {"refills": J[d]["ice_refills"], "chains3": J[d]["ice_chains"]} for d in DAYS}
# Benjamini-Hochberg over H1-H13 (H6 counted once per family)
P = {"H1": R1["H1_p"], "H2": R1["H2_p"], "H3": R1["H3_p"], "H4": R1["H4_p"], "H5": R1["H5_p"], "H6 distance": R["H6"]["distance"]["p"], "H6 age": R["H6"]["age"]["p"],
     "H6 smoothed": R["H6"]["smoothed"]["p"], "H7": R["H7"]["p"], "H8": R1["H8_p"], "H9": R["H9_p"], "H10": R["H10_p"], "H11": R["H11"]["p"], "H12": R1["H12_p"], "H13": R1["H13_p"]}
ks = sorted(P, key=P.get); m = len(ks); thr = 0
for i, k in enumerate(ks, 1):
    if P[k] <= 0.05 * i / m: thr = i
R["BH"] = {k: {"p": P[k], "reject_null": ks.index(k) < thr} for k in P}
(L19.OUT / "l19_s3_stats2.json").write_text(json.dumps(R, indent=1, default=float))
for k in ("auc_I5", "auc_by_ahead", "H9_pooled", "H9_ci", "H9_days_neg", "H10_days", "H11", "BH"):
    print(k, json.dumps(R[k], default=float)[:900])
for f in fam: print(f, [(o["col"], round(o["auc_oos"], 4), [round(x, 4) for x in o["diff_ci"]]) for o in R["H6"][f]["grid"]])
for g in R["H7"]["grid"]: print("H7", g["Q"], g["T"], sum(r["n"] for r in g["per_day"]), g["days_dist_smaller"], g["days"])
print("ice", sum(v["chains3"] for v in R["icebergs"].values()), sum(v["refills"] for v in R["icebergs"].values()))
