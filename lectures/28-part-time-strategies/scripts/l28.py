"""Lecture 28, part-time strategies: the regime series of both families and the two baselines (results/hypotheses.md).

Baselines: Lecture 27's ETF portfolio (out of sample 2013-2026, from its daily file) and the capstone futures portfolio (Lecture 26's end-2025
held speeds, equal weights, markets equal risk in a class, classes equal risk, total scaled yearly to 10%), with each day's gross exposure,
needed to charge the cost of switching.
Regime series, each known at the close of the day before it is used:
  macro (monthly, data as first published, Philadelphia Fed Real-Time Data Set): growth = |12-month change of industrial production's
    year-on-year growth|, inflation = the same for CPI, each against the full history of the vintage in use; Fed = no change in the target
    rate in the past six months; the growth x inflation quadrant (signs of the 12-month changes) for the scan;
  market state (daily): VIX 21-day average; average absolute pairwise correlation of the baseline's markets over 126 days; share of markets
    whose 21-day and 252-day returns disagree in sign; |252-day change| of the 10y-2y yield spread; |252-day log change| of the broad dollar.
Usage: python l28.py. Output: OUT/l28_base.parquet, OUT/l28_regimes_{etf,futures}.parquet, OUT/l28_macro.parquet."""
import json, os, sys, urllib.request, warnings; warnings.filterwarnings("ignore")
from pathlib import Path
import numpy as np, pandas as pd

LECTURE = Path(__file__).resolve().parents[1]; REPO = LECTURE.parents[1]
sys.path.insert(0, str(REPO / "lectures" / "27-the-baseline-trend-portfolio" / "scripts")); import l27 as M27, l27_futures_test as FT
L26, L25 = M27.L26, M27.L25
RESULTS = Path(os.environ.get("L28_RESULTS", LECTURE / "results")); FIG = LECTURE / "figures"; RESULTS.mkdir(parents=True, exist_ok=True)
OUT = Path(os.environ.get("L28_OUT", L25.DATA / "l28")); OUT.mkdir(parents=True, exist_ok=True)
RAW = Path(L25.DATA).parent; RT = RAW / "l28_realtime"; RT.mkdir(parents=True, exist_ok=True)
PREFIX = os.environ.get("L28_PREFIX", "")
COST_BP, LAMBDA = 5.0, 0.10
FRACS = {"still": (0.25, 1 / 3, 0.5), "busy": (0.75, 2 / 3, 0.5)}           # threshold grid; the middle value is the fixed one
FUT_START, ETF_START = "2006-01-01", "2013-01-01"
FRED = ("DFEDTAR", "DFEDTARU", "T10Y2Y", "DTWEXB", "DTWEXBGS", "VIXCLS", "CPIAUCSL", "INDPRO")
PHILLY = {"PCPI": "pcpiMvMd.xlsx", "IPT": "iptMvMd.xlsx"}


