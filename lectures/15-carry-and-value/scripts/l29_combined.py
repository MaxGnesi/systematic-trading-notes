"""Lecture 15: the four groups together, monthly (2026-11-16). Carry and value each = currencies (9), commodities (7), bonds (9 countries),
equities (15 countries) at equal risk, each group scaled yearly to 10% (l29_bonds_g10.stream), the total scaled yearly to 10%.
Carry signal (all groups): score = average of [z(level) + z(level / volatility)] / 2 and the same for the 3-month change (z within the group).
Value: rule = against the 10-year trend line (z); AQR's construction reported alongside.
Trend = Lecture 13's baseline across all its markets (not trend on these markets): futures 2006 to 2022-10 (with both Treasury funds),
ETFs 2013-2026; each combination at equal risk, scaled on its past (expanding, from 12 months) to trend's volatility.
Luck baseline: N random strategies per style, each market's sign a two-state Markov chain with the real signal's average holding period
(months), same machinery. Usage: python l29_combined.py [N]"""
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l29 as L, l29_bonds_g10 as G, l29_equity_countries as Q, l29_backtest as B
TO_M = lambda x: x.resample("ME").last().set_axis(x.resample("ME").last().index.to_period("M"))


def compound(r):
    m = (1 + r.fillna(0)).resample("ME").prod() - 1; m = m.where(r.notna().resample("ME").sum() > 0); m.index = m.index.to_period("M"); return m


def score(C, R):
    vol = R.rolling(36, min_periods=24).std() * np.sqrt(12)
    part = lambda X: (G.zrow(X) + G.zrow(X / vol)) / 2
    return (part(C) + part(C - C.shift(3))) / 2


def groups():
    """Monthly returns, carry measure and value signals (rule, AQR's construction) per group."""
    out = {}
    R = B.returns(); carry, _, _ = L.signals()
    # currencies and commodities: daily data to monthly
    Vt = L.value_trend(10)
    for g in ("fx", "commod"):
        Rm = compound(R[g]); Cm = TO_M(L.smooth(carry[g])); Vm = TO_M(Vt[g])
        out[g] = dict(R=Rm, C=Cm, V=Vm)
    lr = L.FX.reer().drop(columns="USD"); lr = lr.resample("ME").last(); lr.index = lr.index.to_period("M")
    out["fx"]["Va"] = -(lr - lr.shift(54).rolling(13).mean())
    Qp = L.spot_prices()[L.COMMOD]; lq = np.log(Qp.resample("ME").last()); lq.index = lq.index.to_period("M")
    out["commod"]["Va"] = -(lq - lq.shift(54).rolling(13).mean())
    # bonds: ten countries, month-end yields
    Y, C = G.data(); E = G.month_end().reindex(Y.index); Rb = G.returns(Y, C, E)
    out["bonds"] = dict(R=Rb, C=Y - C, V=G.rank_centred(G.trend_z(Y)) * 0 + G.trend_z(Y), Va=Y - Y.shift(54).rolling(13).mean())
    # equities: fifteen countries
    Re, P, DY, CASH_, INF = Q.data(); real = CASH_ - INF; Ce = DY - real; Ce["US"] = Q.us_earnings_yield(Ce.index) - real["US"]
    lp = np.log(P); out["equity"] = dict(R=Re, C=Ce, V=L.trend_gap(lp, 10), Va=-(lp - lp.shift(54).rolling(13).mean()))
    return out


def value5(Gs):
    """Value against each market's own 5-year trend line (z; positive = cheap), per group, monthly."""
    import l29 as L_
    V = {}
    Vt = L_.value_trend(5)
    for g in ("fx", "commod"): V[g] = TO_M(Vt[g])
    Y, _ = G.data(); V["bonds"] = G.trend_z(Y, 5)
    _, P, _, _, _ = Q.data(); V["equity"] = L.trend_gap(np.log(P), 5)
    return V


def tilted(Gs, w, V5=None):
    """Carry tilted by value: score = carry score + w x z(value against the 5-year line)."""
    V5 = V5 or value5(Gs)
    return {g: score(Gs[g]["C"], Gs[g]["R"]).add(w * G.zrow(V5[g].reindex(Gs[g]["R"].index)), fill_value=0)
              .where(score(Gs[g]["C"], Gs[g]["R"]).notna()) for g in Gs}


