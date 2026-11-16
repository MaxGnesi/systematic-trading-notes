"""Lecture 29: a cross-country government bond group, as AQR builds it (correction of 2026-11-16: two US maturities compare the curve, not countries).
Ten markets: 10-year government bonds of the US, Germany (for the euro), Japan, the UK, Canada, Australia, New Zealand, Norway, Sweden, Switzerland.
Monthly return over local cash, which is also the dollar-hedged return over US cash (hedging swaps local cash for dollar cash):
    r_m = y_{m-1} / 12 - D_{m-1} * (y_m - y_{m-1}) - c_{m-1} / 12,   D = duration of a 10-year par bond at yield y,
with y the OECD long-term (10-year) yield and c the OECD 3-month interbank rate (FRED, free, monthly averages: they smooth the monthly change a
little, a stated limitation). Signals, known at the end of the month before the position:
    carry = y - c (term spread; no roll-down, which would need a 9-year yield);
    value, AQR's version = the yield minus its average 4.5 to 5.5 years earlier (a yield above its past = cheap);
    value, our rule = the yield against its own 10-year trend line, as a z-score;
    momentum (check only) = the past 12-month return, skipping the last month.
Machinery, monthly: weights within the group (rank, or score: half absolute, half per unit of risk), each position = weight x 10% / its 36-month
volatility, 5 bp per unit traded, the group scaled each year to 10% on its past three years.
Checks: US synthetic against VFITX; momentum and value against AQR's bond factors (VME, monthly)."""
import subprocess, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l29 as L
LT = {"US": "US", "DE": "DE", "JP": "JP", "GB": "GB", "CA": "CA", "AU": "AU", "NZ": "NZ", "NO": "NO", "SE": "SE", "CH": "CH"}
ST = {"US": "US", "DE": "EZ", "JP": "JP", "GB": "GB", "CA": "CA", "AU": "AU", "NZ": "NZ", "NO": "NO", "SE": "SE", "CH": "CH"}
DIR = L.RAW / "l29_bonds"; TARGET, COST = 0.10, 0.0005


