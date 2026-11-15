"""Lecture 29: carry and value signals for every group (plan: results/hypotheses.md, all choices fixed before any strategy return).
Every signal is a daily table (business days 1999-2022-11-18 for the futures dataset), known at the close of its day; positions use it the next day.

Carry (raw measure, annualised):
  currencies (9 G10 against the dollar): foreign minus US 3-month interbank rate (l29_fx);
  commodities (7): ln(front / contract about 12 months later) * 365 / days between them; six-month fallback in 2022 (l29_commodity_check);
  bonds (VFITX, VUSTX): term spread + roll-down, 5y - bill + 4.5 * (5y - 3y) / 2 and 20y - bill + 14 * (20y - 10y) / 10;
  equity (S&P 500): earnings yield (Shiller 12-month earnings, used six months later, over the daily index) minus (bill - 12-month CPI inflation).
  Carry is averaged over 21 days before use. Signal = average of the within-group rank of the level and the rank of the 3-month change.
Value: minus ln(today / average 4.5 to 5.5 years earlier) of a price without income: the real exchange rate (currencies), the front contract
(commodities), the spot index (equity); bonds: the yield minus its average 4.5 to 5.5 years earlier."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[2]; RAW = ROOT.parent / "data" / "raw"
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(ROOT / "lectures" / "28-part-time-strategies" / "scripts"))
import l29_fx as FX, l29_commodity_check as CC, l28 as L28
FT, L26 = L28.FT, L28.L26
DAYS = pd.bdate_range("1999-01-04", "2022-11-18")
COMMOD = list(CC.MARKETS); BONDS = ["VFITX", "VUSTX"]; EQUITY = ["cme-es", "cme-nasdaq"]
LO, HI = int(4.5 * 252), int(5.5 * 252)                                              # 4.5 to 5.5 years back, in business days


def fred_local(sid):
    x = pd.read_csv(RAW / f"fred_{sid}.csv", index_col=0, parse_dates=True).iloc[:, 0]
    return pd.to_numeric(x, errors="coerce").dropna()


def daily(x, limit=5):
    return x.reindex(DAYS.union(x.index)).ffill(limit=limit).reindex(DAYS)


def inflation():
    """Past 12 months' CPI change, each month used from the start of the month two months later."""
    c = fred_local("CPIAUCSL"); i = c / c.shift(12) - 1; i.index = i.index + pd.offsets.MonthBegin(2)
    return daily(i, limit=45)


def bill():
    return daily(fred_local("DTB3")) / 100


# ---------- carry: raw measures ----------
def carry_fx():
    _, _, C = FX.build(); return C.reindex(DAYS)


def carry_commod():
    return pd.DataFrame({t: CC.carry12(t, DAYS)["carry"] for t in COMMOD})


def carry_bonds():
    y = {k: daily(fred_local(f"DGS{k}")) / 100 for k in (3, 5, 10, 20)}; b = bill()
    return pd.DataFrame({"VFITX": y[5] - b + 4.5 * (y[5] - y[3]) / 2, "VUSTX": y[20] - b + 14 * (y[20] - y[10]) / 10})


def shiller():
    x = pd.read_excel(RAW / "l29_shiller_ie_data.xls", sheet_name="Data", header=None, skiprows=8).iloc[:, :4]
    x.columns = ["date", "P", "D", "E"]; x = x[pd.to_numeric(x["date"], errors="coerce").notna()]
    d = x["date"].astype(float); yr = d.astype(int); mo = ((d - yr) * 100).round().astype(int)
    x.index = pd.to_datetime(dict(year=yr, month=mo, day=1)); return x[["P", "D", "E"]].apply(pd.to_numeric, errors="coerce")


def carry_equity():
    E = shiller()["E"].dropna(); E.index = E.index + pd.offsets.MonthBegin(6)          # each month's earnings used six months later
    spx = pd.read_csv(RAW / "l27_spx.csv", index_col=0, parse_dates=True).iloc[:, 0]
    ep = daily(E, limit=45) / daily(spx)
    return pd.DataFrame({"cme-es": ep - (bill() - inflation())})


def smooth(C):
    return C.rolling(21, min_periods=10).mean()


def rank_centred(X):
    """Within-row rank scaled to [-1, 1], centred (NaN where fewer than two markets)."""
    r = X.rank(axis=1); n = X.notna().sum(axis=1)
    return (2 * (r.sub(1)).div(n - 1, axis=0) - 1).where(n >= 2)


def carry_signal(C):
    """Rule: average of the rank of the level and the rank of the 3-month change (63 business days)."""
    C = smooth(C); return (rank_centred(C) + rank_centred(C - C.shift(63))) / 2


# ---------- value ----------
def reversal(P):
    lp = np.log(P); past = lp.shift(LO).rolling(HI - LO + 1, min_periods=(HI - LO) // 2).mean()
    return -(lp - past)


def traded():
    S = pd.read_pickle(FT.CACHE); px = {t: S[t]["ratio"] for t in COMMOD + EQUITY}
    b = FT.bond_funds(); px.update({k: b[k] for k in BONDS})
    return pd.DataFrame({k: daily(v.dropna()) for k, v in px.items()})


def value_fx():
    R = FX.reer(); return (-(R - R.shift(LO).rolling(HI - LO + 1, min_periods=(HI - LO) // 2).mean())).reindex(DAYS)


def spot_prices():
    """Prices without income, for value: commodities the front contract (not rolled; AQR's spot), equities the spot indices."""
    S = pd.read_pickle(FT.CACHE); out = {t: daily(S[t]["raw"].dropna()) for t in COMMOD}
    out["cme-es"] = daily(pd.read_csv(RAW / "l27_spx.csv", index_col=0, parse_dates=True).iloc[:, 0])
    out["cme-nasdaq"] = daily(pd.read_csv(RAW / "l29_ndx.csv", index_col=0, parse_dates=True).iloc[:, 0])
    return pd.DataFrame(out)


def value_bonds():
    """The 5-year change in the matching yield, without coupons: yield above its average 4.5-5.5 years earlier = cheap."""
    y = pd.DataFrame({"VFITX": daily(fred_local("DGS5")), "VUSTX": daily(fred_local("DGS20"))}) / 100
    return y - y.shift(LO).rolling(HI - LO + 1, min_periods=(HI - LO) // 2).mean()


def signals():
    """Raw carry and value per group, as dicts of DataFrames."""
    P = traded()
    carry = {"fx": carry_fx(), "commod": carry_commod(), "bonds": carry_bonds(), "equity": carry_equity()}
    Q = spot_prices()
    value = {"fx": value_fx().drop(columns="USD"), "commod": reversal(Q[COMMOD]), "bonds": value_bonds(), "equity": reversal(Q[EQUITY])}
    return carry, value, P