def fred(code):
    """A FRED series (free, no account), saved once under data/raw/l28_realtime."""
    f = RT / f"fred_{code}.csv"
    if not f.exists(): urllib.request.urlretrieve(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={code}", f)
    s = pd.read_csv(f, index_col=0, parse_dates=True).iloc[:, 0]; return pd.to_numeric(s, errors="coerce").dropna()


def philly(code):
    """Monthly vintages of the Philadelphia Fed Real-Time Data Set, saved once; columns = vintages, index = observation month."""
    f = RT / PHILLY[code]
    if not f.exists():
        urllib.request.urlretrieve(f"https://www.philadelphiafed.org/-/media/frbp/assets/surveys-and-data/real-time-data/data-files/xlsx/{PHILLY[code].lower()}", f)
    d = pd.read_excel(f); d.index = pd.PeriodIndex(d.pop("DATE").str.replace(":", "-"), freq="M"); return d.apply(pd.to_numeric, errors="coerce")


def vintage_day(col):
    """'PCPI98M11' -> 16 November 1998: a vintage reflects data available in mid-month and is used from the 16th."""
    import re
    yy, mm = re.search(r"(\d{2})M(\d{1,2})$", col).groups(); y = int(yy); y += 1900 if y > 50 else 2000
    return pd.Timestamp(year=y, month=int(mm), day=16)


def macro_measure(x):
    """|12-month change of the year-on-year rate| and the signed change, on one vintage (or the revised series)."""
    yoy = x / x.shift(12) - 1; d = yoy - yoy.shift(12); return d.abs(), d


def macro_realtime(code):
    """For each vintage: the latest measure, its quantiles over the vintage's full history, and the sign of the latest change."""
    V = philly(code); rows = {}
    for col in V.columns:
        x = V[col].dropna()
        if len(x) < 60: continue
        m, d = macro_measure(x); m = m.dropna()
        rows[vintage_day(col)] = dict(m=m.iloc[-1], sign=np.sign(d.dropna().iloc[-1]), obs=str(m.index[-1]),
                                      **{f"q{f:.2f}": m.quantile(f) for f in FRACS["still"]})
    return pd.DataFrame(rows).T.sort_index()


def macro_revised(series):
    """The same measures on today's revised data, dated at the end of each observation month (the look-ahead version)."""
    x = series.resample("ME").last(); m, d = macro_measure(x); out = pd.DataFrame({"m": m, "sign": np.sign(d)}).dropna()
    for f in FRACS["still"]: out[f"q{f:.2f}"] = m.expanding(60).quantile(f)
    return out


def daily_from_monthly(df, days):
    return df.reindex(df.index.union(days)).ffill().reindex(days)


def fed_on_hold(days):
    tgt = pd.concat([fred("DFEDTAR")[:"2008-12-15"], fred("DFEDTARU")["2008-12-16":]]).sort_index()
    chg = tgt.diff().fillna(0).ne(0).astype(float); last = chg.rolling("183D").sum()      # changes in the past six months
    return daily_from_monthly(last.to_frame("n"), days)["n"].eq(0)


def expanding_flags(x, kind):
    """Lagged measure against the quantiles of its own history to date (at least five years), for each threshold of the grid."""
    x = x.shift(1); out = {}
    for f in FRACS[kind]:
        q = x.expanding(1260).quantile(f)
        out[f"{f:.2f}"] = (x <= q) if kind == "still" else (x >= q)
        out[f"{f:.2f}"] = out[f"{f:.2f}"].where(q.notna())
    return pd.DataFrame(out)


def dollar():
    a, b = fred("DTWEXB"), fred("DTWEXBGS"); ra = np.log(a).diff(); rb = np.log(b).diff()
    r = pd.concat([ra[: b.index[0] - pd.Timedelta(days=1)], rb]).dropna(); return r.cumsum()


def market_state(R, members, days):
    """R: daily excess returns of all the baseline's markets, full history; members(day) -> the markets the baseline holds that day."""
    vix = fred("VIXCLS").reindex(days).ffill().rolling(21).mean()
    R = R.reindex(days); vals = R.to_numpy(); col = {t: j for j, t in enumerate(R.columns)}
    corr = pd.Series(np.nan, index=days); turn = pd.Series(np.nan, index=days)
    lp = np.log1p(R.fillna(0)).cumsum().to_numpy()
    for i in range(252, len(days)):
        js = [col[t] for t in members(days[i]) if t in col]
        w = vals[i - 125: i + 1, js]; ok = np.isnan(w).mean(axis=0) <= 0.1                  # a market needs 90% of the window
        if ok.sum() >= 5:
            c = pd.DataFrame(w[:, ok]).corr(min_periods=100).to_numpy(); corr.iloc[i] = np.nanmean(np.abs(c[np.triu_indices(ok.sum(), 1)]))
        full = ~np.isnan(vals[i - 251: i + 1, js]).all(axis=0) & (np.isnan(vals[i - 251: i + 1, js]).mean(axis=0) <= 0.1)
        if full.sum() >= 5:
            jj = np.array(js)[full]; s1 = np.sign(lp[i, jj] - lp[i - 21, jj]); s12 = np.sign(lp[i, jj] - lp[i - 252, jj]); turn.iloc[i] = float(np.mean(s1 != s12))
    curve = (fred("T10Y2Y").reindex(days).ffill().diff(252)).abs()
    usd = dollar().reindex(days).ffill().diff(252).abs()
    meas = pd.DataFrame({"volatility": vix, "correlation": corr, "turning": turn, "curve": curve, "dollar": usd})
    kinds = {"volatility": "still", "correlation": "busy", "turning": "busy", "curve": "still", "dollar": "still"}
    flags = {k: expanding_flags(meas[k], kinds[k]) for k in kinds}
    return meas, flags


def etf_inputs():
    D = pd.read_parquet(M27.OUT / "l27_daily.parquet"); base = pd.DataFrame({"ret": D["rule"], "gross": D.gross_U * D.ctot})
    close, high, low, dv, rf = L26.load_daily(); uni = {y: [t for m in M27.UNI[str(y)]["sc_div"].values() for t in m] for y in range(2012, 2026)}
    R = {}
    for t in sorted({t for v in uni.values() for t in v}):
        c = close[t].dropna(); R[t] = L26.excess(c, high[t].reindex(c.index), low[t].reindex(c.index), rf)[0].pct_change()
    members = lambda d: uni[min(max(d.year - 1, 2012), 2025)]                       # the markets chosen at the previous year end
    return base, pd.DataFrame(R).sort_index(), members


def futures_inputs():
    """The capstone futures baseline (as Lecture 27's futures test, equal weights) with its daily gross exposure, and the markets' returns."""
    S = pd.read_pickle(FT.CACHE); px = {k: S[k]["ratio"] for k in S if k in FT.CLASS}
    tb = pd.to_numeric(pd.read_csv(RAW / "fred_DTB3.csv", index_col=0, parse_dates=True).iloc[:, 0], errors="coerce"); fx = FT.bond_funds()
    for t in ("VFITX", "VUSTX"):
        r = fx[t].pct_change() - (tb.reindex(fx.index).ffill() / 100 / 252).shift(1); px[t] = 100 * (1 + r.fillna(0)).cumprod()
    N, P, R = {}, {}, {}
    for t, p in px.items():
        x = p.dropna(); x = x[x > 0]; N[t] = L26.net(L26.stream_returns(x, x, x))[FT.HELD].mean(axis=1)
        P[t] = M27.positions(x, x, x)[FT.HELD].mean(axis=1); R[t] = x.pct_change()
    N, P, R = pd.DataFrame(N), pd.DataFrame(P), pd.DataFrame(R)
    days, gross = [], []
    for y in range(2002, 2022):
        hist, nxt = slice(f"{y - 2}-01-01", f"{y}-12-31"), slice(f"{y + 1}-01-01", f"{y + 1}-12-31"); a = 1 / N.loc[hist].std(); pe, w = {}, {}
        cl = [k for k in sorted(set(FT.CLASS.values())) if any(FT.CLASS[t] == k and N[t].loc[hist].notna().sum() > 500 for t in N)]
        for k in cl:
            m = [t for t in N if FT.CLASS[t] == k and N[t].loc[hist].notna().sum() > 500]
            be = N[m].mul(a[m]).mean(axis=1); sc = (M27.TARGET / np.sqrt(252)) / be.loc[hist].std(); pe[k] = be * sc
            for t in m: w[t] = a[t] * sc / len(m) / len(cl)
        U = pd.DataFrame(pe).mean(axis=1); ct = (M27.TARGET / np.sqrt(252)) / U.loc[hist].std()
        days.append((U * ct).loc[nxt]); gross.append((P[list(w)].shift(1).mul(pd.Series(w) * ct).abs().sum(axis=1)).loc[nxt])
    base = pd.DataFrame({"ret": pd.concat(days), "gross": pd.concat(gross)}).dropna()
    return base, R, (lambda d: list(R.columns))


if __name__ == "__main__":
    base_e, R_e, mem_e = etf_inputs(); base_f, R_f, mem_f = futures_inputs()
    print(f"ETF baseline {base_e.index[0].date()}-{base_e.index[-1].date()} Sharpe {L26.sharpe(base_e.ret):.3f} gross {base_e.gross.median():.2f}; "
          f"futures {base_f.index[0].date()}-{base_f.index[-1].date()} Sharpe {L26.sharpe(base_f.ret):.3f} gross {base_f.gross.median():.2f}", flush=True)
    pd.concat({"etf": base_e, "futures": base_f}, axis=1).to_parquet(OUT / "l28_base.parquet")
    days_all = pd.bdate_range("1998-01-01", "2026-12-31")
    # macro, real time and revised
    MAC = {}
    for code, name, rev in (("IPT", "growth", "INDPRO"), ("PCPI", "inflation", "CPIAUCSL")):
        rt = macro_realtime(code); rv = macro_revised(fred(rev))
        MAC[name] = rt; MAC[name + "_revised"] = rv
        print(name, "real-time vintages", rt.index[0].date(), "to", rt.index[-1].date(), flush=True)
    pd.concat(MAC, axis=1).to_parquet(OUT / "l28_macro.parquet")
    hold = fed_on_hold(days_all)
    for tag, R, mem, base in (("etf", R_e, mem_e, base_e), ("futures", R_f, mem_f, base_f)):
        days = pd.bdate_range(R.index[0], base.index[-1]); meas, flags = market_state(R, mem, days)
        cols = {}
        for k, F in flags.items():
            for f, s in F.items(): cols[(k, f)] = s
            cols[(k, "measure")] = meas[k]
        for name in ("growth", "inflation"):
            for src in ("", "_revised"):
                g = MAC[name + src]; dd = daily_from_monthly(g, days).shift(1)
                for f in FRACS["still"]: cols[(name + src, f"{f:.2f}")] = (dd["m"] <= dd[f"q{f:.2f}"]).where(dd["m"].notna())
                cols[(name + src, "measure")] = dd["m"].astype(float); cols[(name + src, "sign")] = dd["sign"].astype(float)
        cols[("fed", "hold")] = hold.reindex(days).shift(1)
        G = pd.DataFrame(cols); G.columns = pd.MultiIndex.from_tuples(G.columns)
        G.to_parquet(OUT / f"l28_regimes_{tag}.parquet")
        on = G.loc[base.index[0]:]
        print(tag, "share of days off at the fixed threshold:", {k: round(float(on[(k, "0.33" if k not in ("correlation", "turning") else "0.67")].mean()), 2)
              for k in ("volatility", "correlation", "turning", "curve", "dollar", "growth", "inflation")}, "| Fed on hold", round(float(on[("fed", "hold")].mean()), 2), flush=True)