def scale_total(r):
    out = []
    for y in sorted(set(r.index.year)):
        h = r[(r.index.year >= y - 3) & (r.index.year < y)].dropna()
        if len(h) >= 24: out.append(r[r.index.year == y] * (G.TARGET / np.sqrt(12)) / h.std())
    return pd.concat(out)


def style(Gs, weights):
    S = pd.DataFrame({g: G.stream(weights[g], Gs[g]["R"]) for g in Gs}); return scale_total(S.mean(axis=1, skipna=True)), S


def with_trend(s, trend):
    both = pd.concat([trend, s], axis=1).dropna(); c = both.mean(axis=1)
    c = c * both.iloc[:, 0].std() / c.expanding(12).std().shift(1); return c.dropna()


def markov_signs(W, hold, rng):
    p = (1 / hold.reindex(W.columns).clip(lower=1)).to_numpy(); flips = rng.random(W.shape) < p
    s = rng.choice([-1.0, 1.0], W.shape[1]) * np.where(np.cumsum(flips, axis=0) % 2 == 0, 1.0, -1.0)
    return pd.DataFrame(s, W.index, W.columns).where(W.notna())


def holding(W):
    s = np.sign(W); return pd.Series({c: len(x) / max((x != x.shift()).sum(), 1) for c in s for x in [s[c].dropna()[lambda v: v != 0]]})


if __name__ == "__main__":
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    Gs = groups()
    W = {"carry": {g: score(Gs[g]["C"], Gs[g]["R"]) for g in Gs},
         "value": {g: G.rank_centred(Gs[g]["V"]) for g in Gs},
         "value (AQR's construction)": {g: G.rank_centred(Gs[g]["Va"]) for g in Gs}}
    tf = compound(pd.read_parquet(L.RAW / "l29_trend_futures_fixed.parquet")["ret"])
    te = compound(pd.read_parquet(L.L28.OUT / "l28_base.parquet")[("etf", "ret")].dropna())
    periods = {"futures trend, 2006-2022": (tf, "2006-01", "2022-10"), "ETF trend, 2013-2026": (te, "2013-01", "2026-10")}
    res = {}
    for name, w in W.items():
        tot, S = style(Gs, w); res[name] = tot
        print(f"\n{name}: groups 2006-2022 " + ", ".join(f"{g} {G.sharpe_m(S[g].loc['2006':'2022-10']):+.2f}" for g in S))
        for pn, (tr, a, b) in periods.items():
            s = tot.loc[a:b]; c = with_trend(s, tr.loc[a:b])
            print(f"  {pn}: {name} {G.sharpe_m(s):+.2f}, corr with trend {pd.concat([s, tr], axis=1).dropna().corr().iat[0, 1]:+.2f}; "
                  f"trend {G.sharpe_m(tr.loc[c.index]):+.2f} -> trend + {name.split(' ')[0]} {G.sharpe_m(c):+.2f}")
        if N and name != "value (AQR's construction)":
            rng = np.random.default_rng(29); hold = {g: holding(w[g]) for g in w}; alone, comb = [], []
            tr, a, b = periods["futures trend, 2006-2022"]
            for i in range(N):
                rt, _ = style(Gs, {g: markov_signs(w[g], hold[g], rng) for g in w}); rt = rt.loc[a:b]
                alone.append(G.sharpe_m(rt)); comb.append(G.sharpe_m(with_trend(rt, tr.loc[a:b])))
            real_a, real_c = G.sharpe_m(tot.loc[a:b]), G.sharpe_m(with_trend(tot.loc[a:b], tr.loc[a:b]))
            print(f"  luck baseline ({N}, futures period): alone beats {np.mean(np.array(alone) < real_a):.0%} (median {np.median(alone):+.2f}, 95th {np.percentile(alone, 95):+.2f}); "
                  f"with trend beats {np.mean(np.array(comb) < real_c):.0%} (median {np.median(comb):+.2f}, 95th {np.percentile(comb, 95):+.2f})")
    pd.DataFrame(res).to_timestamp(how="end").to_parquet(L.RAW / "l29_combined.parquet")
