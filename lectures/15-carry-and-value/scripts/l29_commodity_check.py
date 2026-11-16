"""Lecture 15, data check before any strategy: commodity carry from the front contract against the contract about twelve months later.
For each day: front = nearest contract with a price that day and more than five business days from its last day; later = the contract with a price that day whose last day is closest
to twelve months after the front's (within 9 to 15 months); where none exists, the furthest contract at least six months ahead (flagged). Carry = ln(F_front / F_later) * 365 / days between their last days.
Reported per market, 2006 to 2022-11-18: share of days with a 12-month pair; share of those days on which the later contract did not trade
(volume zero, a settlement price only) or its price was unchanged from the day before; size of the jump in carry on the days the pair changes,
against ordinary days; and the share of days the 21-day average carry is positive (backwardation)."""
import re
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parents[3]; KAGGLE = ROOT.parent / "data" / "raw" / "kaggle"
CODES = "FGHJKMNQUVXZ"
MARKETS = {"nymex-cl": "Crude oil", "nymex-ng": "Natural gas", "comex-gc": "Gold", "cbot-corn": "Corn", "cbot-soybeans": "Soybeans",
           "cbot-wheat": "Wheat", "ice-cocoa": "Cocoa"}


def contracts(market):
    C = []
    for f in (KAGGLE / market).glob("*.csv"):
        m = re.search(r"([FGHJKMNQUVXZ])(\d{4})\.csv$", f.name)
        x = pd.read_csv(f, index_col=0, parse_dates=True).sort_index(); x = x[x["Close"] > 0]
        if len(x) > 20: C.append((int(m.group(2)) * 12 + CODES.index(m.group(1)), x))
    C.sort(key=lambda c: c[0]); return [c[1] for c in C]


def carry12(market, days):
    C = contracts(market); last = np.array([c.index[-1] for c in C], dtype="datetime64[ns]")
    P = pd.DataFrame({i: c["Close"] for i, c in enumerate(C)}).reindex(days)
    V = pd.DataFrame({i: c["Volume"] for i, c in enumerate(C)}).reindex(days)
    pos = np.searchsorted(last, (days + pd.offsets.BDay(5)).to_numpy())
    out = pd.DataFrame(index=days, columns=["carry", "pair", "stale", "short"], dtype=float)
    PV = np.isfinite(P.to_numpy())
    for k, d in enumerate(days):
        live = np.where(PV[k] & (np.arange(len(C)) >= pos[k]))[0]                # contracts with a price today, past the five-day cut
        if not len(live): continue
        i = live[0]
        gap = (last - last[i]) / np.timedelta64(1, "D"); ok = live[(gap[live] >= 270) & (gap[live] <= 456)]
        if len(ok): j = ok[np.argmin(np.abs(gap[ok] - 365))]
        else:                                                                     # no 12-month contract (2022: the data hold none after Dec 2022)
            far = live[gap[live] >= 182]
            if not len(far): continue
            j = far[-1]; out.at[d, "short"] = 1.0                                  # the furthest one at least six months ahead, flagged
        a, b = P.iat[k, i], P.iat[k, j]
        if np.isfinite(a) and np.isfinite(b):
            prev = P.iat[k - 1, j] if k else np.nan
            out.iloc[k, :3] = [np.log(a / b) * 365 / gap[j], i * 1000 + j, float((V.iat[k, j] == 0) or (b == prev))]
    return out


if __name__ == "__main__":
    days = pd.bdate_range("2006-01-02", "2022-11-18")
    print(f"{'market':12s} {'pair':>6s} {'stale':>6s} {'jump roll':>10s} {'jump other':>10s} {'backw.':>7s} {'median':>7s}")
    for t, name in MARKETS.items():
        X = carry12(t, days); ok = X["carry"].notna()
        roll = X["pair"].diff().fillna(0).ne(0) & ok & ok.shift(1, fill_value=False)
        dc = X["carry"].diff().abs()
        avg = X["carry"].rolling(21, min_periods=10).mean()
        print(f"{name:12s} {ok.mean():6.0%} {X.loc[ok, 'stale'].mean():6.0%} {dc[roll].median():10.2%} {dc[~roll & ok].median():10.2%} "
              f"{(avg.dropna() > 0).mean():7.0%} {X['carry'].median():+7.1%}  2022: carry on {X.loc['2022', 'carry'].notna().mean():.0%} of days, six-month fallback {X['short'].notna().sum()} days")
