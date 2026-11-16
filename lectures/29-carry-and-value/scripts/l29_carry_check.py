"""Lecture 29, data check before any strategy: carry of the equity-index futures measured two ways.
Spot against the front future: carry = ln(S / F_front) * 365 / days to the front's last day; for an index this is dividend yield minus the rate,
so dividend yield implied = carry + bill rate (should be close to the index's known dividend yield: S&P 500 about 1.2-2.2%, Nasdaq-100 about 0.6-1.2%).
Front against next: ln(F_front / F_next) * 365 / days between their last days. The front is the nearest contract more than five business days
from its last day in the data (as Lecture 28 §7). Spot: S&P 500 (local) and Nasdaq-100 (Yahoo ^NDX, free, saved locally once)."""
import re, sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parents[3]; RAW = ROOT.parent / "data" / "raw"; KAGGLE = RAW / "kaggle"
CODES = "FGHJKMNQUVXZ"


def contracts(market):
    C = []
    for f in (KAGGLE / market).glob("*.csv"):
        m = re.search(r"([FGHJKMNQUVXZ])(\d{4})\.csv$", f.name)
        x = pd.read_csv(f, index_col=0, parse_dates=True)["Close"].sort_index().dropna(); x = x[x > 0]
        if len(x) > 20: C.append((int(m.group(2)) * 12 + CODES.index(m.group(1)), x))
    C.sort(key=lambda c: c[0]); return [c[1] for c in C]


def front_next(market, days, lag=5, step=1):
    """Daily front price, the price of the contract `step` places later, and both last days."""
    C = contracts(market); last = np.array([c.index[-1] for c in C], dtype="datetime64[ns]")
    P = pd.DataFrame({i: c for i, c in enumerate(C)}).reindex(days)
    pos = np.searchsorted(last, (days + pd.offsets.BDay(lag)).to_numpy())
    out = pd.DataFrame(index=days, columns=["front", "later", "t_front", "t_later"], dtype=float)
    for k, d in enumerate(days):
        i = pos[k]
        if i + step < len(C):
            out.iloc[k] = [P.iat[k, i], P.iat[k, i + step], (last[i] - d.to_datetime64()) / np.timedelta64(1, "D"),
                           (last[i + step] - last[i]) / np.timedelta64(1, "D")]
    return out


def spot_ndx():
    f = RAW / "l29_ndx.csv"
    if not f.exists():
        import yfinance as yf
        yf.download("^NDX", start="1999-01-01", end="2023-01-01", auto_adjust=False, progress=False)["Close"].to_csv(f)
    return pd.read_csv(f, index_col=0, parse_dates=True).iloc[:, 0]


if __name__ == "__main__":
    days = pd.bdate_range("2000-01-03", "2022-11-18")
    bill = pd.read_csv(RAW / "fred_DTB3.csv", index_col=0, parse_dates=True).iloc[:, 0].apply(pd.to_numeric, errors="coerce").reindex(days).ffill() / 100
    spots = {"cme-es": pd.read_csv(RAW / "l27_spx.csv", index_col=0, parse_dates=True).iloc[:, 0], "cme-nasdaq": spot_ndx()}
    for mkt, s in spots.items():
        F = front_next(mkt, days); s = s.reindex(days)
        c_spot = np.log(s / F["front"]) * 365 / F["t_front"].where(F["t_front"] > 10)       # skip the last days: tiny horizon, noisy ratio
        c_fn = np.log(F["front"] / F["later"]) * 365 / F["t_later"]
        dy = c_spot + bill
        both = pd.concat([c_spot, c_fn], axis=1, keys=["spot", "fn"]).dropna()
        m = both.resample("ME").mean()
        print(f"{mkt}: days {len(both)}; implied dividend yield median {dy.median():.2%} (by period: "
              + ", ".join(f"{a}-{b} {dy.loc[str(a):str(b)].median():.2%}" for a, b in ((2000, 2007), (2008, 2015), (2016, 2022))) + ")")
        print(f"   carry spot-front: median {c_spot.median():+.2%}, daily std {c_spot.std():.2%};  front-next: median {c_fn.median():+.2%}, daily std {c_fn.std():.2%}")
        print(f"   correlation spot-front vs front-next: daily {both.corr().iat[0, 1]:.2f}, monthly averages {m.corr().iat[0, 1]:.2f}; "
              f"same sign on {(np.sign(both['spot']) == np.sign(both['fn'])).mean():.0%} of days")
