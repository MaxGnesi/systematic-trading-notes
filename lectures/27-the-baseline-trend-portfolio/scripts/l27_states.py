"""Lecture 27, descriptive checks of three ideas added after the results (results/hypotheses.md, changes after results); no portfolio profit
and loss is used to choose anything.
  1. strength: average over the markets held of |sum of stream weights x sign of stream position| (1: all speeds agree), relative to its
     median over the past three years; correlated with the position-aware scale relative to the rule's scale (l27_daily.parquet).
  2. four states per market and month end, 2007-2026, all ETFs with streams: six-month volatility below or above its three-year median, by
     six-month efficiency ratio below or above its three-year median; what follows over the next 63 days: realised volatility over the
     six-month volatility, and the return of the 13 streams held at every review in Lecture 26 per unit of their past risk.
  3. calm and stacked, OOS 2013-2026: share of the risk-asset markets (equity, credit, commodities) held long >= 0.8, and the median of their
     six-month volatility over its three-year median < 1; spells of at least 21 days; what follows each over 63 days.
Output: results/states.json."""
import json, sys, warnings; warnings.filterwarnings("ignore")
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l27 as M
L26, L25 = M.L26, M.L25
CORE = [f"{r}_{h}" for r in L26.RULES for h in (61, 89, 127, 179)] + ["ewma_251"]     # held at every review 2012-2025 (Lecture 26 §5)
RISK = ("Equity", "Credit", "Commodities"); H = 63


def er(x, n=126):
    return (x - x.shift(n)).abs() / x.diff().abs().rolling(n).sum()


