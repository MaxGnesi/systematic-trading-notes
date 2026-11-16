"""Lecture 13, how optimisers choose: three speeds in one market (results/hypotheses.md, 2026-11-16, fixed before any result).

EWMA crossover streams at 43, 89 and 179 days (about 50, 100 and 200), net of 5 bp, each scaled to unit risk on its in-sample volatility.
At every year end 2012-2025 each method sets risk weights on the in-sample window (market start to the review); the weights are
applied the following year. Output: results/optimisers.json, figures/27_optimisers_weights.png, figures/27_optimisers_end.png.
Usage: python l27_optimisers.py"""
import json, sys, warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path[:0] = [str(REPO), str(REPO / "lectures" / "12-trend-speeds-by-asset-class" / "scripts"), str(REPO / "lectures" / "11-choosing-the-markets" / "scripts")]
import l26 as L26                                                                                     # noqa: E402
from trading_models.allocation import EqualRiskContribution, HRPAllocator, NCO, SpectralRiskParity  # noqa: E402

RES, FIG = HERE.parent / "results", HERE.parent / "figures"
SPEEDS, RULE = (43, 89, 179), "ewma"
MARKETS = ("SPY", "USO", "TLT")
YEARS = range(2012, 2026)
NAMES = [f"{s} days" for s in SPEEDS]


def streams(ticker):
    S = pd.read_parquet(L26.OUT / "streams" / f"{ticker}.parquet")
    N = L26.net(S)
    cols = [f"{RULE}_{s}" for s in SPEEDS]
    missing = [c for c in cols if c not in N.columns]
    assert not missing, (ticker, missing, list(N.columns)[:10])
    X = N[cols].copy(); X.columns = NAMES
    return X.dropna()


def corr_of(X):
    return X.corr().to_numpy()


def long_only(obj, n):
    best = None
    for k in range(n + 1):                                                                          # several starts: corners and centre
        x0 = np.full(n, 1 / n) if k == n else np.eye(n)[k] * 0.98 + 0.01
        r = minimize(obj, x0, bounds=[(0, 1)] * n, constraints={"type": "eq", "fun": lambda w: w.sum() - 1}, method="SLSQP")
        if best is None or r.fun < best.fun: best = r
    w = np.clip(best.x, 0, None)                                                                     # SLSQP round-off only (|w| < 1e-9)
    return w / w.sum()


def max_sharpe(C, mu, longonly):
    if not longonly:
        w = np.linalg.solve(C, mu); return w / w.sum()
    return long_only(lambda w: -(w @ mu) / np.sqrt(w @ C @ w), len(mu))


def shrunk(sr, years):
    """Empirical Bayes: keep only the part of the Sharpe ratios' spread that exceeds sampling error (variance 1/years each)."""
    se2 = 1.0 / years
    spread = max(0.0, np.var(sr, ddof=1) - se2)
    k = spread / (spread + se2)
    return sr.mean() + k * (sr - sr.mean()), k


def weights_all(X):
    """Risk weights of every method on the in-sample window X (streams already at unit risk)."""
    C = corr_of(X); n = len(C)
    years = len(X) / 252
    sr = (X.mean() / X.std() * np.sqrt(252)).to_numpy()
    srs, k = shrunk(sr, years)
    W = {
        "Equal weight": np.full(n, 1 / n),
        "Equal risk contributions": EqualRiskContribution().weights(X).to_numpy(),
        "Minimum variance, long only": long_only(lambda w: w @ C @ w, n),
        "Minimum variance, shorts": (lambda w: w / w.sum())(np.linalg.solve(C, np.ones(n))),
        "Maximum Sharpe, long only": max_sharpe(C, sr, True),
        "Maximum Sharpe, shorts": max_sharpe(C, sr, False),
        "Maximum Sharpe, shrunk, long only": max_sharpe(C, srs, True),
        "HRP": HRPAllocator().weights(X).to_numpy(),
        "NCO (equal risk contributions)": NCO(n_clusters=2, inner="erc", outer="erc").weights(X).to_numpy(),
        "Spectral risk parity, long only": SpectralRiskParity(long_only=True).weights(X).to_numpy(),
    }
    return W, sr, k


def pc_shares(w, C):
    lam, v = np.linalg.eigh(C); lam, v = lam[::-1], v[:, ::-1]
    y = v.T @ w; p = lam * y ** 2
    return p / p.sum()


