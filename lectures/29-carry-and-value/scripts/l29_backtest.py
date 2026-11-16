"""Lecture 29: first backtest of carry and value on the futures dataset (plan: results/hypotheses.md), 2006 to 2022-11-18.
Machinery as trend (Lectures 26-28): each market's target position = its weight / its six-month volatility (10% a year), reached a tenth of
the way each day, 5 bp per unit traded; within a group the weights are the signal scores divided by their sum of absolute values; each group's
return scaled each year to 10% on its past three years; groups at equal risk (those with a signal); the strategy's total scaled each year to 10%.
Versions: rule (ranking within group), own sign, and the PCA hedge with alpha = 1/2 (currencies and commodities; others as the rule).
Output: OUT/l29_streams.parquet (daily returns of every version), printed summary."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l29 as L
TARGET, SPEED, COST = 0.10, 0.1, 0.0005
START, END = "2006-01-01", "2022-11-18"


def returns():
    """Daily returns over cash of every traded market, by group."""
    S = pd.read_pickle(L.FT.CACHE); _, R_fx, _ = L.FX.build()
    tb = L.bill() / 252; b = L.FT.bond_funds()
    com = pd.DataFrame({t: S[t]["ratio"].pct_change() for t in L.COMMOD}).reindex(L.DAYS)
    eq = pd.DataFrame({t: S[t]["ratio"].pct_change() for t in L.EQUITY}).reindex(L.DAYS)
    bd = pd.DataFrame({k: b[k].pct_change() for k in L.BONDS}).reindex(L.DAYS).sub(tb.shift(1), axis=0)
    return {"fx": R_fx.reindex(L.DAYS), "commod": com, "bonds": bd, "equity": eq}


def pca_hedge(scores, R, alpha=0.5, every=21):
    """w = (I - v1 v1' - alpha v2 v2') s, components of the correlation of vol-scaled returns over the past three years, refreshed monthly."""
    Z = R / R.rolling(126, min_periods=60).std().shift(1); out = scores.copy() * np.nan; V = None
    for k, d in enumerate(scores.index):
        if k % every == 0:
            h = Z.iloc[max(0, k - 756):k].dropna(axis=1, thresh=500).dropna()
            if len(h) > 250 and h.shape[1] >= 3:
                val, vec = np.linalg.eigh(np.corrcoef(h.T.values)); V = (h.columns, vec[:, ::-1][:, :2])
        s = scores.iloc[k]
        if V is None: continue
        cols, vec = V; ok = [c for c in cols if np.isfinite(s.get(c, np.nan))]
        if len(ok) < 3: continue
        idx = [list(cols).index(c) for c in ok]; v1, v2 = vec[idx, 0], vec[idx, 1]
        x = s[ok].to_numpy(); w = x - v1 * (v1 @ x) - alpha * v2 * (v2 @ x); out.loc[d, ok] = w
    return out


def group_stream(W, R):
    """Unit-risk group return (before group scaling) from scores W, net of costs."""
    W = W.div(W.abs().sum(axis=1), axis=0)                                          # weights sum to 1 in absolute value
    vol = R.rolling(126, min_periods=60).std().shift(1) * np.sqrt(252)
    tgt = (W * TARGET / vol).fillna(0)
    pos = tgt.ewm(alpha=SPEED, adjust=False).mean()                                  # a tenth of the way each day
    held = pos.shift(1)
    gross = (held * R).sum(axis=1, min_count=1); cost = pos.diff().abs().sum(axis=1) * COST
    return (gross.fillna(0) - cost.shift(1).fillna(0)).where(W.notna().any(axis=1).shift(1, fill_value=False))


def yearly_scale(r):
    """Scale each calendar year to 10% on the past three years' daily returns."""
    out = []
    for y in range(r.index[0].year + 3, r.index[-1].year + 1):
        h = r.loc[f"{y - 3}-01-01":f"{y - 1}-12-31"].dropna()
        if len(h) < 250: continue
        out.append(r.loc[str(y)] * (TARGET / np.sqrt(252)) / h.std())
    return pd.concat(out) if out else r * np.nan


