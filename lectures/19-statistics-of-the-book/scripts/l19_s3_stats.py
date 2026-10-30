"""Lecture 19 §3, light tests H1-H5, H8, H12, H13 (fixed in results/hypotheses.md) from L19_OUT/s3/samples_*.parquet and mk_*.json.
AUC is computed from per-day histograms of the score (4,000 bins), so that the bootstrap over days only adds histograms. Output: l19_s3_stats.json."""
import json, sys
from pathlib import Path
import numpy as np, polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l19 as L19
D = L19.S3
DAYS = sorted(p.stem.replace("samples_", "") for p in D.glob("samples_*.parquet"))
INS = [d for d in DAYS if d <= "2025-10-09"]; OOS = [d for d in DAYS if d >= "2025-10-11"]; CASC = "2025-10-10"
NB, NBOOT = 4000, 2000; rng = np.random.default_rng(19)
S = {d: pl.read_parquet(D / f"samples_{d}.parquet") for d in DAYS}


def logit_fit(X, y, it=30):
    """Logistic regression by Newton's method; X without the constant."""
    X = np.column_stack([np.ones(len(X)), X]); b = np.zeros(X.shape[1])
    for _ in range(it):
        p = 1 / (1 + np.exp(-X @ b)); W = p * (1 - p)
        b += np.linalg.solve(X.T @ (X * W[:, None]) + 1e-9 * np.eye(len(b)), X.T @ (y - p))
    return b


def hist(score, up, lo, hi):
    k = np.clip(((score - lo) / (hi - lo) * NB).astype(int), 0, NB - 1)
    return np.bincount(k[up], minlength=NB), np.bincount(k[~up], minlength=NB)


def auc(hu, hd):
    U, Dn = hu.sum(), hd.sum()
    below = np.cumsum(hd) - hd
    return float((hu * below).sum() + 0.5 * (hu * hd).sum()) / (U * Dn)


def boot(days, stat):
    """stat(list of days) -> number; returns the bootstrap draws over days."""
    return np.array([stat(list(rng.choice(days, len(days)))) for _ in range(NBOOT)])


def arr(d, cols):
    return [S[d][c].to_numpy() for c in cols]


R = {"days": DAYS, "n_samples": {d: S[d].height for d in DAYS}}
# H1: logistic fit in sample; out-of-sample AUC of I1
Xi = np.concatenate([S[d]["I1"].to_numpy() for d in INS]); yi = np.concatenate([S[d]["up"].to_numpy() for d in INS])
b1 = logit_fit(Xi[:, None].astype(float), yi.astype(float)); R["H1_coef"] = b1.tolist()
H_I1 = {d: hist(*arr(d, ["I1", "up"]), -1, 1) for d in DAYS}
def auc_days(H, days): return auc(sum(H[d][0] for d in days), sum(H[d][1] for d in days))
R["auc_I1"] = {"in": auc_days(H_I1, INS), "oos": auc_days(H_I1, OOS), "casc": auc_days(H_I1, [CASC]), "all": auc_days(H_I1, DAYS)}
bs = boot(OOS, lambda ds: auc_days(H_I1, ds)); R["H1_p"] = float(np.mean(bs <= 0.5)); R["auc_I1_oos_ci"] = np.quantile(bs, [0.025, 0.975]).tolist()
# H2: day by day
daily = []
for d in DAYS:
    I, up = arr(d, ["I1", "up"]); bd = logit_fit(I[:, None].astype(float), up.astype(float))
    daily.append({"day": d, "x1": float(bd[1]), "auc": auc(*H_I1[d]), "n": int(len(I))})
