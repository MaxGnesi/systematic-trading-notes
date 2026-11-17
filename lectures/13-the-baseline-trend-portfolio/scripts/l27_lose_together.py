"""Lecture 13 §4: do the class trend streams lose together? (results/hypotheses.md, 2026-11-17, plan fixed before any result)

Trend streams only (positioned returns), never the assets: a trend book holds the streams, so the assets' own correlations say little.
Measures: (1) how many of the five streams lose in the same month, against chance (months shuffled per stream);
(2) average pairwise correlation in months when both lose against months when both gain, down minus up with a 12-month block bootstrap;
(3) descriptive: average pairwise correlation in the book's worst and best fifth of months.
Output: results/lose_together.json. Usage: python l27_lose_together.py"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

import l27_regimes as G

RES = Path(__file__).resolve().parent.parent / "results"
rng = np.random.default_rng(0)
S = G.trend_streams(G.classes()).loc[:"2024-12"].dropna()
X = S.to_numpy(); T, n = X.shape
pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]


def count_share(X):
    k = (X < 0).sum(1)
    return float(np.mean(k >= 4)), float(np.mean(k <= 1))          # four or five lose; four or five gain


def down_up(X):
    d, u = [], []
    for i, j in pairs:
        a, b = X[:, i], X[:, j]
        dn, up = (a < 0) & (b < 0), (a > 0) & (b > 0)
        d.append(np.corrcoef(a[dn], b[dn])[0, 1]); u.append(np.corrcoef(a[up], b[up])[0, 1])
    return float(np.mean(d)), float(np.mean(u))


lose4, gain4 = count_share(X)
sh = np.array([count_share(np.column_stack([rng.permutation(X[:, c]) for c in range(n)])) for _ in range(1000)])
dn, up = down_up(X)
boot = []
for _ in range(1000):
    starts = rng.integers(0, T - 12, size=T // 12 + 1)
    idx = np.concatenate([np.arange(s, s + 12) for s in starts])[:T]
    boot.append(np.subtract(*down_up(X[idx])))
lo, hi = np.percentile(boot, [5, 95])
book = X.mean(1); q = np.quantile(book, [0.2, 0.8])


def avg_corr(M):
    C = np.corrcoef(M.T); return float(np.mean([C[i, j] for i, j in pairs]))


out = {"months": T, "first": str(S.index[0].date()), "last": str(S.index[-1].date()),
       "share_4plus_lose": lose4, "share_4plus_lose_chance": float(sh[:, 0].mean()), "p_lose": float(np.mean(sh[:, 0] >= lose4)),
       "share_4plus_gain": gain4, "share_4plus_gain_chance": float(sh[:, 1].mean()), "p_gain": float(np.mean(sh[:, 1] >= gain4)),
       "loss_frequency": dict(zip(S.columns, map(float, (X < 0).mean(0)))),
       "corr_all": avg_corr(X), "corr_down": dn, "corr_up": up, "down_minus_up": dn - up, "band90": [float(lo), float(hi)],
       "corr_book_worst_fifth": avg_corr(X[book <= q[0]]), "corr_book_best_fifth": avg_corr(X[book >= q[1]]),
       "skew_book": float(pd.Series(book).skew())}
(RES / "lose_together.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
for k, v in out.items(): print(k, v if not isinstance(v, float) else round(v, 3))