def fred(sid):
    f = DIR / f"{sid}.csv"
    if not f.exists():
        DIR.mkdir(parents=True, exist_ok=True)
        subprocess.run(["curl", "-s", "-f", "-m", "120", "-o", str(f), f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"], check=True)
    x = pd.read_csv(f, index_col=0, parse_dates=True).iloc[:, 0]
    return pd.to_numeric(x, errors="coerce").dropna()


def data():
    Y = pd.DataFrame({c: fred(f"IRLTLT01{k}M156N") for c, k in LT.items()}) / 100
    C = pd.DataFrame({c: L.FX.fred(f"IR3TIB01{k}M156N") for c, k in ST.items()}) / 100
    Y.index, C.index = Y.index.to_period("M"), C.index.to_period("M")
    C = C.reindex(Y.index)
    return Y.loc["1990":], C.loc["1990":]


def month_end():
    """Month-end 10-year yields: FRED DGS10 for the US, each central bank's daily series for the others (data/raw/l29_bonds/daily, SOURCES.md);
    New Zealand's central bank blocks automated downloads, so New Zealand has no month-end series (left out of the returns)."""
    E = {"US": L.fred_local("DGS10")}
    for c in ("DE", "GB", "CA", "AU", "NO", "SE", "CH", "JP"):
        E[c] = pd.read_csv(DIR / "daily" / f"{c}.csv", index_col=0, parse_dates=True)["yield"]
    E = pd.DataFrame({c: x.resample("ME").last() for c, x in E.items()}) / 100; E.index = E.index.to_period("M")
    return E


def returns(Y, C, E=None):
    """Return over local cash from month-end yields E where given (rule); from the OECD monthly averages Y otherwise (the check)."""
    X = (E if E is not None else Y).reindex(columns=Y.columns)
    y0 = X.shift(1); D = (1 - (1 + y0) ** -10) / y0
    return y0 / 12 - D * (X - y0) - C.shift(1) / 12


def zrow(X):
    n = X.notna().sum(axis=1); return X.sub(X.mean(axis=1), axis=0).div(X.std(axis=1, ddof=0), axis=0).where(n >= 2)


def rank_centred(X):
    r = X.rank(axis=1); n = X.notna().sum(axis=1); return (2 * (r - 1).div(n - 1, axis=0) - 1).where(n >= 2)


def trend_z(Y, years=10):
    n = years * 12; t = np.arange(n); out = Y * np.nan
    for c in Y:
        x = Y[c].to_numpy(dtype=float)
        for k in range(n, len(x)):
            w = x[k - n:k]
            if np.isfinite(w).sum() >= 0.8 * n and np.isfinite(x[k]):
                ok = np.isfinite(w); b = np.polyfit(t[ok], w[ok], 1); sd = np.std(w[ok] - (b[0] * t[ok] + b[1]), ddof=2)
                out.iat[k, out.columns.get_loc(c)] = (x[k] - (b[0] * n + b[1])) / sd          # a yield above its line = cheap
    return out


def stream(W, R):
    """Monthly group return from weights W (known at the end of the month before), vol-scaled, net of costs, scaled yearly to 10%."""
    W = W.div(W.abs().sum(axis=1), axis=0)
    vol = R.rolling(36, min_periods=24).std().shift(1) * np.sqrt(12)
    pos = (W * TARGET / vol).shift(1)                                                   # held during month m, set at the end of m-1
    r = (pos * R).sum(axis=1, min_count=1) - pos.diff().abs().sum(axis=1) * COST
    r = r.where(pos.notna().any(axis=1))
    out = []
    for y in sorted(set(r.index.year)):
        h = r[(r.index.year >= y - 3) & (r.index.year < y)].dropna()
        if len(h) >= 24: out.append(r[r.index.year == y] * (TARGET / np.sqrt(12)) / h.std())
    return pd.concat(out)


def sharpe_m(r):
    r = r.dropna(); return float(r.mean() / r.std() * np.sqrt(12))


def aqr():
    d = pd.read_excel(L.RAW / "l29_aqr" / "vme_factors_monthly.xlsx", "VME Factors", header=21)
    d.index = pd.DatetimeIndex(pd.to_datetime(d.pop("DATE"))).to_period("M"); return d.apply(pd.to_numeric, errors="coerce")


if __name__ == "__main__":
    Y, C = data(); E = month_end().reindex(Y.index); R = returns(Y, C, E)
    print("first month with yield and cash:", {c: str(pd.concat([Y[c], C[c]], axis=1).dropna().index[0]) for c in Y})
    # check 1: US synthetic vs VFITX (monthly, over US cash)
    vf = L.FT.bond_funds()["VFITX"].resample("ME").last().pct_change(); vf.index = vf.index.to_period("M")
    us = pd.concat([R["US"], vf - C["US"].shift(1) / 12], axis=1).loc["1999":"2022"].dropna()
    print("countries with month-end returns:", [c for c in R if R[c].loc["2006":].notna().any()])
    print(f"check 1: synthetic US 10-year vs VFITX, monthly corr {us.corr().iat[0, 1]:.2f}; return a year {us.iloc[:, 0].mean() * 12:+.2%} vs {us.iloc[:, 1].mean() * 12:+.2%}")
    A = aqr(); S, E = "2006-01", "2022-10"
    mom = (np.log1p(R).rolling(11).sum()).shift(1)                                     # months t-12..t-2
    sig = {"momentum (check)": rank_centred(mom), "value, AQR's version": rank_centred(Y - Y.shift(54).rolling(13).mean()),
           "value, our rule (10-year line, z)": rank_centred(trend_z(Y)),
           "carry, rank": rank_centred(Y - C), "carry, score": (zrow(Y - C) + zrow((Y - C) / (R.rolling(36, min_periods=24).std().shift(1) * np.sqrt(12)))) / 2}
    ref = {"momentum (check)": "MOMLS_VME_FI", "value, AQR's version": "VALLS_VME_FI", "value, our rule (10-year line, z)": "VALLS_VME_FI"}
    out = {}
    for k, w in sig.items():
        s = stream(w, R).loc[S:E]; out[k] = s
        extra = f", corr with AQR {pd.concat([s, A[ref[k]]], axis=1).dropna().corr().iat[0, 1]:+.2f} (AQR Sharpe {sharpe_m(A[ref[k]].loc[S:E]):+.2f})" if k in ref else ""
        print(f"{k:36s} Sharpe {sharpe_m(s):+.2f}{extra}")
    pd.DataFrame(out).to_timestamp(how="end").to_parquet(L.RAW / "l29_bonds_g10.parquet")
