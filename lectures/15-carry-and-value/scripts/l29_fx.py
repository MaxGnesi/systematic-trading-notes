"""Lecture 15: currency returns over cash built from spot rates and 3-month interest differentials (the standard construction of currency carry).
For each G10 currency against the dollar, the daily return over US cash of holding the foreign currency in a foreign deposit:
    r_t = S_t / S_{t-1} - 1 + (i*_m - i_m) * days / 365,
S = dollars per unit of foreign currency (FRED H.10 noon rates, daily), i* and i = the foreign and US 3-month interbank rates (OECD via FRED, monthly averages),
the rates of the previous month applied through the current month, so every number is known on the day. Both legs use the same source (interbank) so the
gap is not a credit spread. Data downloaded once from FRED (free, no key) into data/raw/l29_fx and kept local.
Checks: the euro and the yen against the capstone futures (covered interest parity says a future's return over cash is the same thing)."""
import subprocess, sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT.parent / "data" / "raw"; FXDIR = RAW / "l29_fx"
SPOT = {"EUR": ("DEXUSEU", False), "JPY": ("DEXJPUS", True), "GBP": ("DEXUSUK", False), "CHF": ("DEXSZUS", True), "CAD": ("DEXCAUS", True),
        "AUD": ("DEXUSAL", False), "NZD": ("DEXUSNZ", False), "NOK": ("DEXNOUS", True), "SEK": ("DEXSDUS", True)}      # True: quoted as foreign per dollar
RATE = {"EUR": "EZ", "JPY": "JP", "GBP": "GB", "CHF": "CH", "CAD": "CA", "AUD": "AU", "NZD": "NZ", "NOK": "NO", "SEK": "SE", "USD": "US"}


def fred(sid):
    f = FXDIR / f"{sid}.csv"
    if not f.exists():
        FXDIR.mkdir(parents=True, exist_ok=True)
        subprocess.run(["curl", "-s", "-f", "-m", "120", "-o", str(f), f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"], check=True)
    x = pd.read_csv(f, index_col=0, parse_dates=True).iloc[:, 0]
    return pd.to_numeric(x, errors="coerce").dropna()


def build():
    days = pd.bdate_range("1999-01-04", "2026-10-30")
    us = fred(f"IR3TIB01{RATE['USD']}M156N")
    S, R, C = {}, {}, {}
    for c, (sid, inv) in SPOT.items():
        s = fred(sid); s = (1 / s) if inv else s                                  # dollars per unit of foreign currency
        s = s.reindex(days).ffill(limit=5)
        i = fred(f"IR3TIB01{RATE[c]}M156N")
        gap = (i - us).dropna() / 100                                             # monthly average of month m
        gap.index = gap.index + pd.offsets.MonthBegin(1)                          # applied through month m+1: known on the day
        g = gap.reindex(days, method="ffill", limit=45)                           # a month plus slack; a series that stops publishing goes blank, not stale
        dt = pd.Series(days, index=days).diff().dt.days
        R[c] = s.pct_change() + g.shift(0) * dt / 365
        S[c], C[c] = s, g
    return pd.DataFrame(S), pd.DataFrame(R), pd.DataFrame(C)


REER = {"EUR": "XM", "JPY": "JP", "GBP": "GB", "CHF": "CH", "CAD": "CA", "AUD": "AU", "NZD": "NZ", "NOK": "NO", "SEK": "SE", "USD": "US"}


def reer():
    """BIS real broad effective exchange rates (FRED RB..BIS, monthly, 1994-), each month usable from the start of the month two months later
    (the BIS publishes in the middle of the following month), as a daily table of log levels; higher = dearer in real terms."""
    days = pd.bdate_range("1994-01-03", "2026-10-30"); out = {}
    for c, k in REER.items():
        x = np.log(fred(f"RB{k}BIS")); x.index = x.index + pd.offsets.MonthBegin(2)
        out[c] = x.reindex(days, method="ffill", limit=45)
    return pd.DataFrame(out)


if __name__ == "__main__":
    S, R, C = build()
    print("coverage (first and last day with a return):")
    for c in R:
        r = R[c].dropna(); print(f"  {c}: {r.index[0].date()} to {r.index[-1].date()}  carry now {C[c].dropna().iloc[-1]:+.2%}")
    # check against the capstone futures: returns over cash should match (covered interest parity), apart from the time of the close
    sys.path.insert(0, str(ROOT / "lectures" / "14-regime-filters" / "scripts")); import l28 as L
    F = pd.read_pickle(L.FT.CACHE)
    for c, t, sign in (("EUR", "cme-euro", 1), ("JPY", "cme-jpy", 1)):
        f = F[t]["ratio"].pct_change() * sign
        both = pd.concat([R[c], f], axis=1, keys=["built", "future"]).loc["2000":"2022-11-18"].dropna()
        m = (1 + both).resample("ME").prod() - 1
        diff = (m["built"] - m["future"]).mean() * 12
        print(f"{c}: daily corr {both.corr().iat[0, 1]:.3f}, monthly corr {m.corr().iat[0, 1]:.3f}; return a year built {m['built'].mean() * 12:+.2%}, "
              f"future {m['future'].mean() * 12:+.2%}, gap {diff:+.2%}; carry average {C[c].loc['2000':'2022'].mean():+.2%}")
