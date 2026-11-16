"""Lecture 15: robustness grid of the carry strategy (four groups together, monthly, futures period 2006 to October 2022).
One choice varied at a time around the rule (score; level and 3-month change; volatility over 36 months; no hedge):
sizing horizon (12, 36, 60 months), signal (level only, change only, change over 1, 3, 6 months), weighting (score, rank), and the PCA hedge in
currencies and commodities (alpha = 0, 1/2, 1: first component removed, the second removed by alpha). Prints Sharpe ratio alone and with trend."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l29_combined as M, l29_bonds_g10 as G, l29 as L
A, B_ = "2006-01", "2022-10"


def zpart(X, vol): return (G.zrow(X) + G.zrow(X / vol)) / 2


def sig(C, R, level=True, change=3):
    vol = R.rolling(36, min_periods=24).std() * np.sqrt(12); parts = []
    if level: parts.append(zpart(C, vol))
    if change: parts.append(zpart(C - C.shift(change), vol))
    return sum(parts) / len(parts)


def hedge(W, R, alpha):
    Z = R / R.rolling(36, min_periods=24).std(); out = W * np.nan
    for k, d in enumerate(W.index):
        h = Z.iloc[max(0, k - 36):k].dropna(axis=1, thresh=24).dropna()
        s = W.loc[d]; ok = [c for c in h.columns if np.isfinite(s.get(c, np.nan))]
        if len(h) < 24 or len(ok) < 3: continue
        val, vec = np.linalg.eigh(np.corrcoef(h[ok].T.values)); v1, v2 = vec[:, -1], vec[:, -2]; x = s[ok].to_numpy()
        out.loc[d, ok] = x - v1 * (v1 @ x) - alpha * v2 * (v2 @ x)
    return out


def stats(r):
    """Sharpe, Sortino, Omega (gains / losses, monthly, over cash) and Calmar (compound return a year / worst drawdown)."""
    r = r.dropna(); w = (1 + r).cumprod(); dd = (w / w.cummax() - 1).min(); ann = w.iloc[-1] ** (12 / len(r)) - 1
    return dict(sharpe=G.sharpe_m(r), sortino=r.mean() / np.sqrt((np.minimum(r, 0) ** 2).mean()) * np.sqrt(12),
                omega=r[r > 0].sum() / -r[r < 0].sum(), calmar=ann / abs(dd), maxdd=dd)


def run(Gs, W, tf, vol_months=36):
    S = pd.DataFrame({g: G.stream(W[g], Gs[g]["R"], vol_months) for g in Gs}); tot = M.scale_total(S.mean(axis=1, skipna=True)).loc[A:B_]
    return stats(tot), stats(M.with_trend(tot, tf.loc[A:B_]))


if __name__ == "__main__":
    Gs = M.groups(); tf = M.compound(pd.read_parquet(L.RAW / "l29_trend_futures_fixed.parquet")["ret"])
    rule = {g: sig(Gs[g]["C"], Gs[g]["R"]) for g in Gs}
    rows = [("rule (score, level + 3-month change, 36-month vol)", rule, 36)]
    for vm in (12, 60): rows.append((f"sizing: {vm}-month volatility", rule, vm))
    rows.append(("signal: level only", {g: sig(Gs[g]["C"], Gs[g]["R"], True, 0) for g in Gs}, 36))
    rows.append(("signal: change only (3 months)", {g: sig(Gs[g]["C"], Gs[g]["R"], False, 3) for g in Gs}, 36))
    for ch in (1, 6): rows.append((f"signal: level + {ch}-month change", {g: sig(Gs[g]["C"], Gs[g]["R"], True, ch) for g in Gs}, 36))
    rank = {g: (G.rank_centred(Gs[g]["C"]) + G.rank_centred(Gs[g]["C"] - Gs[g]["C"].shift(3))) / 2 for g in Gs}
    rows.append(("weighting: rank instead of score", rank, 36))
    for a in (0, 0.5, 1):
        rows.append((f"hedge alpha = {a} (currencies, commodities)", {g: (hedge(rule[g], Gs[g]["R"], a) if g in ("fx", "commod") else rule[g]) for g in Gs}, 36))
    s0, _ = run(Gs, rule, tf); idx = M.with_trend(M.scale_total(pd.DataFrame({g: G.stream(rule[g], Gs[g]["R"]) for g in Gs}).mean(axis=1, skipna=True)).loc[A:B_], tf.loc[A:B_]).index
    tr = stats(tf.loc[idx]); fmt = lambda x: f"{x['sharpe']:+5.2f} {x['sortino']:+6.2f} {x['omega']:5.2f} {x['calmar']:5.2f} {x['maxdd']:6.1%}"
    print(f"{'':50s} {'carry: Sharpe Sortino Omega Calmar maxDD':>40s} | {'trend + carry: same':>36s}")
    print(f"{'trend alone (same months as the combinations)':50s} {'':40s} | {fmt(tr)}")
    for name, W, vm in rows:
        s, c = run(Gs, W, tf, vm); print(f"{name:50s} {fmt(s):>40s} | {fmt(c)}", flush=True)
