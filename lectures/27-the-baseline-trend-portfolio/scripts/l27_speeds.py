"""Lecture 27, blending the speeds inside each market (results/hypotheses.md, restructure 2026-11-14). At each year end 2012-2025, on in-sample
data only:
  correlation  the 36 streams' gross daily returns, standardised per market, averaged over the markets above the floor with each asset class
               the same total weight;
  cost         each held stream's marginal cost in the combined position (5 bp x its contribution to the blend's turnover, so fast and slow
               trades net), a year, per unit of its risk: Sharpe-ratio units, median over the markets;
  blends       equal per stream (the rule); correlation only (equal risk contributions); correlation and cost (risk budget = PRIOR - cost).
Each blend is traded the following year exactly as the rule: markets equal risk in a class, classes equal risk, total scaled yearly.
Usage: python l27_speeds.py. Output: results/speeds.json, OUT/l27_speeds_daily.parquet."""
import json, sys, warnings; warnings.filterwarnings("ignore")
from pathlib import Path
import numpy as np, pandas as pd
from scipy.optimize import minimize
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l27 as M
L26, L25 = M.L26, M.L25
PRIORS = (0.2, 0.3, 0.5); PRIOR = 0.3


def erc(C, b):
    """Weights with risk contributions proportional to b on correlation C (minimise w'Cw/2 - sum b log w, then normalise)."""
    b = np.asarray(b, float) / np.sum(b); n = len(b)
    f = lambda w: (0.5 * w @ C @ w - b @ np.log(w), C @ w - b / w)
    r = minimize(f, np.ones(n) / n, jac=True, bounds=[(1e-9, None)] * n, method="L-BFGS-B", options=dict(maxiter=2000, gtol=1e-12))
    w = r.x / r.x.sum(); rc = w * (C @ w); return w, rc / rc.sum()


def bets(C, w):
    return float(w.sum() ** 2 / (w @ C @ w))                                             # effective number of independent streams (unit risk)


if __name__ == "__main__":
    close, high, low, dv, rf = L26.load_daily(); D = L26.OUT / "streams"
    G = {t: pd.read_parquet(D / f"{t}.parquet")[L26.START:] for t in close.columns if (D / f"{t}.parquet").exists()}
    NET = {t: L26.net(G[t]) for t in G}
    universe = M.UNI; names = sorted({t for y in range(2012, 2026) for k, mk in universe[str(y)]["sc_div"].items() for t in mk})
    X = {}
    for t in names:
        c = close[t].dropna(); X[t] = L26.excess(c, high[t].reindex(c.index), low[t].reindex(c.index), rf)
    out = {"reviews": {}}; days = []
    for y in range(2012, 2026):
        end = pd.Timestamp(f"{y}-12-31"); liq = L25.liquidity(dv, end); hist, nxt = slice(f"{y - 2}-01-01", f"{y}-12-31"), slice(f"{y + 1}-01-01", f"{y + 1}-12-31")
        held = [k for k, v in M.SEL[str(y)]["weights"]["one_set"].items() if v >= 0.2]
        ok = [t for t in G if liq.get(t, 0) >= L25.FLOOR and G[t].loc[:end].shape[0] >= 756]
        Cs, wts, cost = [], [], {}
        for t in ok:
            g = G[t].loc[:end, [f"g_{k}" for k in L26.STREAMS]]; g.columns = L26.STREAMS; Cs.append(g.corr().to_numpy()); wts.append(L26.CLASS[t])
        cls = pd.Series(wts); cw = (1 / cls.map(cls.value_counts())).to_numpy(); cw = cw / cw.sum()
        C36 = pd.DataFrame(np.nansum([c * w for c, w in zip(Cs, cw)], axis=0), L26.STREAMS, L26.STREAMS); C = C36.loc[held, held].to_numpy()
        # marginal cost in the equal-weight blend, from the positions (rebuilt for the OOS markets only, which are the ones traded)
        mc = []
        for t in [t for t in names if t in ok]:
            P = M.positions(*X[t]).loc[:end, held].iloc[-756:]; B = P.mean(axis=1); s = np.sign(B.diff()).fillna(0)
            dmarg = P.diff().fillna(0).mul(s, axis=0).sum()                                         # d turnover / d weight, per stream
            risk = G[t].loc[P.index, [f"g_{k}" for k in held]].std().to_numpy() * np.sqrt(252)
            mc.append(L26.COST_BP / 1e4 * dmarg.to_numpy() * 252 / len(P) / risk)
        c_s = pd.Series(np.median(mc, axis=0), held)
        W = {"equal": pd.Series(1.0 / len(held), held)}
        # maximum Sharpe ratio, long only, on the in-sample Sharpe ratios after costs pooled as the correlation (a demonstration of the error maximiser)
        mu = pd.Series(np.nansum([NET[t].loc[:end, held].apply(L26.sharpe).to_numpy() * w for t, w in zip(ok, cw)], axis=0), held)
        neg = lambda w: -(w @ mu.to_numpy()) / np.sqrt(w @ C @ w)
        r = minimize(neg, np.ones(len(held)) / len(held), bounds=[(0, 1)] * len(held), constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1}], method="SLSQP")
        W["max_sharpe"] = pd.Series(r.x, held).clip(lower=0) / pd.Series(r.x, held).clip(lower=0).sum()
        w, rc = erc(C, np.ones(len(held))); W["correlation"] = pd.Series(w, held)
        for p in PRIORS:
            b = p - c_s
            if (b <= 0).any(): print(y, "budget not positive for", list(b[b <= 0].index), "at prior", p)
            w, rc = erc(C, np.maximum(b.to_numpy(), 1e-6) if (b <= 0).any() else b.to_numpy()); W[f"cost_{p}"] = pd.Series(w, held)
        out["reviews"][str(y)] = dict(held=held, cost=c_s.round(4).to_dict(), weights={k: v.round(4).to_dict() for k, v in W.items()}, sharpe_in_sample=mu.round(3).to_dict(),
                                      bets={k: bets(C, v.to_numpy()) for k, v in W.items()}, corr=C36.round(3).to_dict())
        # out of sample: the rule's portfolio with each blend
        uni = universe[str(y)]["sc_div"]; row = {}
        for k, wk in W.items():
            R = pd.DataFrame({t: (NET[t][held] * wk).sum(axis=1) for k2 in uni for t in uni[k2]}); a = 1 / R.loc[hist].std(); parts = {}
            for k2, mk in uni.items():
                full = R[mk].mul(a[mk]).mean(axis=1); parts[k2] = full * (M.TARGET / np.sqrt(252)) / full.loc[hist].std()
            U = pd.DataFrame(parts).mean(axis=1); row[k] = (U * (M.TARGET / np.sqrt(252)) / U.loc[hist].std()).loc[nxt]
        days.append(pd.DataFrame(row))
        print(y, len(ok), "markets |", "bets:", {k: round(v, 2) for k, v in out["reviews"][str(y)]["bets"].items()}, "| cost range", round(c_s.min(), 3), round(c_s.max(), 3), flush=True)
    Dd = pd.concat(days); Dd.to_parquet(M.OUT / "l27_speeds_daily.parquet")
    out["oos"] = {k: L26.sharpe(Dd[k]) for k in ["equal", "correlation", "max_sharpe"] + [f"cost_{p}" for p in PRIORS]}
    (M.RESULTS / "speeds.json").write_text(json.dumps(out, indent=1), encoding="utf-8"); print(out["oos"])