def run(ticker):
    X0 = streams(ticker)
    out = {"weights": {}, "sharpe_in": {}, "shrink_k": {}, "pc": {}, "oos": {}}
    daily = {m: [] for m in [*weights_all(X0.loc[:"2011"])[0]]}
    for y in YEARS:
        ins = X0.loc[: f"{y}"]
        vol = ins.std()
        Xu = ins / vol                                                                               # unit risk in sample
        W, sr, k = weights_all(Xu)
        C = corr_of(Xu)
        out["weights"][y] = {m: [float(v) for v in w] for m, w in W.items()}
        out["sharpe_in"][y] = [float(v) for v in sr]; out["shrink_k"][y] = float(k)
        out["pc"][y] = {m: [float(v) for v in pc_shares(w, C)] for m, w in W.items()}
        nxt = X0.loc[f"{y + 1}"] / vol                                                               # same scaling, next year
        for m, w in W.items():
            daily[m].append(nxt @ w)
    corr_end = corr_of(X0.loc[:"2025"] / X0.loc[:"2025"].std())
    out["corr_end2025"] = corr_end.round(3).tolist()
    for m, parts in daily.items():
        r = pd.concat(parts)
        wts = np.array([out["weights"][y][m] for y in YEARS])
        out["oos"][m] = {"sharpe": float(r.mean() / r.std() * np.sqrt(252)),
                         "eff_speeds": float(np.mean([1 / np.sum((w / np.abs(w).sum()) ** 2) for w in wts])),
                         "weight_change": float(np.mean(np.abs(np.diff(wts, axis=0)).sum(axis=1))),
                         "min_weight": float(wts.min()), "max_weight": float(wts.max())}
    return out


def charts(R):
    from plotly.subplots import make_subplots
    from trading_models.plotting import SERIES, apply_theme, save_figure
    apply_theme()
    spy = R["SPY"]; methods = list(spy["oos"]); cols = [SERIES[0], SERIES[1], SERIES[2]]
    rows = (len(methods) + 1) // 2
    f = make_subplots(rows=rows, cols=2, subplot_titles=methods, vertical_spacing=0.06, horizontal_spacing=0.07, shared_yaxes=True)
    for i, m in enumerate(methods):
        r, c = i // 2 + 1, i % 2 + 1
        W = np.array([spy["weights"][y][m] for y in YEARS])
        for j in range(3):
            f.add_scatter(x=list(YEARS), y=W[:, j], name=NAMES[j], line=dict(color=cols[j], width=2.4), mode="lines+markers",
                          marker=dict(size=5), showlegend=(i == 0), row=r, col=c)
        f.add_hline(y=0, line=dict(color="#898781", width=1), row=r, col=c)
    f.update_yaxes(range=[-0.6, 1.1], tickformat=".0%")
    f.update_layout(title="How each method weights the three speeds on SPY, review by review<br><sup>risk weights set at each year end 2012-2025 on data up to that date; EWMA crossover at 43, 89 and 179 days</sup>",
                    height=260 * rows + 140, width=1100, legend=dict(orientation="h", y=1.03, x=0), margin=dict(t=120))
    save_figure(f, "27_optimisers_weights", FIG)


if __name__ == "__main__":
    R = {t: run(t) for t in MARKETS}
    (RES / "optimisers.json").write_text(json.dumps(R, indent=1), encoding="utf-8")
    charts(R)
    for t in MARKETS:
        print(f"\n== {t}  correlation end-2025 {R[t]['corr_end2025']}  shrink k end-2025 {R[t]['shrink_k'][2025]:.2f}")
        print(f"{'method':38s} {'end-2025 weights':24s} {'range':14s} {'eff':>5s} {'chg':>5s} {'SR oos':>7s}  PC risk end-2025")
        for m, o in R[t]["oos"].items():
            w = R[t]["weights"][2025][m]; pc = R[t]["pc"][2025][m]
            print(f"{m:38s} {' '.join(f'{v:6.1%}' for v in w):24s} {o['min_weight']:5.0%}..{o['max_weight']:4.0%} {o['eff_speeds']:5.2f} {o['weight_change']:5.2f} {o['sharpe']:7.3f}  {' '.join(f'{v:4.0%}' for v in pc)}")
