"""Lecture 27, when positions lose together (results/hypotheses.md). The rule: Lecture 26's out-of-sample portfolio (volatility only: markets equal
risk within a class, classes equal risk, the total scaled to 10% on its past three years). Rival 1, position-aware risk: the total scaled each day
to 10% on a forecast from today's signed exposures, the markets' six-month volatilities and their weekly correlations over the past three years
shrunk to the identity (Ledoit-Wolf), reached a tenth of the way each day, 5 bp on every change. Rival 2, groups by trend phase: the classes
replaced by five groups from Ward clustering (average linkage as first fixed, also reported) on 1 - concordance of 26-week trend phases (sign ignored), past three years.
Usage: python l27.py [year ...] (default 2012-2025). Output: OUT/l27_daily.parquet, results/portfolios.json."""
import json, os, sys, time, warnings; warnings.filterwarnings("ignore")
from pathlib import Path
import numpy as np, pandas as pd
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform
from sklearn.covariance import ledoit_wolf

LECTURE = Path(__file__).resolve().parents[1]; REPO = LECTURE.parents[1]
sys.path.insert(0, str(REPO / "lectures" / "26-trend-speeds-by-asset-class" / "scripts")); import l26 as L26
L25 = L26.L25
RESULTS = Path(os.environ.get("L27_RESULTS", LECTURE / "results")); FIG = LECTURE / "figures"; RESULTS.mkdir(parents=True, exist_ok=True)
OUT = Path(os.environ.get("L27_OUT", L25.DATA / "l27")); OUT.mkdir(parents=True, exist_ok=True)
PREFIX = os.environ.get("L27_PREFIX", "")
TARGET, LAMBDA, COST_BP, NGROUPS = 0.10, 0.10, 5.0, 5
SEL = json.loads((L26.RESULTS / "select.json").read_text(encoding="utf-8"))["reviews"]
UNI = json.loads((REPO / "lectures" / "25-choosing-the-markets" / "results" / "fill.json").read_text(encoding="utf-8"))["reviews"]


def positions(x, xh, xl):
    """Positions of the 36 streams of one market (the same as Lecture 26's stream_returns, which stores only their returns)."""
    c, hi, lo = x.to_frame("x"), xh.to_frame("x"), xl.to_frame("x"); r = x.pct_change(); out = {}
    vol = np.sqrt((r ** 2).ewm(span=L26.VOL_SPAN, min_periods=60).mean() * 252)
    for h in L26.SPEEDS:
        for name, s in L26.signals(c, hi, lo, h).items():
            target = (s["x"] * L26.VOL_TARGET / vol).fillna(0.0).to_numpy(); pos = np.zeros_like(target)
            for t in range(1, len(target)): pos[t] = pos[t - 1] + L26.LAMBDA * (target[t] - pos[t - 1])
            out[f"{name}_{h}"] = pos
    return pd.DataFrame(out, x.index)


def groups_by_phase(PH, names, end, method="average"):
    """Five groups of markets by clustering on 1 - concordance of trend phases over the past three years (average linkage as fixed; Ward added
    2026-11-13 before the full run, because average linkage left one large group and single markets)."""
    P = PH.loc[:end, names].iloc[-L25.WIN:]
    D = np.array([[0.0 if a == b else 1 - L25.concordance(P, a, b) for b in names] for a in names])
    lab = fcluster(linkage(squareform(D, checks=False), method), NGROUPS, "maxclust"); return {n: f"G{g}" for n, g in zip(names, lab)}


def shrunk_corr(X):
    """Correlation of weekly returns shrunk towards the identity with the Ledoit-Wolf intensity (on standardised returns); and the intensity."""
    Z = (X - X.mean()) / X.std(); S, d = ledoit_wolf(Z.values); s = np.sqrt(np.diag(S)); return pd.DataFrame(S / np.outer(s, s), X.columns, X.columns), float(d)


