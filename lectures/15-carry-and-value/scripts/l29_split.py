"""Lecture 15: is carry added to trend a carry filter on trend in disguise? (user, 2026-11-16, after the first results)
Carry's return (rule, futures 2006 to 2022-11-18, at the strategy's own scaling) is split by market and day into:
  carry only   - markets trend does not trade (seven of the nine G10 currencies), or days trend holds no position there;
  agree        - markets both trade, carry's position on the same side as trend's (the combination holds more: amplifies trend);
  disagree     - markets both trade, carry against trend (the positions net: the filter-like part, trend held less).
Each part's return a year and Sharpe ratio (on all days, zero when the part holds nothing) and its share of carry's return."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l29 as L, l29_backtest as B
M27 = L.L28.M27; FT = L.FT
MAP = {"EUR": "cme-euro", "JPY": "cme-jpy"}


def contributions(W, R):
    """Per-market unit P&L net of costs (the pieces whose sum is group_stream)."""
    W = W.div(W.abs().sum(axis=1), axis=0)
    vol = R.rolling(126, min_periods=60).std().shift(1) * np.sqrt(252)
    pos = (W * B.TARGET / vol).fillna(0).ewm(alpha=B.SPEED, adjust=False).mean()
    pnl = pos.shift(1) * R - (pos.diff().abs() * B.COST).shift(1)
    return pnl.fillna(0).where(W.notna().any(axis=1).shift(1, fill_value=False), np.nan), pos.shift(1)


def scales(r):
    """The yearly factors of B.yearly_scale, as a daily series."""
    f = pd.Series(np.nan, r.index)
    for y in range(r.index[0].year + 3, r.index[-1].year + 1):
        h = r.loc[f"{y - 3}-01-01":f"{y - 1}-12-31"].dropna()
        if len(h) >= 250: f.loc[str(y)] = (B.TARGET / np.sqrt(252)) / h.std()
    return f


def trend_positions():
    S = pd.read_pickle(FT.CACHE); px = {k: S[k]["ratio"] for k in S if k in FT.CLASS}
    tb = L.bill() / 252; fx = FT.bond_funds()
    for t in L.BONDS:
        r = fx[t].pct_change() - tb.reindex(fx.index).ffill().shift(1); px[t] = 100 * (1 + r.fillna(0)).cumprod()
    P = {}
    for t, p in px.items():
        x = p.dropna(); x = x[x > 0]; P[t] = M27.positions(x, x, x)[FT.HELD].mean(axis=1)
    return pd.DataFrame(P).reindex(L.DAYS).shift(1)                                   # held on the day


if __name__ == "__main__":
    R = B.returns(); carry, _, _ = L.signals()
    sig = {g: (np.sign(L.smooth(carry[g])) if g == "equity" else L.carry_signal(carry[g])) for g in carry}
    C, POS, G = {}, {}, {}
    for g in sig:
        c, p = contributions(sig[g], R[g][sig[g].columns]); C[g], POS[g] = c, p; G[g] = c.sum(axis=1, min_count=1)
    fg = {g: scales(G[g]) for g in G}
    Gs = pd.DataFrame({g: G[g] * fg[g] for g in G}); n = Gs.notna().sum(axis=1)
    U = Gs.mean(axis=1, skipna=True); ft = scales(U)
    T = trend_positions()
    parts = {k: pd.Series(0.0, L.DAYS) for k in ("carry only", "agree", "disagree")}
    for g in C:
        for m in C[g]:
            pnl = C[g][m] * fg[g] / n * ft                                             # the market's share of the carry strategy's return
            tm = MAP.get(m, m); tp = T[tm] if tm in T else pd.Series(0.0, L.DAYS)
            cp = POS[g][m]; s = np.sign(cp) * np.sign(tp.fillna(0))
            parts["carry only"] += pnl.where(s == 0, 0).fillna(0)
            parts["agree"] += pnl.where(s > 0, 0).fillna(0)
            parts["disagree"] += pnl.where(s < 0, 0).fillna(0)
    D = pd.DataFrame(parts).loc[B.START:B.END]; tot = D.sum(axis=1)
    check = pd.read_parquet(L.RAW / "l29_streams.parquet")["carry_rule"]
    print(f"check: rebuilt carry vs backtest, correlation {tot.corr(check):.4f}, return a year {tot.mean() * 252:+.2%} vs {check.mean() * 252:+.2%}")
    for k in D:
        x = D[k]; print(f"  {k:10s} return a year {x.mean() * 252:+.2%}  share of carry's return {x.mean() / tot.mean():+.0%}  Sharpe {B.sharpe(x):+.2f}  "
                        f"share of carry's risk exposure days {(x != 0).mean():.0%}")