R["daily"] = daily
from math import comb
k = sum(1 for r in daily if r["x1"] > 0 and r["auc"] > 0.5); n = len(daily)
R["H2_days_ok"] = k; R["H2_p"] = sum(comb(n, j) for j in range(k, n + 1)) / 2 ** n
# H3: out of sample and 10 Oct (10 Oct: bootstrap over samples within the day)
I, up = arr(CASC, ["I1", "up"]); idx = np.arange(len(I))
bc = np.array([auc(*hist(I[s], up[s], -1, 1)) for s in (rng.choice(idx, len(idx)) for _ in range(NBOOT))])
R["H3_p_casc"] = float(np.mean(bc <= 0.5)); R["H3_p"] = max(R["H1_p"], R["H3_p_casc"]); R["auc_casc_ci"] = np.quantile(bc, [0.025, 0.975]).tolist()
# H4: (I1, I5) vs I1
X2 = np.column_stack([np.concatenate([S[d][c].to_numpy() for d in INS]) for c in ("I1", "I5")]).astype(float)
b2 = logit_fit(X2, yi.astype(float)); R["H4_coef"] = b2.tolist(); lim = abs(b2[1]) + abs(b2[2])
H_2 = {d: hist(b2[1] * S[d]["I1"].to_numpy() + b2[2] * S[d]["I5"].to_numpy(), S[d]["up"].to_numpy(), -lim, lim) for d in DAYS}
R["auc_I1I5"] = {"oos": auc_days(H_2, OOS), "casc": auc_days(H_2, [CASC])}
H_I5 = {d: hist(*arr(d, ["I5", "up"]), -1, 1) for d in DAYS}; R["auc_I5"] = {"oos": auc_days(H_I5, OOS), "in": auc_days(H_I5, INS)}
bs = boot(OOS, lambda ds: auc_days(H_2, ds) - auc_days(H_I1, ds)); R["H4_p"] = float(np.mean(bs <= 0)); R["H4_diff_ci"] = np.quantile(bs, [0.025, 0.975]).tolist()
# H5: by the smaller best queue
BK = [(0, 0.1), (0.1, 1), (1, np.inf)]
H_q = {(d, i): hist(S[d]["I1"].to_numpy()[m], S[d]["up"].to_numpy()[m], -1, 1)
       for d in DAYS for i, (lo, hi) in enumerate(BK) for m in [((S[d]["qmin"].to_numpy() >= lo) & (S[d]["qmin"].to_numpy() < hi))]}
def auc_q(i, ds): return auc(sum(H_q[(d, i)][0] for d in ds), sum(H_q[(d, i)][1] for d in ds))
R["H5_auc"] = {f"{lo}-{hi}": {"oos": auc_q(i, OOS), "in": auc_q(i, INS), "share_oos": float(sum(H_q[(d, i)][0].sum() + H_q[(d, i)][1].sum() for d in OOS) /
               sum(S[d].height for d in OOS))} for i, (lo, hi) in enumerate(BK)}
bs = boot(OOS, lambda ds: auc_q(0, ds) - auc_q(2, ds)); R["H5_p"] = float(np.mean(bs <= 0)); R["H5_diff_ci"] = np.quantile(bs, [0.025, 0.975]).tolist()
# P(up) by 20 bands of I1, in and out of sample (for the chart)
def pup(ds):
    I = np.concatenate([S[d]["I1"].to_numpy() for d in ds]); up = np.concatenate([S[d]["up"].to_numpy() for d in ds]); b = np.clip(((I + 1) / 2 * 20).astype(int), 0, 19)
    return {"I": [float(I[b == k].mean()) for k in range(20)], "p": [float(up[b == k].mean()) for k in range(20)], "n": [int((b == k).sum()) for k in range(20)]}
R["pup"] = {"in": pup(INS), "oos": pup(OOS), "casc": pup([CASC])}
# H8: microprice = mid + g(band of I1), g estimated in sample, for three targets
TG = ["d_next", "d_1s", "d_10s"]
def band(I): return np.clip(((I + 1) / 2 * 20).astype(int), 0, 19)
G = {}
for t in TG:
    I = np.concatenate([S[d]["I1"].to_numpy() for d in INS]); y = np.concatenate([S[d][t].to_numpy() for d in INS]).astype(float); b = band(I)
    G[t] = np.array([y[b == k].mean() for k in range(20)])