if __name__ == "__main__":
    years = [int(y) for y in sys.argv[1:]] or list(range(2012, 2026))
    close, high, low, dv, rf = L26.load_daily(); _, _, _, PH, _ = L25.load()
    names = sorted({t for y in years for k, mk in UNI[str(y)]["sc_div"].items() for t in mk})
    X, P, N, R = {}, {}, {}, {}
    t0 = time.time()
    for t in names:
        c = close[t].dropna(); x, xh, xl = L26.excess(c, high[t].reindex(c.index), low[t].reindex(c.index), rf)
        X[t] = x; P[t] = positions(x, xh, xl); N[t] = L26.net(pd.read_parquet(L26.OUT / "streams" / f"{t}.parquet"))
    print(f"{len(names)} markets, positions rebuilt in {time.time() - t0:.0f} s", flush=True)
    W = pd.DataFrame({t: np.log(X[t]).resample("W-FRI").last().diff() for t in names})       # weekly log returns over cash
    VOL = pd.DataFrame({t: np.sqrt((X[t].pct_change() ** 2).ewm(span=L26.VOL_SPAN, min_periods=60).mean()) for t in names})   # daily, six months
    days, info = [], {}
    for y in years:
        end = pd.Timestamp(f"{y}-12-31"); hist = slice(f"{y - 2}-01-01", f"{y}-12-31"); nxt = slice(f"{y + 1}-01-01", f"{y + 1}-12-31")
        w = pd.Series(SEL[str(y)]["weights"]["one_set"]); w = (w >= 0.2).astype(float); w = w[w > 0] / w[w > 0].sum()
        uni = UNI[str(y)]["sc_div"]; mk = [t for k in uni for t in uni[k]]
        R = pd.DataFrame({t: (N[t][w.index] * w).sum(axis=1) for t in mk}); E = pd.DataFrame({t: (P[t][w.index] * w).sum(axis=1) for t in mk})
        a = 1 / R.loc[hist].std()                                                                  # each market at equal risk (past three years)
        out = {}
        for name, grp in (("rule", {t: k for k in uni for t in uni[k]}), ("groups", groups_by_phase(PH, mk, end)), ("ward", groups_by_phase(PH, mk, end, "ward"))):
            G = sorted(set(grp.values())); ret, ex = {}, {}
            for g in G:
                m = [t for t in mk if grp[t] == g]; full = R[m].mul(a[m]).mean(axis=1); c = (TARGET / np.sqrt(252)) / full.loc[hist].std()
                ret[g] = full * c; ex.update({t: E[t] * a[t] / len(m) * c for t in m})
            U = pd.DataFrame(ret).mean(axis=1); ctot = (TARGET / np.sqrt(252)) / U.loc[hist].std()
            if name == "rule": out["rule_parts"] = ret
            out[name] = U * ctot; out[name + "_U"] = U; out[name + "_exp"] = pd.DataFrame(ex) / len(G)            # exposures before the total scale
            if name == "rule": info[str(y)] = {}
            else: info[str(y)][name] = {g: [t for t in mk if grp[t] == g] for g in G}
        # rival 1: the rule's total scaled on a forecast from today's exposures
        C, delta = shrunk_corr(W.loc[:end, mk].iloc[-L25.WIN:].dropna()); info[str(y)]["lw_intensity"] = delta
        q = out["rule_exp"][mk]; D = VOL[mk]                                                       # same column order as the correlations
        fc = np.sqrt(252 * np.einsum("ti,ij,tj->t", (q * D).values, C.values, (q * D).values)); fc = pd.Series(fc, q.index)
        df = pd.DataFrame({"rule": out["rule"], "groups": out["groups"], "ward": out["ward"], "U": out["rule_U"], "forecast_U": fc, "gross_U": q.abs().sum(axis=1), "ctot": (TARGET / np.sqrt(252)) / out["rule_U"].loc[hist].std()})
        df["gross_target"] = float((q.abs().sum(axis=1) * df.ctot.iloc[0]).loc[hist].median())         # constant leverage: the rule's median gross, past three years
        for k in L26.CLASSES:                                                                       # each class's contribution to the rule and its gross exposure
            m = [t for t in mk if t in uni.get(k, [])]
            df[f"ret_{k}"] = out[f"rule_parts"][k] * df.ctot.iloc[0] / len(uni) if m else 0.0
            df[f"gross_{k}"] = q[m].abs().sum(axis=1) * df.ctot.iloc[0] if m else 0.0
        days.append(df.loc[nxt].assign(review=y))
        print(y, f"{len(mk)} markets; LW intensity {delta:.2f}; Ward groups:", " | ".join(" ".join(v) for v in info[str(y)]["ward"].values()), flush=True)
    D = pd.concat(days)
    s = np.zeros(len(D)); tgt = (TARGET / D.forecast_U).to_numpy(); s[0] = tgt[0]
    for i in range(1, len(D)): s[i] = s[i - 1] + LAMBDA * (tgt[i] - s[i - 1])
    c = np.zeros(len(D)); tg = (D.gross_target / D.gross_U).to_numpy(); c[0] = tg[0]                   # constant leverage, reached a tenth of the way each day
    for i in range(1, len(D)): c[i] = c[i - 1] + LAMBDA * (tg[i] - c[i - 1])
    D["lev_scale"] = c; D["constant_leverage"] = D.lev_scale.shift(1).fillna(c[0]) * D.U - COST_BP / 1e4 * D.lev_scale.diff().abs().fillna(0) * D.gross_U
    D["scale"] = s; D["aware"] = D.scale.shift(1).fillna(s[0]) * D.U - COST_BP / 1e4 * D.scale.diff().abs().fillna(0) * D.gross_U   # first day: starts at its target
    D.to_parquet(OUT / "l27_daily.parquet")
    summ = {v: {"sharpe": L26.sharpe(D[v]), "vol": float(D[v].std() * np.sqrt(252))} for v in ("rule", "aware", "groups", "ward", "constant_leverage")}
    (RESULTS / "portfolios.json").write_text(json.dumps({"summary": summ, "reviews": info}, indent=1), encoding="utf-8")
    print(pd.DataFrame(summ).round(3).to_string())
