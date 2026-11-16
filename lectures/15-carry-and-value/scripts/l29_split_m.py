"""Lecture 15 §7: is carry a carry filter on trend in disguise? The rule's monthly return (four groups, futures period) split by market and month:
carry only (markets trend does not trade, or months trend holds nothing there), agree (same side as trend), disagree (against trend).
Trend's markets map onto carry's: euro and yen futures -> EUR, JPY; the 7 commodity futures -> the same; the S&P 500 future -> US equity;
the US Treasury funds -> the US 10-year bond. Trend's position sign: Lecture 13's held speeds averaged, at the end of the month before.
Output: results/split.json."""
import json, os, sys
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); import l29_combined as M, l29_grids as Gr, l29_bonds_g10 as G, l29_split as S0, l29 as L
RESD = Path(os.environ.get("L29_RESULTS", HERE.parent / "results")); RESD.mkdir(parents=True, exist_ok=True)
A, B = "2006-01", "2022-10"
MAP = {("fx", "EUR"): "cme-euro", ("fx", "JPY"): "cme-jpy", ("equity", "US"): "cme-es", ("bonds", "US"): "VFITX",
       **{("commod", t): t for t in L.COMMOD}}


def contributions(W, R, vm=36):
    """Per-market monthly P&L of G.stream before its yearly scaling, and the yearly factor."""
    W = W.div(W.abs().sum(axis=1), axis=0)
    vol = R.rolling(vm, min_periods=24).std().shift(1) * np.sqrt(12)
    pos = (W * G.TARGET / vol).shift(1)
    pnl = pos * R - pos.diff().abs() * G.COST
    r = pnl.sum(axis=1, min_count=1).where(pos.notna().any(axis=1))
    f = pd.Series(np.nan, r.index)
    for y in sorted(set(r.index.year)):
        h = r[(r.index.year >= y - 3) & (r.index.year < y)].dropna()
        if len(h) >= 24: f[r.index.year == y] = (G.TARGET / np.sqrt(12)) / h.std()
    return pnl, pos, f


if __name__ == "__main__":
    Gs = M.groups(); W = {g: Gr.sig(Gs[g]["C"], Gs[g]["R"]) for g in Gs}
    T = S0.trend_positions().resample("ME").last(); T.index = T.index.to_period("M")
    parts, groups = {}, {}
    for g in Gs:
        pnl, pos, f = contributions(W[g], Gs[g]["R"]); groups[g] = (pnl, pos, f)
    gs = pd.DataFrame({g: groups[g][0].sum(axis=1, min_count=1).where(groups[g][1].notna().any(axis=1)) * groups[g][2] for g in Gs})
    n = gs.notna().sum(axis=1); U = gs.mean(axis=1, skipna=True)
    ft = pd.Series(np.nan, U.index)
    for y in sorted(set(U.index.year)):
        h = U[(U.index.year >= y - 3) & (U.index.year < y)].dropna()
        if len(h) >= 24: ft[U.index.year == y] = (G.TARGET / np.sqrt(12)) / h.std()
    acc = {k: pd.Series(0.0, U.index) for k in ("carry only", "agree", "disagree")}
    for g in Gs:
        pnl, pos, f = groups[g]
        for m in pnl:
            x = (pnl[m] * f / n * ft).fillna(0)
            tm = MAP.get((g, m)); tp = T[tm].reindex(U.index).shift(1).fillna(0) if tm in T else pd.Series(0.0, U.index)
            s = np.sign(pos[m].fillna(0)) * np.sign(tp)
            acc["carry only"] += x.where(s == 0, 0); acc["agree"] += x.where(s > 0, 0); acc["disagree"] += x.where(s < 0, 0)
    D = pd.DataFrame(acc).loc[A:B]; tot = D.sum(axis=1); ref = M.scale_total(pd.DataFrame({g: G.stream(W[g], Gs[g]["R"]) for g in Gs}).mean(axis=1, skipna=True)).loc[A:B]
    print(f"check: rebuilt vs rule, corr {tot.corr(ref):.4f}, return a year {tot.mean() * 12:+.2%} vs {ref.mean() * 12:+.2%}")
    out = {k: dict(ret=float(D[k].mean() * 12), share=float(D[k].mean() / tot.mean()), sharpe=float(G.sharpe_m(D[k]))) for k in D}
    for k, v in out.items(): print(f"  {k:10s} return a year {v['ret']:+.2%}  share of carry's return {v['share']:+.0%}  Sharpe {v['sharpe']:+.2f}")
    (RESD / "split.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
