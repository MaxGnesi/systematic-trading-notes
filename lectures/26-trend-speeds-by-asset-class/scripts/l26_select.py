"""Lecture 26, the rule (results/hypotheses.md, addenda 5-7): at each year end from 2012, 500 random splits of the in-sample quarters and markets
into halves; a stream works on a half if its Sharpe ratio after costs, averaged over that half's markets, is in the top half of the 36; it passes
if it works on both halves; streams are held in proportion to their pass share (weighted union). The rule: within each asset class, each market's vote weighted by the log of its dollar volume (the user); comparisons:
equal votes within the class, and one shared set for all markets. Also the intersection (pass share >= 0.9, equal risk), the union (pass share > 0, equal risk) and all 36 with equal risk.
Out of sample: the next year, on the markets Lecture 25 chose at that review; markets equal risk within a class, classes equal risk (each scaled
on its past three years). Usage: python l26_select.py [year ...] (default 2012-2025). Output: results/select.json, OUT/oos.parquet."""
import json, sys, time, warnings; warnings.filterwarnings("ignore")
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l26 as L
NSPLIT, SEED, MIN_Q = 500, 20261113, 12                                    # splits; seed; a market needs 12 in-sample quarters


def quarter_stats(N):
    """Per stream and quarter: days, sum and sum of squares of daily net returns (N: DataFrame of the 36 streams)."""
    q = N.index.to_period("Q"); g = N.groupby(q)
    return g.count(), g.sum(), (N ** 2).groupby(q).sum()


def pass_share(stats, markets, quarters, rng, vote=None):
    """Share of NSPLIT random halves (of markets and quarters) in which each stream works on both halves."""
    M = len(markets); Q = len(quarters); passed = np.zeros(len(L.STREAMS))
    n = np.stack([stats[m][0].reindex(quarters).fillna(0).to_numpy() for m in markets])     # markets x quarters x streams
    s1 = np.stack([stats[m][1].reindex(quarters).fillna(0).to_numpy() for m in markets])
    s2 = np.stack([stats[m][2].reindex(quarters).fillna(0).to_numpy() for m in markets])
    def works(mi, qi):
        nn, a, b = n[mi][:, qi].sum(1), s1[mi][:, qi].sum(1), s2[mi][:, qi].sum(1)           # markets x streams
        mu = a / np.where(nn > 0, nn, np.nan); sd = np.sqrt(b / np.where(nn > 0, nn, np.nan) - mu ** 2)
        x = mu / sd; v = np.ones(len(mi)) if vote is None else vote[mi]                          # each market's vote (weighted average)
        ok = np.isfinite(x); sh = np.nansum(np.where(ok, x, 0) * v[:, None], 0) / np.maximum((ok * v[:, None]).sum(0), 1e-12)
        return sh >= np.nanmedian(sh)                                                         # top half of the 36
    for _ in range(NSPLIT):
        pm = rng.permutation(M); pq = rng.permutation(Q)
        mA, mB, qA, qB = pm[: M // 2], pm[M // 2:], pq[: Q // 2], pq[Q // 2:]
        passed += works(mA, qA) & works(mB, qB)
    return pd.Series(passed / NSPLIT, L.STREAMS)


def blend(N, w):
    """A market's return from its streams, weighted by w (normalised)."""
    w = w[w > 0]; return (N[w.index] * (w / w.sum())).sum(axis=1) if len(w) else pd.Series(0.0, N.index)


if __name__ == "__main__":
    years = [int(y) for y in sys.argv[1:]] or list(range(2012, 2026)); rng = np.random.default_rng(SEED)
    close, high, low, dv, rf = L.load_daily(); D = L.OUT / "streams"
    N = {t: L.net(pd.read_parquet(D / f"{t}.parquet"))[L.START:] for t in close.columns}
    stats = {t: quarter_stats(N[t]) for t in N}
    universe = json.loads((L.REPO / "lectures" / "25-choosing-the-markets" / "results" / "fill.json").read_text(encoding="utf-8"))["reviews"]
    out = {"reviews": {}}; oos = []
    for y in years:
        t0 = time.time(); end = pd.Timestamp(f"{y}-12-31"); liq = L.L25.liquidity(dv, end)
        quarters = [q for q in pd.period_range(L.START, end, freq="Q")]
        ok = [t for t in N if liq.get(t, 0) >= L.FLOOR and (stats[t][0].reindex(quarters).fillna(0) > 0).iloc[:, 0].sum() >= MIN_Q]
        W = {"shared": pass_share(stats, ok, quarters, rng)}; Weq = {}
        for k in L.CLASSES:
            mk = [t for t in ok if L.CLASS[t] == k]; vote = np.log(np.array([liq[t] for t in mk]))   # log dollar volume: the size-weighted vote
            W[k] = pass_share(stats, mk, quarters, rng, vote) if len(mk) >= 2 else W["shared"]
            Weq[k] = pass_share(stats, mk, quarters, rng) if len(mk) >= 2 else W["shared"]
        rec = {"markets": len(ok), "weights": {k: v.round(3).to_dict() for k, v in W.items()}, "weights_equal_vote": {k: v.round(3).to_dict() for k, v in Weq.items()}}
        out["reviews"][str(y)] = rec
        # out of sample: the next year, Lecture 25's universe for that review
        uni = {k: v for k, v in universe[str(y)]["sc_div"].items()}; nxt = slice(f"{y + 1}-01-01", f"{y + 1}-12-31"); hist = slice(f"{y - 2}-01-01", f"{y}-12-31")
        def variant(name):
            cls = {}
            for k, mk in uni.items():
                wk = {"shared": W["shared"], "class": W[k], "class_equal_vote": Weq[k], "all36": pd.Series(1.0, L.STREAMS),
                      "intersection": (W[k] >= 0.9).astype(float), "union": (W[k] > 0).astype(float)}[name]
                if wk.sum() == 0: wk = pd.Series(1.0, L.STREAMS); rec.setdefault("empty", []).append(f"{name}:{k}")
                R = pd.DataFrame({t: blend(N[t], wk) for t in mk if t in N})
                full = R.div(R.loc[hist].std()).mean(axis=1)                                   # markets at equal risk (past three years)
                cls[k] = full / full.loc[hist].std() * (0.10 / np.sqrt(252))                   # class scaled to 10% a year on the past three years
            P = pd.DataFrame(cls); tot = P.mean(axis=1); tot = tot / tot.loc[hist].std() * (0.10 / np.sqrt(252))
            return pd.concat([P, tot.rename("total")], axis=1).loc[nxt].assign(variant=name)
        for v in ("class", "class_equal_vote", "shared", "all36", "intersection", "union"): oos.append(variant(v))
        top = {k: W[k].sort_values(ascending=False).head(4).round(2).to_dict() for k in ("shared",) + tuple(L.CLASSES)}
        print(y, f"{time.time() - t0:.0f} s", len(ok), "markets |", "; ".join(f"{k}: {', '.join(f'{s}={v}' for s, v in d.items())}" for k, d in top.items()), flush=True)
    O = pd.concat(oos); O.to_parquet(L.OUT / "oos.parquet")
    summ = {}
    for v, g in O.groupby("variant"):
        g = g.drop(columns="variant"); summ[v] = {c: L.sharpe(g[c]) for c in g.columns}
    out["oos_sharpe"] = summ; (L.RESULTS / "select.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(pd.DataFrame(summ).round(2).to_string())