if __name__ == "__main__":
    close, high, low, dv, rf = L26.load_daily(); out = {}
    # ---- 2. four states per market and month end
    rows = []
    for t in close.columns:
        f = L26.OUT / "streams" / f"{t}.parquet"
        if not f.exists(): continue
        c = close[t].dropna(); x = L26.excess(c, high[t].reindex(c.index), low[t].reindex(c.index), rf)[0]; r = x.pct_change()
        vol = np.sqrt((r ** 2).ewm(span=126, min_periods=60).mean() * 252); e = er(x)
        core = L26.net(pd.read_parquet(f))[CORE].mean(axis=1); risk = core.rolling(756, min_periods=252).std()
        me = x.groupby(x.index.to_period("M")).tail(1).index; me = me[(me >= pd.Timestamp("2007-01-01"))]
        vmed, emed = vol.rolling(756, min_periods=252).median(), e.rolling(756, min_periods=252).median()
        pos = {d: i for i, d in enumerate(x.index)}
        for d in me:
            i = pos[d]
            if i + H >= len(x) or np.isnan(vmed.iloc[i]) or np.isnan(emed.iloc[i]) or np.isnan(risk.iloc[i]): continue
            nxt = slice(i + 1, i + 1 + H)
            rows.append(dict(market=t, cls=L26.CLASS[t], date=d, low_vol=bool(vol.iloc[i] < vmed.iloc[i]), smooth=bool(e.iloc[i] > emed.iloc[i]),
                             vol_jump=float(r.iloc[nxt].std() * np.sqrt(252) / vol.iloc[i]), trend=float(core.iloc[nxt].sum() / (risk.iloc[i] * np.sqrt(H)))))
    S = pd.DataFrame(rows); S["state"] = np.where(S.low_vol, "low vol", "high vol") + ", " + np.where(S.smooth, "smooth trend", "chop")
    g = S.groupby("state").agg(n=("vol_jump", "size"), vol_jump_median=("vol_jump", "median"), vol_jump_share_over_1_5=("vol_jump", lambda v: (v > 1.5).mean()),
                               trend_mean=("trend", "mean"), trend_median=("trend", "median"))
    out["states"] = g.round(4).to_dict(orient="index"); print(g.round(3).to_string())
    out["states_by_class"] = S.groupby(["cls", "state"]).agg(n=("vol_jump", "size"), vol_jump=("vol_jump", "median"), trend=("trend", "mean")).round(4).reset_index().to_dict(orient="records")
    print(S.groupby(["cls", "state"]).agg(n=("vol_jump", "size"), vol_jump=("vol_jump", "median"), trend=("trend", "mean")).round(3).to_string())
    # ---- 1 and 3: the OOS universe, rebuilt as in l27.py
    names = sorted({t for y in range(2012, 2026) for k, mk in M.UNI[str(y)]["sc_div"].items() for t in mk})
    X, P = {}, {}
    for t in names:
        c = close[t].dropna(); x, xh, xl = L26.excess(c, high[t].reindex(c.index), low[t].reindex(c.index), rf); X[t] = x; P[t] = M.positions(x, xh, xl)
    VOL = pd.DataFrame({t: np.sqrt((X[t].pct_change() ** 2).ewm(span=126, min_periods=60).mean()) for t in names})
    VREL = VOL / VOL.rolling(756, min_periods=252).median()
    A, LONG, CALM = [], [], []
    for y in range(2012, 2026):
        w = pd.Series(M.SEL[str(y)]["weights"]["one_set"]); w = (w >= 0.2).astype(float); w = w[w > 0] / w[w > 0].sum()
        uni = M.UNI[str(y)]["sc_div"]; mk = [t for k in uni for t in uni[k]]; rk = [t for k in RISK for t in uni.get(k, [])]
        agree = pd.DataFrame({t: (np.sign(P[t][w.index]) * w).sum(axis=1).abs() for t in mk}).mean(axis=1)
        hist, nxt = slice(f"{y - 2}-01-01", f"{y}-12-31"), slice(f"{y + 1}-01-01", f"{y + 1}-12-31")
        A.append((agree / agree.loc[hist].median()).loc[nxt])
        expo = pd.DataFrame({t: (P[t][w.index] * w).sum(axis=1) for t in rk}); LONG.append((expo > 0).mean(axis=1).loc[nxt]); CALM.append(VREL[rk].median(axis=1).loc[nxt])
    D = pd.read_parquet(M.OUT / "l27_daily.parquet"); A = pd.concat(A).reindex(D.index); aw = D.scale / D.ctot
    mo = D.index.to_period("M")
    out["strength_vs_aware"] = dict(corr_daily=float(A.corr(aw)), corr_monthly=float(A.groupby(mo).mean().corr(aw.groupby(mo).mean())),
                                    corr_monthly_changes=float(A.groupby(mo).mean().diff().corr(aw.groupby(mo).mean().diff())))
    print("strength against position-aware scale:", {k: round(v, 3) for k, v in out["strength_vs_aware"].items()})
    LONG, CALM = pd.concat(LONG).reindex(D.index), pd.concat(CALM).reindex(D.index); state = (LONG >= 0.8) & (CALM < 1)
    spell = (state != state.shift()).cumsum()[state]; eps = []
    rv = D.rule.rolling(H).std().shift(-H) * np.sqrt(252)
    for k, idx in spell.groupby(spell).groups.items():
        if len(idx) < 21: continue
        s, e = idx.min(), idx.max(); i = D.index.get_loc(e)
        if i + H >= len(D): fut = None
        else: fut = dict(rule_next63=float(D.rule.iloc[i + 1: i + 1 + H].sum()), rule_vol_next63=float(D.rule.iloc[i + 1: i + 1 + H].std() * np.sqrt(252)))
        eps.append(dict(start=str(s.date()), end=str(e.date()), days=len(idx), long_share=float(LONG.loc[idx].mean()), calm=float(CALM.loc[idx].mean())) | (fut or {}))
    base = dict(share_of_days_in_state=float(state.mean()), rule_next63_all_days_mean=float(D.rule.rolling(H).sum().shift(-H).mean()))
    out["calm_stacked"] = dict(episodes=eps, baseline=base); print(pd.DataFrame(eps).round(3).to_string()); print(base)
    (M.RESULTS / "states.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