R["H8_g"] = {t: G[t].tolist() for t in TG}
SSE = {}
for d in DAYS:
    I = S[d]["I1"].to_numpy().astype(float); g = band(I)
    for t in TG:
        y = S[d][t].to_numpy().astype(float)
        SSE[(d, t)] = np.array([(y ** 2).sum(), ((y - I / 2) ** 2).sum(), ((y - G[t][g]) ** 2).sum(), len(y)])
def mse(ds, t): s = sum(SSE[(d, t)] for d in ds); return s[:3] / s[3]
R["H8_mse"] = {t: {"oos": mse(OOS, t).tolist(), "in": mse(INS, t).tolist(), "casc": mse([CASC], t).tolist()} for t in TG}
ps = []
for t in TG:
    bm = boot(OOS, lambda ds: mse(ds, t)); ps += [float(np.mean(bm[:, 2] >= bm[:, 0])), float(np.mean(bm[:, 2] >= bm[:, 1]))]
    R["H8_mse"][t]["gain_vs_mid_ci"] = np.quantile(1 - bm[:, 2] / bm[:, 0], [0.025, 0.975]).tolist()
R["H8_p"] = max(ps)
# H12, H13: markouts
MK = {d: json.loads((D / f"mk_{d}.json").read_text()) for d in DAYS}
HS = [0, 100, 1000, 10000, 60000]
def mk(ds, bucket=None, spread_one=False):
    rows = [b for d in ds for b in MK[d]["buckets"] if b["spread_one"] == spread_one and (bucket is None or b["lo"] == bucket)]
    q = sum(b["size"] for b in rows); return np.array([sum(b[f"m{h}"] for b in rows) / q for h in HS])
R["markout"] = {k: {"all": mk(ds).tolist(), **{str(lo): mk(ds, lo).tolist() for lo in (0, 0.01, 0.1, 1)}} for k, ds in (("in", INS), ("oos", OOS), ("casc", [CASC]))}
R["markout_spread_one_oos"] = mk(OOS, spread_one=True).tolist()
bm = boot(OOS, lambda ds: mk(ds)); imp = bm[:, [0]] - bm
R["H12_impact_ci"] = {str(h): np.quantile(imp[:, j], [0.025, 0.975]).tolist() for j, h in enumerate(HS)}
R["H12_p"] = float(max(np.mean(imp[:, 2] <= 0), np.mean(imp[:, 3] <= 0)))
def imp10(ds, lo): m = mk(ds, lo); return m[0] - m[3]
bm = boot(OOS, lambda ds: imp10(ds, 1) - imp10(ds, 0)); R["H13_p"] = float(np.mean(bm <= 0)); R["H13_diff_ci"] = np.quantile(bm, [0.025, 0.975]).tolist()
R["H13_imp10_oos"] = {str(lo): imp10(OOS, lo) for lo in (0, 0.01, 0.1, 1)}
(L19.OUT / "l19_s3_stats.json").write_text(json.dumps(R, indent=1, default=float))
for k in ("H1_coef", "auc_I1", "auc_I1_oos_ci", "H1_p", "H2_days_ok", "H2_p", "H3_p_casc", "auc_casc_ci", "H4_coef", "auc_I1I5", "auc_I5", "H4_p", "H4_diff_ci",
          "H5_auc", "H5_p", "H5_diff_ci", "H8_mse", "H8_p", "markout", "markout_spread_one_oos", "H12_impact_ci", "H12_p", "H13_imp10_oos", "H13_p", "H13_diff_ci"):
    print(k, json.dumps(R[k], default=float)[:600])
print("daily auc range", min(r["auc"] for r in daily), max(r["auc"] for r in daily), "x1 range", min(r["x1"] for r in daily), max(r["x1"] for r in daily))
