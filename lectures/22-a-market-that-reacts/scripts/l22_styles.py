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


def crossings(M, O, slow=3000, fast=1, after=60, quiet=0, gross=False, day=86_400_000, hour=3_600_000):
    """H11 on a mid M (t in ms on a 1 s grid, mid) and taker orders O (t, side, q): the seconds at which the average of the last `fast` mids crosses the average of the last `slow` (fast=1: the mid itself),
    and the signed taker size in the `after` seconds from each, against matched moments without a crossing within `after` s either side: same day, same hour, same tercile of the mid's move over the last 60 s.
    gross=True counts only the taker size on the crossing's side (buys after a crossing from below), not buys less sells. quiet > 0 keeps only crossings with none in the `quiet` s before (the first of a cluster). Returns one row per crossing: t, d (+1 from below), flow, ctrl (the cell's mean), excess = d (flow - ctrl), in BTC on the side of the crossing."""
    t, x = M["t"].to_numpy(), M["mid"].to_numpy().astype(float); c = np.concatenate(([0.0], np.cumsum(x)))
    avg = lambda w: np.concatenate((np.full(w - 1, np.nan), (c[w:] - c[:-w]) / w))
    s, f = avg(slow), (x if fast == 1 else avg(fast)); above = f > s; ok = ~np.isnan(s)
    cross = np.zeros(len(x), int); i = np.nonzero(ok[1:] & ok[:-1] & (above[1:] != above[:-1]))[0] + 1; cross[i] = np.where(above[i], 1, -1)
    if quiet: i = i[np.concatenate(([True], np.diff(t[i]) > quiet * 1000))]
    ot, sd, q = O["t"].to_numpy(), O["side"].to_numpy(), O["q"].to_numpy(); a, b = np.searchsorted(ot, t, "left"), np.searchsorted(ot, t + after * 1000, "left")
    win = lambda v: (lambda c: c[b] - c[a])(np.concatenate(([0.0], np.cumsum(v))))
    flow, up, dn = win(sd * q), win(q * (sd > 0)), win(q * (sd < 0))
    move = x - np.concatenate((np.full(60, np.nan), x[:-60])); edge = np.nanquantile(move, [1 / 3, 2 / 3]); terc = np.digitize(move, edge)
    near = np.convolve(np.abs(cross), np.ones(2 * after + 1), "same") > 0; cell = (t // day) * 10_000 + (t % day) // hour * 10 + terc
    keep = ok & ~near & ~np.isnan(move) & (t + after * 1000 <= ot[-1])
    C = pl.DataFrame(dict(cell=cell[keep], flow=flow[keep], up=up[keep], dn=dn[keep])).group_by("cell").agg(pl.col("flow").mean().alias("ctrl"), pl.col("up").mean().alias("ctrl_up"), pl.col("dn").mean().alias("ctrl_dn"), pl.len().alias("n_ctrl"))
    if gross: C = C.drop("ctrl")
    X = pl.DataFrame(dict(t=t[i], d=cross[i], flow=np.where(cross[i] > 0, up[i], dn[i]) if gross else flow[i], cell=cell[i], valid=~np.isnan(move[i]) & (t[i] + after * 1000 <= ot[-1]))).filter("valid").join(C, on="cell", how="inner")
    if gross: X = X.with_columns(pl.when(pl.col("d") > 0).then("ctrl_up").otherwise("ctrl_dn").alias("ctrl"))
    return X.with_columns(((pl.col("flow") - pl.col("ctrl")) * (1 if gross else pl.col("d"))).alias("excess")).drop("valid", "ctrl_up", "ctrl_dn")


def marks(O, Q, period=60_000, slow=50, early=3, late=(10, 49), before=2, offset=0):
    """H11 at each mark (a whole `period`) from taker orders O (t, side, q) and published quotes Q (t, bid, ask). trend: the sign of the mid at the mark (the last quote at or before it) against the
    average of the last `slow` such mids. w0, g0: taker flow on the trend's side and taker size in the first `early` s after the mark; wc, gc: the same per second in seconds late[0] to late[1], times
    `early`; sb, sa, sc: the mean spread in the `before` s up to the mark, the `early` s after it and seconds late[0] to late[1]; xb, xa, xc: the same for the share of quotes wider than the narrowest spread (one tick). The excess of H11a is w0 - wc, of H11b xb - xc. offset moves every mark that many ms off the whole period (a fake mark); the seconds
    late[0] to late[1] stay those of the whole period, so a fake mark is compared with the same quiet seconds as the real one and never with the next real mark."""
    qt, bid, ask = Q["t"].to_numpy(), Q["bid"].to_numpy().astype(float), Q["ask"].to_numpy().astype(float); mk = np.arange((qt[0] // period + 1) * period + offset, qt[-1] - (late[1] + 1) * 1000, period)
    j = np.searchsorted(qt, mk, "right") - 1; mid = (bid[j] + ask[j]) / 2; c = np.concatenate(([0.0], np.cumsum(mid))); avg = np.full(len(mid), np.nan); avg[slow - 1:] = (c[slow:] - c[:-slow]) / slow
    tr = np.sign(mid - avg); ot, sd, q = O["t"].to_numpy(), O["side"].to_numpy(), O["q"].to_numpy(); cs, cg = np.concatenate(([0.0], np.cumsum(sd * q))), np.concatenate(([0.0], np.cumsum(q)))
    win = lambda cum, x, a, b, r=0: cum[np.searchsorted(x, mk + r + b, "left")] - cum[np.searchsorted(x, mk + r + a, "left")]
    k = early / (late[1] - late[0] + 1); a0, b0, a1, b1 = 0, early * 1000, late[0] * 1000, (late[1] + 1) * 1000
    sp = ask - bid; cn = np.arange(len(sp) + 1.0); mean_of = lambda v: (lambda cv: lambda a, b, r=0: win(cv, qt, a, b, r) / np.maximum(win(cn, qt, a, b, r), 1))(np.concatenate(([0.0], np.cumsum(v))))
    sm, wd = mean_of(sp), mean_of((sp > sp.min()).astype(float))
    X = pl.DataFrame(dict(t=mk, trend=tr, w0=tr * win(cs, ot, a0, b0), wc=k * tr * win(cs, ot, a1, b1, -offset), g0=win(cg, ot, a0, b0), gc=k * win(cg, ot, a1, b1, -offset),
                          sb=sm(-before * 1000 + 1, 1), sa=sm(1, b0 + 1), sc=sm(a1 + 1, b1 + 1, -offset), xb=wd(-before * 1000 + 1, 1), xa=wd(1, b0 + 1), xc=wd(a1 + 1, b1 + 1, -offset)))
    return X.filter(pl.col("trend").is_not_nan() & (pl.col("trend") != 0))


def placebo(data, fakes=range(10_000, 50_001, 500), unit=86_400_000, **kw):
    """H11's tests: for a list of (O, Q), per `unit` of time (a day), the mean excess over the marks at the whole minute less its mean over fake marks 10 to 50 s after it (every 500 ms), each
    fake still compared with its own minute's quiet seconds; then a one-sided t over units. Returns, for H11a (a), H11b (x) and the size burst (g): the mean difference, t and p, and the number of units."""
    from scipy import stats
    def ex(O, Q, off):
        return marks(O, Q, offset=off, **kw).with_columns(((pl.col("t") - off) // unit).alias("u"), (pl.col("w0") - pl.col("wc")).alias("a"), (pl.col("xb") - pl.col("xc")).alias("x"),
                                                         (pl.col("g0") - pl.col("gc")).alias("g")).group_by("u").agg(pl.col("a", "x", "g").mean())
    D = []
    for i, (O, Q) in enumerate(data):
        F = pl.concat([ex(O, Q, f) for f in fakes]).group_by("u").agg(pl.col("a", "x", "g").mean().name.suffix("_f"))
        D.append(ex(O, Q, 0).join(F, on="u").with_columns(pl.lit(i).alias("run")))
    D = pl.concat(D); out = dict(units=D.height)
    for k in "axg":
        d = (D[k] - D[k + "_f"]).to_numpy(); t = float(d.mean() / d.std(ddof=1) * np.sqrt(len(d))); out[k] = dict(diff=float(d.mean()), t=t, p=float(stats.t.sf(t, len(d) - 1)))
    return out
