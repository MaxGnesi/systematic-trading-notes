"""Lecture 20 Section 3: tests H1-H7 (results/hypotheses.md) and the measurements reported beside them. Inputs: L20_OUT/book10 (OFI per second),
L20_OUT/orders (taker orders), L20_OUT/s3/{prop.json, vpin_hours.parquet, hawkes_hours.parquet, leadlag.parquet, puzzle.json}.
Output: L20_OUT/s3/stats.json. Usage: python l20_s3_stats.py"""
import json, sys
from math import comb
from pathlib import Path
import numpy as np, polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l20 as L20

S3 = L20.S3
DAYS = L20.days()
INS = [d for d in DAYS if d <= "2025-10-09"]; OOS = [d for d in DAYS if d >= "2025-10-11"]; CASC = "2025-10-10"
rng = np.random.default_rng(20); NB = 2000
R = {}


def sign_p(k, n):
    """One-sided sign test: P(at least k successes of n | p = 1/2)."""
    return float(sum(comb(n, i) for i in range(k, n + 1)) / 2 ** n)


def spear(x, y): return float(np.corrcoef(pl.Series(x).rank().to_numpy(), pl.Series(y).rank().to_numpy())[0, 1])


def day_boot(days, stat):
    """stat(list of days) -> value; bootstrap over days."""
    return np.array([stat([days[i] for i in rng.integers(0, len(days), len(days))]) for _ in range(NB)])


intervals = L20.intervals                                                  # OFI, TI and the mid per interval: in l20.py, shared with the notebook


def ols(X, y):
    X1 = np.column_stack([np.ones(len(y)), X]); return np.linalg.lstsq(X1, y, rcond=None)[0]


def r2_oos(coef, X, y, ybar):
    pred = np.column_stack([np.ones(len(y)), X]) @ coef; return 1 - ((y - pred) ** 2).sum() / ((y - ybar) ** 2).sum()


