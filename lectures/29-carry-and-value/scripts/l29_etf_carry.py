"""Lecture 29: carry on the bond and credit ETFs (plan entries of 2026-11-16), 2013-2026 against Lecture 27's ETF trend portfolio.
Carry per fund = yield proxy - bill rate: last regular distribution x payments in the past year / unadjusted close (rule) or the past year's
regular distributions / close (variant); specials (above twice the median of the past 12 payments) excluded; a distribution is known from the
day after its ex-date. TIP: TIPS real yield (average of 5- and 10-year) + past 12 months' CPI inflation.
Groups: Lecture 25's classes, Rates (SHY IEI IEF TLT TIP BWX BNDX) and Credit (LQD HYG EMB MBB BKLN); comparison: one fixed-income group of all 12
(the classic carry trade: high yield, loans and EM debt against Treasuries). Machinery and score as the futures (l29_backtest, l29.carry_score)."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l29 as L, l29_backtest as B
INC = L.RAW / "l29_long" / "etf_income"
RATES = ["SHY", "IEI", "IEF", "TLT", "TIP", "BWX", "BNDX"]; CREDIT = ["LQD", "HYG", "EMB", "MBB", "BKLN"]
DAYS = pd.bdate_range("2003-01-02", "2026-11-13"); START, END = "2013-01-01", "2026-11-13"


def ffill_days(x, limit=5):
    return x.reindex(DAYS.union(x.index)).ffill(limit=limit).reindex(DAYS)


def yield_proxy(t, kind="last"):
    d = pd.read_csv(INC / f"{t}_div.csv", index_col=0, parse_dates=True).iloc[:, 0]; d = d[d > 0]
    c = pd.read_csv(INC / f"{t}_close.csv", index_col=0, parse_dates=True).iloc[:, 0].dropna()
    med = d.rolling(12, min_periods=3).median().shift(1); reg = d[~(d > 2 * med)]
    known = reg.copy(); known.index = known.index + pd.offsets.BDay(1)
    days = pd.Series(1.0, known.index)
    if kind == "last":
        freq = days.rolling("365D").sum(); inc = known * freq                        # last payment x payments in the past year
    else:
        inc = known.rolling("365D").sum()
    inc = inc.reindex(DAYS.union(inc.index)).ffill(limit=300).reindex(DAYS)          # a fund that stops paying keeps its last income ~1 year
    return inc / ffill_days(c)


def bill():
    return ffill_days(L.fred_local("DTB3")) / 100


def carry_table(kind="last"):
    C = {t: yield_proxy(t, kind) for t in RATES + CREDIT if t != "TIP"}
    cpi = L.fred_local("CPIAUCSL"); infl = cpi / cpi.shift(12) - 1; infl.index = infl.index + pd.offsets.MonthBegin(2)
    C["TIP"] = (ffill_days(L.fred_local("DFII5")) + ffill_days(L.fred_local("DFII10"))) / 200 + ffill_days(infl, 45)
    return pd.DataFrame(C).sub(bill(), axis=0)


def returns():
    close, high, low, dv, rf = L.L28.L26.load_daily()
    return pd.DataFrame({t: L.L28.L26.excess(close[t].dropna(), high[t], low[t], rf)[0].pct_change() for t in RATES + CREDIT}).reindex(DAYS)


if __name__ == "__main__":
    R = returns(); trend = pd.read_parquet(L.L28.OUT / "l28_base.parquet")[("etf", "ret")].rename("trend").loc[START:END]
    out = {}
    for kind in ("last", "12m"):
        C = carry_table(kind); sm = L.smooth(C)
        if kind == "last":
            print("median carry 2013-2026 (yield proxy - bill):", sm.loc[START:].median().round(4).to_dict())
        for name, groups in (("classes", {"rates": RATES, "credit": CREDIT}), ("one group", {"fi": RATES + CREDIT})):
            for ver, f in (("score", lambda c, r: L.carry_score(c, r)), ("rank", lambda c, r: L.carry_signal(c)), ("own", lambda c, r: np.sign(L.smooth(c)))):
                st = {g: B.group_stream(f(C[m], R[m]), R[m]) for g, m in groups.items()}
                tot, G = B.strategy(st); tot = tot.loc[START:END]
                both = pd.concat([trend, tot.reindex(trend.index)], axis=1).dropna()
                comb = both.mean(axis=1); comb = comb * (both.iloc[:, 0].std() / comb.expanding(250).std().shift(1))   # scaled on its past to trend's risk
                comb = comb.dropna(); tr = trend.reindex(comb.index)
                key = f"{kind} | {name} | {ver}"; out[key] = tot
                print(f"{key:28s} carry {B.sharpe(tot.reindex(comb.index)):+.2f}  corr trend {tot.corr(trend):+.2f}  trend {B.sharpe(tr):+.2f} -> trend+carry {B.sharpe(comb):+.2f} "
                      f"({comb.index[0].year}-{comb.index[-1].year})  "
                      f"groups {({g: round(B.sharpe(G[g].loc[START:END]), 2) for g in G})}", flush=True)
    print(f"trend alone {B.sharpe(trend):+.2f}")
    pd.DataFrame(out).to_parquet(L.RAW / "l29_etf_carry.parquet")
