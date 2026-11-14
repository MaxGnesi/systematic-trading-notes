"""Lecture 27, two legitimate ways to run the same portfolio, out of sample 2013-2026 (OUT/l27_daily.parquet from l27.py): a volatility target
(the rule: the total scaled to 10% on its past three years, so leverage moves with the markets' volatility) and constant leverage (the total
scaled each day so that gross exposure stays at the rule's median of the past three years, so risk moves instead). Proportions are the same.
Reports performance, risk over time, drawdowns, storm-after-calm windows, gross exposure, and each class's share of capital and of risk;
the Sharpe ratio difference with a 90% band (block bootstrap over months). Output: results/leverage.json."""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l27 as M
sharpe = M.L26.sharpe
V = {"rule": "volatility target", "constant_leverage": "constant leverage"}
WINDOWS = {"taper tantrum 2013": ("2013-05-01", "2013-06-28"), "volatility spike Feb 2018": ("2018-01-26", "2018-02-09"),
           "Covid crash 2020": ("2020-02-19", "2020-03-23"), "rate shock 2022": ("2022-01-03", "2022-10-31"), "regional banks Mar 2023": ("2023-03-08", "2023-03-24")}


def drawdowns(x, n=3):
    """The n worst drawdowns that do not overlap: depth, peak, trough, recovery (None if not recovered)."""
    v = (1 + x).cumprod(); dd = v / v.cummax() - 1; out = []; used = pd.Series(False, dd.index)
    for _ in range(n):
        d = dd[~used]
        if d.empty or d.min() >= 0: break
        t = d.idxmin(); pk = v.loc[:t].idxmax(); after = dd.loc[t:]; rec = after[after >= 0].index.min()
        out.append(dict(depth=float(dd.loc[t]), peak=str(pk.date()), trough=str(t.date()), recovered=None if pd.isna(rec) else str(rec.date())))
        used.loc[pk: rec if not pd.isna(rec) else dd.index[-1]] = True
    return out


if __name__ == "__main__":
    D = pd.read_parquet(M.OUT / "l27_daily.parquet"); mo = D.index.to_period("M"); um = mo.unique(); rng = np.random.default_rng(20261113)
    gross = {"rule": D.gross_U * D.ctot, "constant_leverage": D.gross_U * D.lev_scale.shift(1).fillna(D.lev_scale.iloc[0])}
    res = {"profile": {}, "by_year": {}, "drawdowns": {}, "windows": {}}
    for v, nm in V.items():
        x = D[v]; rv = x.rolling(63).std() * np.sqrt(252)
        res["profile"][nm] = dict(sharpe=sharpe(x), return_a_year=float(x.mean() * 252), vol=float(x.std() * np.sqrt(252)),
                                  vol_3m_low=float(rv.quantile(.05)), vol_3m_high=float(rv.quantile(.95)), worst_month=float(x.groupby(mo).sum().min()),
                                  worst_drawdown=drawdowns(x, 1)[0]["depth"], gross_median=float(gross[v].median()), gross_low=float(gross[v].quantile(.05)), gross_high=float(gross[v].quantile(.95)))
        res["by_year"][nm] = {str(y): dict(ret=float(g.sum()), vol=float(g.std() * np.sqrt(252)), gross=float(gross[v].loc[g.index].median())) for y, g in x.groupby(x.index.year)}
        res["drawdowns"][nm] = drawdowns(x)
        res["windows"][nm] = {w: float(x.loc[a:b].sum()) for w, (a, b) in WINDOWS.items()}
    idx = {u: np.where(mo == u)[0] for u in um}; b = []
    for _ in range(2000):
        ii = np.concatenate([idx[um[i]] for i in rng.choice(len(um), len(um))]); b.append(sharpe(D.constant_leverage.iloc[ii]) - sharpe(D.rule.iloc[ii]))
    res["sharpe_difference"] = dict(diff=sharpe(D.constant_leverage) - sharpe(D.rule), ci90=[float(np.quantile(b, .05)), float(np.quantile(b, .95))])
    # each class's share of capital (gross) and of risk (contribution to the variance of the total), the same proportions in both
    sh = {}
    for y, g in D.groupby(D.index.year):
        tot = sum(g[f"ret_{k}"] for k in M.L26.CLASSES); gr = sum(g[f"gross_{k}"] for k in M.L26.CLASSES)
        sh[str(y)] = {k: dict(capital=float((g[f"gross_{k}"] / gr).mean()), risk=float(g[f"ret_{k}"].cov(tot) / tot.var())) for k in M.L26.CLASSES}
    res["class_shares"] = sh; (M.RESULTS / "leverage.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(pd.DataFrame(res["profile"]).round(3).to_string()); print("Sharpe difference (constant leverage - target):", {k: np.round(v, 3) for k, v in res["sharpe_difference"].items()})
    for nm in V.values(): print(nm, res["drawdowns"][nm])
    print(pd.DataFrame(res["windows"]).round(3).to_string())
    print(pd.DataFrame({nm: {y: f"{d['ret']:+.1%} vol {d['vol']:.1%} gross {d['gross']:.1f}" for y, d in res["by_year"][nm].items()} for nm in V.values()}).to_string())
    print(pd.DataFrame({y: {f"{k} {s}": d[k][s] for k in M.L26.CLASSES for s in ("capital", "risk")} for y, d in sh.items()}).round(2).to_string())
