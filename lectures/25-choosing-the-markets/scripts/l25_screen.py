"""Lecture 25, the screen as planned (results/hypotheses.md, fixed 2026-11-13): seven methods on the same weekly returns, yearly reviews 2009-2025,
majority consensus of the 31 variants of methods 1-3, out-of-sample checks, stability, and the descriptive methods (spanning tree, graphical lasso,
downside correlation against the normal benchmark, sell-off weeks). Output: results/screen.json."""
import json, sys, warnings; warnings.filterwarnings("ignore")
from pathlib import Path
import numpy as np, pandas as pd
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import squareform
from scipy.sparse.csgraph import minimum_spanning_tree, shortest_path
from sklearn.covariance import graphical_lasso
from sklearn.metrics import adjusted_rand_score
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l25 as L

RHOS = (0.70, 0.75, 0.80, 0.85, 0.90); LINKS = ("average", "complete", "ward"); REDUND = 0.8


def dist(C): return np.sqrt(np.maximum(2 * (1 - C.values), 0))      # Onnela et al. (2003); the max only removes rounding below zero


def clusters(C, link, rho):
    D = dist(C); np.fill_diagonal(D, 0)
    return fcluster(linkage(squareform(D, checks=False), method=link), t=np.sqrt(2 * (1 - rho)), criterion="distance")


def dr_signed(C, names): return len(names) / np.sqrt(C.loc[names, names].values.sum())


def avg_corr(C): a = C.values; n = len(a); return float((a.sum() - n) / (n * (n - 1)))


def hc_select(C, link, rho, liq, inc):
    lab = pd.Series(clusters(C, link, rho), C.index); sel = set(i for i in inc if i in C.index); flags = []
    for _, g in lab.groupby(lab):
        m = list(g.index)
        if sel & set(m): continue
        ok = [x for x in m if liq.get(x, 0) >= L.FLOOR]; pick = max(ok or m, key=lambda x: liq.get(x, 0))
        if not ok: flags.append(pick)
        sel.add(pick)
    return sel | set(inc), lab, flags


def greedy(C, liq, inc):
    cand = [x for x in C.index if liq.get(x, 0) >= L.FLOOR]; sel = [i for i in inc if i in C.index] or [max(cand, key=lambda x: liq.get(x, 0))]
    cur = dr_signed(C, sel) if len(sel) > 1 else 1.0
    while True:
        best, bv = None, cur
        for x in cand:
            if x not in sel and (v := dr_signed(C, sel + [x])) > bv: best, bv = x, v
        if best is None or bv / cur - 1 < 0.01: break
        sel.append(best); cur = bv
    return set(sel) | set(inc), cur


