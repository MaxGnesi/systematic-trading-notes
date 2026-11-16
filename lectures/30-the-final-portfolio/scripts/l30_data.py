"""Lecture 30: the four carry groups and trend, monthly, extended back to 1990 for the out-of-sample test (plan: results/hypotheses.md).
Currencies are rebuilt monthly from 1985: month-end spot (FRED daily; the euro before 1999 via the German mark, FRED EXGEUS monthly, converted at
the fixed 1.95583 marks per euro) and 3-month rates (OECD via FRED, the previous month's value; where the 3-month series starts late, the
call-money rate: Germany for the euro area before 1994, Switzerland before mid-1999, Japan before 2002). Return over cash in month m:
spot change + (foreign - US rate) / 12. Bonds, equities and commodities as Lecture 29 (each from its data's start). Trend 1990-2005: Lecture 28's
12-market trend portfolio (l28_confirm), compounded monthly. 60/40: S&P 500 total return (Shiller) and the US 10-year bond built from yields."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parent; REPO = HERE.parents[2]
for d in ("29-carry-and-value", "28-part-time-strategies"): sys.path.insert(0, str(REPO / "lectures" / d / "scripts"))
import l29 as L, l29_combined as M, l29_bonds_g10 as G
FX = L.FX
SPOT = FX.SPOT; RATE3 = FX.RATE
CALL = {"EUR": ("IRSTCI01DEM156N", "1994-01"), "CHF": ("IRSTCI01CHM156N", "1999-07"), "JPY": ("IRSTCI01JPM156N", "2002-04")}   # call money before these months


def mperiod(x):
    m = x.resample("ME").last(); m.index = m.index.to_period("M"); return m


def fx_monthly():
    """Monthly currency returns over cash, carry (rate gap) and spot, 1985-2026."""
    S = {}
    for c, (sid, inv) in SPOT.items():
        s = FX.fred(sid); s = (1 / s) if inv else s; S[c] = mperiod(s)
    mark = FX.fred("EXGEUS"); mark.index = mark.index.to_period("M")
    eur_pre = 1.95583 / mark                                                     # dollars per euro-equivalent, monthly averages
    S["EUR"] = S["EUR"].combine_first(eur_pre.loc[:"1998-12"])
    S = pd.DataFrame(S).loc["1985-01":]
    def rate(code):
        x = FX.fred(f"IR3TIB01{code}M156N") / 100; x.index = x.index.to_period("M"); return x
    us = rate("US"); R, C = {}, {}
    for c in SPOT:
        r = rate(RATE3[c])
        if c in CALL:
            sid, start = CALL[c]; cm = FX.fred(sid) / 100; cm.index = cm.index.to_period("M")
            r = r.loc[start:].combine_first(cm.loc[:pd.Period(start, "M") - 1])
        gap = (r - us).reindex(S.index)
        C[c] = gap; R[c] = S[c].pct_change() + gap.shift(1) / 12                  # last month's gap earned this month
    return pd.DataFrame(R), pd.DataFrame(C), S


def groups_long():
    """Lecture 29's groups with currencies replaced by the long monthly build."""
    Gs = M.groups()
    Rf, Cf, Sf = fx_monthly()
    Gs["fx"] = dict(R=Rf, C=Cf, V=Gs["fx"]["V"].reindex(Rf.index), Va=Gs["fx"]["Va"].reindex(Rf.index))
    return Gs


def trend_1990():
    import l28_confirm as CF
    R = CF.returns(); base = CF.portfolio(R).loc["1990-01-01":"2005-12-31"]
    return M.compound(base)


def sixty_forty():
    sh = L.shiller(); p, d = sh["P"], sh["D"]; p.index = p.index.to_period("M"); d.index = d.index.to_period("M")
    eq = (p + d / 12) / p.shift(1) - 1                                           # monthly total return (Shiller: monthly average prices)
    Y, C = G.data(); E = G.month_end().reindex(Y.index); bond = G.returns(Y, C, E)["US"] + C["US"].shift(1) / 12   # total return
    cash = C["US"].shift(1) / 12
    return pd.DataFrame({"equity": eq - cash.reindex(eq.index), "60/40": 0.6 * eq.reindex(bond.index) + 0.4 * bond - cash}).dropna()


if __name__ == "__main__":
    Rf, Cf, Sf = fx_monthly()
    print("currencies: first month with a return:", {c: str(Rf[c].first_valid_index()) for c in Rf})
    check = M.compound(FX.build()[1]).loc["2000-01":"2022-10"]
    both = pd.concat([Rf, check], axis=1, keys=["monthly", "daily"]).dropna()
    print("monthly build against Lecture 29's daily build, 2000-2022, correlation by currency:",
          {c: round(both["monthly"][c].corr(both["daily"][c]), 3) for c in Rf})
    t = trend_1990(); print(f"trend 1990-2005: {t.index[0]} to {t.index[-1]}, monthly Sharpe {G.sharpe_m(t):.2f}")
    b = sixty_forty().loc["1990-01":"2005-12"]; print("1990-2005 monthly Sharpe:", {k: round(G.sharpe_m(b[k]), 2) for k in b})
