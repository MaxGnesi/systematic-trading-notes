"""Lecture 13, how optimisers choose, measures added after the first results (results/hypotheses.md, 2026-11-16): one outcome is not proof.

(1) The ten methods of l27_optimisers.py on the 43/89/179-day EWMA streams in every market with in-sample data before 2010: the distribution
    of each method's out-of-sample Sharpe ratio (2013-2026) minus that of equal risk contributions.
(2) Per market, a 90% block-bootstrap band of that difference (21-day blocks, 500 draws on the out-of-sample days).
(3) Stability as a property of the method: the in-sample history to end-2025 resampled in 21-day blocks (200 draws) in SPY, USO and TLT;
    the spread of each speed's weight across draws. Plus disagreement between methods: how far apart their weights are.
Output: results/optimisers_many.json, figures/27_optimisers_spread.png, figures/27_optimisers_resampled.png. Usage: python l27_optimisers_many.py"""
import json, os, sys, warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import l27_optimisers as O  # noqa: E402

RES, FIG = O.RES, O.FIG
REF = "Equal risk contributions"
rng = np.random.default_rng(20261116)


def blocks(n, size, length):
    k = int(np.ceil(length / size)); starts = rng.integers(0, n - size, k)
    return np.concatenate([np.arange(s, s + size) for s in starts])[:length]


def market(ticker):
    X0 = O.streams(ticker)
    if X0.index[0] > pd.Timestamp("2009-12-31") or X0.index[-1] < pd.Timestamp("2026-06-30"): return None
    daily = {}
    for y in O.YEARS:
        ins = X0.loc[: f"{y}"]; vol = ins.std()
        W, _, _ = O.weights_all(ins / vol)
        nxt = X0.loc[f"{y + 1}"] / vol
        for m, w in W.items(): daily.setdefault(m, []).append(nxt @ w)
    R = pd.DataFrame({m: pd.concat(v) for m, v in daily.items()})
    sr = lambda x: x.mean(axis=0) / x.std(axis=0) * np.sqrt(252)
    base = sr(R.to_numpy())
    ref = list(R.columns).index(REF)
    diff = base - base[ref]
    A = R.to_numpy(); n = len(A); draws = []
    for _ in range(500):
        s = sr(A[blocks(n, 21, n)]); draws.append(s - s[ref])
    lo, hi = np.percentile(np.array(draws), [5, 95], axis=0)
    return {m: dict(diff=float(diff[i]), lo=float(lo[i]), hi=float(hi[i])) for i, m in enumerate(R.columns)}


def resampled(ticker, draws=200):
    X0 = O.streams(ticker).loc[:"2025"]; X0 = X0 / X0.std(); A = X0.to_numpy(); n = len(A)
    out = {}
    for _ in range(draws):
        Xb = pd.DataFrame(A[blocks(n, 21, n)], columns=X0.columns)
        W, _, _ = O.weights_all(Xb)
        for m, w in W.items(): out.setdefault(m, []).append(w)
    full, _, _ = O.weights_all(X0)
    res = {}
    for m, ws in out.items():
        ws = np.array(ws)
        res[m] = dict(full=[float(v) for v in full[m]], mean=[float(v) for v in ws.mean(0)], sd=[float(v) for v in ws.std(0)],
                      p5=[float(v) for v in np.percentile(ws, 5, 0)], p95=[float(v) for v in np.percentile(ws, 95, 0)])
    names = list(full)
    M = np.array([full[m] for m in names])
    dis = {a: {b: float(np.abs(M[i] - M[j]).sum() / 2) for j, b in enumerate(names)} for i, a in enumerate(names)}
    return res, dis


if __name__ == "__main__":
    tickers = sorted(p.stem for p in (O.L26.OUT / "streams").glob("*.parquet"))
    many = {}
    for t in tickers:
        try:
            r = market(t)
        except AssertionError:
            r = None
        if r: many[t] = r
    print(len(many), "markets with data from before 2010")
    methods = list(next(iter(many.values())))
    summ = {}
    for m in methods:
        d = np.array([many[t][m]["diff"] for t in many])
        out_band = sum(1 for t in many if many[t][m]["lo"] > 0 or many[t][m]["hi"] < 0)
        above = sum(1 for t in many if many[t][m]["lo"] > 0); below = sum(1 for t in many if many[t][m]["hi"] < 0)
        summ[m] = dict(median=float(np.median(d)), q1=float(np.percentile(d, 25)), q3=float(np.percentile(d, 75)),
                       share_above=float((d > 0).mean()), outside_band=out_band, above_band=above, below_band=below)
        print(f"{m:38s} median {summ[m]['median']:+.3f}  quartiles {summ[m]['q1']:+.3f} .. {summ[m]['q3']:+.3f}  better in {summ[m]['share_above']:4.0%}  band: {above} above, {below} below")
    rs = {}
    for t in O.MARKETS:
        res, dis = resampled(t); rs[t] = dict(weights=res, disagreement=dis)
        print(f"\n== {t}: resampled weights (mean ± sd, 43/89/179 days)")
        for m, v in res.items():
            print(f"{m:38s} " + "  ".join(f"{a:6.0%}±{s:4.0%}" for a, s in zip(v["mean"], v["sd"])))
    (RES / "optimisers_many.json").write_text(json.dumps(dict(markets=many, summary=summ, resampled=rs), indent=1), encoding="utf-8")
