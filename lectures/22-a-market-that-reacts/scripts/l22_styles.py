"""Lecture 22: footprints of trading styles in public trades, one code for the teaching simulation and for Bybit. A taker order is the trades with the same time and side, summed (Lecture 20).
Nothing here sees who traded; the simulation's truth is used only to score the result."""
import numpy as np, polars as pl


def runs(O, cv=0.2, min_n=8, min_gap=1000):
    """H12's runs in a table of taker orders O (t in ms, side, q in BTC, sorted by t): min_n or more consecutive orders of one exact size on one side whose gaps have a coefficient of variation
    below cv and a mean of at least min_gap ms. Greedy: from each order, extend while the gaps stay below cv; a run found, start after it. Returns one row per run, and for each order of O the run it belongs to (-1 if none)."""
    tt, sd, qq = O["t"].to_numpy(), O["side"].to_numpy(), O["q"].to_numpy(); lab = np.full(len(tt), -1); out = []
    o = np.lexsort((tt, qq, sd)); cut = np.nonzero((np.diff(sd[o]) != 0) | (np.diff(qq[o]) != 0))[0] + 1
    for g in np.split(o, cut):
        if len(g) < min_n: continue
        d = np.diff(tt[g]).astype(float); i = 0
        while i <= len(g) - min_n:
            k = i + 1
            while k < len(d) and d[i:k + 1].std() < cv * d[i:k + 1].mean(): k += 1
            if k - i + 1 >= min_n and d[i:k].mean() >= min_gap:
                lab[g[i:k + 1]] = len(out); x = d[i:k]
                out.append(dict(side=int(sd[g[0]]), q=float(qq[g[0]]), n=k - i + 1, gap_s=float(np.median(x)) / 1000, cv=float(x.std() / x.mean()), start=int(tt[g[i]]), end=int(tt[g[k]]), size=float(qq[g[0]]) * (k - i + 1)))
                i = k + 1
            else: i += 1
    return (pl.DataFrame(out) if out else None), lab


def shuffled(O, block=300_000, seed=0):
    """The control of H12: the sizes of the orders permuted within blocks of `block` ms, times and sides kept."""
    r = np.random.default_rng(seed); q = O["q"].to_numpy().copy(); b = O["t"].to_numpy() // block
    for k in np.unique(b):
        i = np.nonzero(b == k)[0]; q[i] = r.permutation(q[i])
    return O.with_columns(pl.Series("q", q))