for D in (1, 10, 60):
    A = pl.concat([intervals(d, D) for d in DAYS])
    I = A.filter(pl.col("day").is_in(INS)); O_ = A.filter(pl.col("day").is_in(OOS))
    ybar = float(I["dm"].mean()); out = {}
    for name, cols in (("ofi", ["ofi_1"]), ("ti", ["ti"]), ("ofi10", [f"ofi_{j}" for j in range(1, 11)])):
        c = ols(I.select(cols).to_numpy(), I["dm"].to_numpy())
        out[name] = dict(coef=c.tolist(), r2_in=float(r2_oos(c, I.select(cols).to_numpy(), I["dm"].to_numpy(), ybar)),
                         r2_oos=float(r2_oos(c, O_.select(cols).to_numpy(), O_["dm"].to_numpy(), ybar)),
                         r2_casc=float(r2_oos(c, A.filter(pl.col("day") == CASC).select(cols).to_numpy(), A.filter(pl.col("day") == CASC)["dm"].to_numpy(), ybar)))
        out[name]["r2_by_day"] = {d: float(r2_oos(c, g.select(cols).to_numpy(), g["dm"].to_numpy(), float(g["dm"].mean())))
                                  for (d,), g in A.group_by("day") if g.height > 20}
    # daily slope of mid change on OFI (H1 reported) and the forecast (H2)
    out["b_pos_days"] = int(sum(ols(g.select("ofi_1").to_numpy(), g["dm"].to_numpy())[1] > 0 for _, g in A.group_by("day")))
    F = A.drop_nulls("ofi_prev"); FI = F.filter(pl.col("day").is_in(INS)); FO = F.filter(pl.col("day").is_in(OOS))
    cf = ols(FI.select("ofi_prev").to_numpy(), FI["dm"].to_numpy())
    out["forecast"] = dict(coef=cf.tolist(), r2_oos=float(r2_oos(cf, FO.select("ofi_prev").to_numpy(), FO["dm"].to_numpy(), float(FI["dm"].mean()))))
    if D == 10:
        by = {d: g for (d,), g in O_.group_by("day")}; byF = {d: g for (d,), g in FO.group_by("day")}
        cO, cT = out["ofi"]["coef"], out["ti"]["coef"]
        def diff(ds):
            g = pl.concat([by[d] for d in ds]); y = g["dm"].to_numpy()
            return r2_oos(np.array(cO), g.select("ofi_1").to_numpy(), y, ybar) - r2_oos(np.array(cT), g.select("ti").to_numpy(), y, ybar)
        bs = day_boot(OOS, diff); R["H1_p"] = float(np.mean(bs <= 0)); R["H1_ci"] = np.quantile(bs, [0.025, 0.975]).tolist()
        def fc(ds):
            g = pl.concat([byF[d] for d in ds]); return r2_oos(cf, g.select("ofi_prev").to_numpy(), g["dm"].to_numpy(), float(FI["dm"].mean()))
        bs = day_boot(OOS, fc); R["H2_p"] = float(np.mean(bs <= 0)); R["H2_ci"] = np.quantile(bs, [0.025, 0.975]).tolist()
        # b against depth at the best, per half hour (reported); Kyle's lambda per half hour
        A30 = A.with_columns((pl.col("k") * 10 // 1800).alias("hh"))
        rows = []
        for (d, hh), g in A30.group_by("day", "hh"):
            if g.height < 60: continue
            rows.append((d, hh, ols(g.select("ofi_1").to_numpy(), g["dm"].to_numpy())[1], ols(g.select("ti").to_numpy(), g["dm"].to_numpy())[1], float(g["q_best"].mean())))
        W = pl.DataFrame(rows, schema=["day", "hh", "b", "lam", "depth"], orient="row").filter((pl.col("b") > 0) & (pl.col("lam") > 0))
        W.write_parquet(S3 / "halfhours.parquet")
        out["b_depth_slope"] = float(np.polyfit(np.log(W["depth"]), np.log(W["b"]), 1)[0])
        out["lam_depth_slope"] = float(np.polyfit(np.log(W["depth"]), np.log(W["lam"]), 1)[0])
        out["lam_median"] = float(W["lam"].median())
    R[f"D{D}"] = out
    print(D, {k: (round(v["r2_oos"], 3) if isinstance(v, dict) and "r2_oos" in v else v) for k, v in out.items() if k != "r2_by_day"}, flush=True)

# ---- H3: propagator ----
P = json.loads((S3 / "prop.json").read_text())
G = {d: np.array(v["G"]) for d, v in P.items()}
k3 = sum(G[d][499] < G[d][0] for d in DAYS)
R["H3"] = dict(days_G500_below_G1=int(k3), n=len(DAYS), p=sign_p(k3, len(DAYS)),
               days_G500_below_G10=int(sum(G[d][499] < G[d][9] for d in DAYS)),
               peak_lag_median=float(np.median([np.argmax(G[d][:200]) + 1 for d in DAYS])),
               G_ratio_500_to_peak_median=float(np.median([G[d][499] / G[d][:200].max() for d in DAYS])),
               gamma_median=float(np.median([P[d]["gamma"] for d in DAYS])), C1_median=float(np.median([P[d]["C"][1] for d in DAYS])))
R["H3_p"] = R["H3"]["p"]

# ---- H4: VPIN ----
V = pl.read_parquet(S3 / "vpin_hours.parquet").drop_nulls(["vpin", "vpin_bvc", "rv_next", "rv_last", "vol_last"])


def partial_spear(g, x, y, ctrl):
    rk = lambda c: g[c].rank().to_numpy()
    Z = np.column_stack([np.ones(g.height)] + [rk(c) for c in ctrl])
    res = lambda v: v - Z @ np.linalg.lstsq(Z, v, rcond=None)[0]
    return float(np.corrcoef(res(rk(x)), res(rk(y)))[0, 1])


VO = V.filter(pl.col("day").is_in(OOS)); byV = {d: g for (d,), g in VO.group_by("day")}
R["H4"] = dict(partial_true=partial_spear(VO, "vpin", "rv_next", ["rv_last", "vol_last"]), partial_bvc=partial_spear(VO, "vpin_bvc", "rv_next", ["rv_last", "vol_last"]),
               plain_true=spear(VO["vpin"], VO["rv_next"]), plain_bvc=spear(VO["vpin_bvc"], VO["rv_next"]),
               vpin_vs_vol=spear(VO["vpin"], VO["vol_last"]), bvc_vs_rv=spear(VO["vpin_bvc"], VO["rv_last"]), hours=VO.height)
bs = day_boot([d for d in OOS if d in byV], lambda ds: partial_spear(pl.concat([byV[d] for d in ds]), "vpin", "rv_next", ["rv_last", "vol_last"]))
R["H4_p"] = float(np.mean(bs <= 0)); R["H4"]["ci"] = np.quantile(bs, [0.025, 0.975]).tolist()

# ---- H5: Hawkes ----
Hk = pl.read_parquet(S3 / "hawkes_hours.parquet")
byH = {d: g for (d,), g in Hk.group_by("day")}
share = lambda ds: float(np.mean(np.concatenate([(byH[d]["n"] < 0.9).to_numpy() for d in ds])))
bs = day_boot(DAYS, share)
R["H5"] = dict(share_below_09=share(DAYS), n_median=float(Hk["n"].median()), n_q05_q95=Hk["n"].quantile(0.05), hours=Hk.height,
               n_q95=Hk["n"].quantile(0.95), n_ge_1=int((Hk["n"] >= 1).sum()), ci=np.quantile(bs, [0.025, 0.975]).tolist(),
               n_median_ins=float(Hk.filter(pl.col("day").is_in(INS))["n"].median()), n_median_oos=float(Hk.filter(pl.col("day").is_in(OOS))["n"].median()),
               n_median_casc=float(Hk.filter(pl.col("day") == CASC)["n"].median()))
R["H5_p"] = float(np.mean(bs <= 0.5))

# ---- H6: lead and lag ----
LL = pl.read_parquet(S3 / "leadlag.parquet")
peaks = {d: int(g.sort("lag")["lag"][int(np.argmax(g.sort("lag")["rho_last"].to_numpy()))]) for (d,), g in LL.group_by("day")}
peaks_mid = {d: int(g.sort("lag")["lag"][int(np.argmax(g.sort("lag")["rho_mid"].to_numpy()))]) for (d,), g in LL.group_by("day")}
def llr(ds, col="rho_last"):
    m = LL.filter(pl.col("day").is_in(ds)).group_by("lag").agg(pl.col(col).mean()).sort("lag")
    r, l = m[col].to_numpy(), m["lag"].to_numpy(); return float((r[l > 0] ** 2).sum() / (r[l < 0] ** 2).sum())
k6 = sum(peaks[d] > 0 for d in DAYS)
bs = day_boot(OOS, llr)
R["H6"] = dict(peaks=peaks, peaks_mid=peaks_mid, days_lead_pos=int(k6), p_sign=sign_p(k6, len(DAYS)), llr_oos=llr(OOS), llr_ci=np.quantile(bs, [0.025, 0.975]).tolist(),
               llr_ins=llr(INS), llr_mid_oos=llr(OOS, "rho_mid"), peak_median=float(np.median(list(peaks.values()))), peak_mid_median=float(np.median(list(peaks_mid.values()))))
R["H6_p"] = max(R["H6"]["p_sign"], float(np.mean(bs <= 1)))

# ---- H7: the Lecture 19 puzzle ----
Z = json.loads((S3 / "puzzle.json").read_text())
k7 = sum(Z[d]["rho_mid"] > Z[d]["rho_last"] for d in INS)
R["H7"] = dict(days_higher=int(k7), n=len(INS), p=sign_p(k7, len(INS)), rho_last_median=float(np.median([Z[d]["rho_last"] for d in INS])),
               rho_mid_median=float(np.median([Z[d]["rho_mid"] for d in INS])))
R["H7_p"] = R["H7"]["p"]

(S3 / "stats.json").write_text(json.dumps(R, default=float))
print({k: v for k, v in R.items() if k.endswith("_p")})
for k in ("H3", "H4", "H5", "H7"): print(k, R[k])
print("H6", {k: v for k, v in R["H6"].items() if not k.startswith("peaks")})