def strategy(groups):
    """Groups' unit streams -> scaled groups -> equal risk among groups with a signal -> total scaled."""
    G = pd.DataFrame({g: yearly_scale(s) for g, s in groups.items()})
    U = G.mean(axis=1, skipna=True)
    return yearly_scale(U), G


def own_sign_fx_value():
    M = L.long_monthly()["fx"]; usd = np.log(np.exp(L.FX.reer().resample("MS").first()["USD"]))
    v = L.trend_gap(M.sub(usd, axis=0), 10)
    return v.reindex(L.DAYS.union(v.index)).ffill(limit=25).reindex(L.DAYS)


def sharpe(r):
    r = r.dropna(); return float(r.mean() / r.std() * np.sqrt(252))


if __name__ == "__main__":
    R = returns(); carry, value, _ = L.signals()
    sm = {g: L.smooth(c) for g, c in carry.items()}
    ver = {}
    # carry
    rank = {g: (np.sign(sm[g]) if g == "equity" else L.carry_signal(carry[g])) for g in carry}
    rule = {g: (np.sign(sm[g]) if g == "equity" else L.carry_score(carry[g], R[g][carry[g].columns])) for g in carry}   # rule after 2026-11-16
    own = {g: np.sign(sm[g]) for g in carry}
    hed = {g: (pca_hedge(rule[g], R[g]) if g in ("fx", "commod") else rule[g]) for g in carry}
    vown = dict(value); vown["fx"] = own_sign_fx_value()
    vrule = {g: L.rank_centred(value[g]) for g in value}
    vhed = {g: (pca_hedge(vrule[g], R[g]) if g in ("fx", "commod") else vrule[g]) for g in value}
    for name, sig in (("carry_rule", rule), ("carry_rank", rank), ("carry_own", own), ("carry_hedge", hed),
                      ("value_rule", vrule), ("value_own", {g: np.sign(v) for g, v in vown.items()}), ("value_hedge", vhed)):
        tot, G = strategy({g: group_stream(sig[g], R[g][sig[g].columns]) for g in sig})
        ver[name] = tot
        for g in G: ver[f"{name}:{g}"] = G[g]
        print(name, "groups:", {g: round(sharpe(G[g].loc[START:END]), 2) for g in G}, flush=True)
    fixed = L.RAW / "l29_trend_futures_fixed.parquet"                                  # trend with both Treasury funds (VUSTX fix, 2026-11-16)
    base = (pd.read_parquet(fixed)["ret"] if fixed.exists() else pd.read_parquet(L.L28.OUT / "l28_base.parquet")[("futures", "ret")]).rename("trend")
    S = pd.DataFrame(ver); S["trend"] = base; S = S.loc[START:END]
    S.to_parquet(L.RAW / "l29_streams.parquet")
    print("\nSharpe 2006-2022 and correlation with trend:")
    for c in ["trend", "carry_rule", "carry_rank", "carry_own", "carry_hedge", "value_rule", "value_own", "value_hedge"]:
        print(f"  {c:12s} Sharpe {sharpe(S[c]):+.2f}  corr with trend {S[c].corr(S['trend']):+.2f}")
    for combo in (["trend", "carry_rule", "value_rule"], ["trend", "carry_rule"], ["trend", "carry_rank"], ["trend", "value_rule"]):
        m = yearly_scale(pd.concat([S[c] for c in combo], axis=1).mean(axis=1)).loc[START:END]
        dd = (np.exp(np.log1p(m.fillna(0)).cumsum())); dd = (dd / dd.cummax() - 1).min()
        print(f"  {' + '.join(combo):30s} Sharpe {sharpe(m):+.2f}  return a year {m.mean() * 252:+.1%}  worst drawdown {dd:.1%}")