if __name__ == "__main__":
    rng = np.random.default_rng(L.SEED); close, dv, R, PH, POS = L.load(); R = R[R.index >= "2002-01-01"]
    variants = [("raw", l, r) for l in LINKS for r in RHOS] + [("rmt", l, r) for l in LINKS for r in RHOS] + [("greedy", None, None)]
    vname = lambda v: v[0] if v[0] == "greedy" else f"{v[0]}_{v[1]}_{v[2]:.2f}"
    inc = {vname(v): set() for v in variants}; cons = set(); out = {"reviews": {}}
    for end in L.REVIEWS:
        X = L.window(R, end); C = L.corr(X, L.MINW); liq = L.liquidity(dv, end); Cc, nsig, edge = L.rmt_clean(C, len(X))
        rec = dict(n=len(C), enb=L.enb(C), pdi=L.pdi(C), mp_signif=nsig, mp_edge=edge, sel={}, nclust={}, flags={}); votes = {}
        for v in variants:
            k = vname(v)
            if v[0] == "greedy": s, val = greedy(C, liq, inc[k]); rec["greedy_dr"] = float(val)
            else:
                s, lab, fl = hc_select(C if v[0] == "raw" else Cc, v[1], v[2], liq, inc[k]); rec["nclust"][k] = int(lab.max()); rec["flags"][k] = fl
            inc[k] = s; rec["sel"][k] = sorted(s)
            for x in s: votes[x] = votes.get(x, 0) + 1
        for x in sorted([x for x, c in votes.items() if c > len(variants) / 2 and x not in cons and x in C.index], key=lambda x: (-votes[x], -liq.get(x, 0))):
            if all(C.loc[x, m] < REDUND for m in cons if m in C.index): cons.add(x)
        rec.update(consensus=sorted(cons), votes=votes, liq={x: liq.get(x, 0) for x in C.index})
        out["reviews"][str(end.year)] = rec
        print(end.year, len(C), "enb", round(rec["enb"], 2), "pdi", round(rec["pdi"], 1), "mp", nsig, "clusters raw avg 0.8", rec["nclust"]["raw_average_0.80"], "consensus", len(cons), flush=True)

    # out of sample, next year: selection against random draws of the same size from markets above the floor
    oos = {k: [] for k in ("consensus", "raw_average_0.80", "rmt_average_0.80", "greedy", "random_member")}
    for end in L.REVIEWS[:-1]:
        rec = out["reviews"][str(end.year)]; nxt = R[(R.index > end) & (R.index <= end + pd.DateOffset(years=1))]
        elig = [x for x in rec["liq"] if rec["liq"][x] >= L.FLOOR and nxt[x].notna().sum() >= 40]
        def score(names):
            names = [x for x in names if x in nxt.columns and nxt[x].notna().sum() >= 40]; C1 = L.psd(nxt[names].corr(min_periods=40))
            return L.enb(C1), avg_corr(C1), len(names)
        for k in ("consensus", "raw_average_0.80", "rmt_average_0.80", "greedy"):
            e, a, n = score(rec["consensus"] if k == "consensus" else rec["sel"][k])
            rand = [score(list(rng.choice(elig, size=min(n, len(elig)), replace=False))) for _ in range(300)]
            re_, ra = np.array([r[0] for r in rand]), np.array([r[1] for r in rand])
            oos[k].append(dict(year=end.year + 1, n=n, enb=e, avg_corr=a, rand_enb_med=float(np.median(re_)), enb_pct=float((re_ < e).mean()),
                               rand_corr_med=float(np.median(ra)), corr_pct=float((ra > a).mean())))
        C = L.corr(L.window(R, end), L.MINW); lab = pd.Series(clusters(C, "average", 0.8), C.index)          # extra control: random member per cluster
        rm = [score([rng.choice(list(g.index)) for _, g in lab.groupby(lab)]) for _ in range(100)]; e = score(rec["sel"]["raw_average_0.80"])[0]
        oos["random_member"].append(dict(year=end.year + 1, liquid_rule_enb=e, random_member_enb_med=float(np.median([r[0] for r in rm])),
                                         enb_pct=float((np.array([r[0] for r in rm]) < e).mean())))
    out["oos"] = oos

    # stability: clusters on 2007-2016 against 2017-2026
    A_, B_ = R["2007":"2016"], R["2017":"2026"]; both = [x for x in R.columns if A_[x].notna().sum() >= L.MINW and B_[x].notna().sum() >= L.MINW]
    CA, CB = L.corr(A_[both], L.MINW), L.corr(B_[both], L.MINW); both = [x for x in CA.index if x in CB.index]; CA, CB = CA.loc[both, both], CB.loc[both, both]
    out["stability"] = {f"{l}_{r:.2f}": float(adjusted_rand_score(clusters(CA, l, r), clusters(CB, l, r))) for l in LINKS for r in RHOS}; out["stability_n"] = len(both)

    # whole sample from 2007: counts, spanning tree, graphical lasso, downside correlation, sell-off weeks
    F = R["2007":]; F = F.loc[:, F.notna().sum() >= L.WIN]; CF = L.corr(F, L.MINW); names = list(CF.index)
    out["full"] = dict(n=len(names), enb=L.enb(CF), pdi=L.pdi(CF), mp_signif=L.rmt_clean(CF, len(F))[1],
                       nclust={f"{l}_{r:.2f}": int(clusters(CF, l, r).max()) for l in LINKS for r in (0.3, 0.4, 0.5, 0.6) + RHOS},
                       labels_avg_08={n: int(c) for n, c in zip(names, clusters(CF, "average", 0.8))})
    D = dist(CF); np.fill_diagonal(D, 0); T = minimum_spanning_tree(D).toarray(); T = T + T.T; deg = (T > 0).sum(1); SP = shortest_path(T, directed=False, unweighted=True)
    out["mst"] = {n: dict(degree=int(deg[i]), mean_steps=float(SP[i].mean()), group=L.GROUP.get(n)) for i, n in enumerate(names)}
    out["mst_edges"] = [(names[i], names[j], float(T[i, j])) for i in range(len(names)) for j in range(i + 1, len(names)) if T[i, j] > 0]
    G = F.loc[:, F.notna().all()].dropna(); CG = G.corr(); gl = {}; out["glasso_n"] = len(CG)          # complete cases: a proper sample matrix
    for a in (0.05, 0.1, 0.2, 0.3, 0.5):
        try: _, P = graphical_lasso(CG.values, alpha=a, max_iter=2000, tol=1e-5, enet_tol=1e-6); gl[str(a)] = {n: int((np.abs(P[i]) > 1e-4).sum() - 1) for i, n in enumerate(CG.index)}
        except FloatingPointError as e: gl[str(a)] = str(e)
    out["glasso_degree"] = gl
    Z = (F - F.mean()) / F.std()
    def trunc_corr(rho, n=200_000):
        x = rng.standard_normal(n); y = rho * x + np.sqrt(1 - rho ** 2) * rng.standard_normal(n); m = (x < -1) & (y < -1); return np.corrcoef(x[m], y[m])[0, 1]
    grid = np.linspace(-0.9, 0.95, 38); tc = np.array([trunc_corr(r) for r in grid]); pairs = []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = Z[names[i]], Z[names[j]]; m = a.notna() & b.notna() & (a < -1) & (b < -1)
            if m.sum() < 20: continue
            r_all = float(CF.iloc[i, j])
            pairs.append(dict(a=names[i], b=names[j], ca=L.CLASS[names[i]], cb=L.CLASS[names[j]], all=r_all, down=float(np.corrcoef(a[m], b[m])[0, 1]),
                              normal=float(np.interp(r_all, grid, tc)), n=int(m.sum())))
    out["downside_pairs"] = pairs
    sell = Z["SPY"] < -1; FS = F[sell]; FS = FS.loc[:, FS.notna().sum() >= 40]; CS = L.psd(FS.corr(min_periods=40)); common = [x for x in CS.index if x in CF.index]
    out["stress"] = dict(sell_weeks=int(sell.sum()), n=len(common), clusters_all=int(clusters(CF.loc[common, common], "average", 0.8).max()),
                         clusters_sell=int(clusters(CS.loc[common, common], "average", 0.8).max()))
    (L.RESULTS / "screen.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8"); print("done")
