"""Lecture 13, correlation regimes across classes (results/hypotheses.md, 2026-11-16, plan fixed before any data was loaded).

Three ideas: (1) how far correlations across classes move between regimes, 1973-2026; (2) choosing markets on their bad-regime overlap,
here thematic ETFs judged through a long-history parent; (3) the total scaled to 10% on the last three years, stressed with each regime's
correlations. Two views: the assets' monthly returns, and each class's 12-month trend stream (the portfolio holds positioned streams).
Data (free, local or fetched once): Shiller S&P 500; US 10-year yield (FRED DGS10); World Bank commodity prices; the dollar against major
currencies (FRED daily rates); Baa corporate yield (FRED BAA, monthly); 3-month bill (FRED DTB3); Kenneth French 49 industry portfolios.
Output: results/regimes.json, figures/27_regimes.png. Usage: python l27_regimes.py"""
import io, json, os, sys, urllib.request, zipfile, warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path[:0] = [str(REPO)]
from trading_models.data.fred import load_fred  # noqa: E402

RAW = Path(os.environ["PORTFOLIO_DATA"]).parent if "PORTFOLIO_DATA" in os.environ else REPO.parent / "data" / "raw"   # long series sit next to the portfolio data
RES, FIG = HERE.parent / "results", HERE.parent / "figures"
WINDOWS = {"1973-1982 high inflation": ("1973-01", "1982-12"), "1983-1999 disinflation": ("1983-01", "1999-12"),
           "2000-2002 equity bear market": ("2000-01", "2002-12"), "2003-2006 calm": ("2003-01", "2006-12"),
           "2007-2009 financial crisis": ("2007-01", "2009-12"), "2010-2019 low rates": ("2010-01", "2019-12"),
           "2020 pandemic": ("2020-02", "2020-12"), "2022-2024 inflation's return": ("2022-01", "2024-12")}
RECENT = ("2023-01", "2025-12")                                    # the baseline's own view: three years to end-2025
WORST = ["2000-2002 equity bear market", "2007-2009 financial crisis", "2022-2024 inflation's return"]
CLASSES = ["Equity", "Government bonds", "Credit", "Commodities", "Dollar"]


def month_end(s):
    return s.dropna().resample("ME").last()


def classes():
    """Monthly excess returns over the bill, 1973 onwards (log changes for commodities and the dollar)."""
    bill = month_end(load_fred(["DTB3"])["DTB3"]) / 100
    # equity: Shiller total return
    x = pd.read_excel(RAW / "l29_shiller_ie_data.xls", sheet_name="Data", header=None, skiprows=8).iloc[:, :3]
    x.columns = ["date", "P", "D"]; x = x[pd.to_numeric(x["date"], errors="coerce").notna()]
    d = x["date"].astype(float); yr = d.astype(int); mo = ((d - yr) * 100).round().astype(int)
    x.index = pd.to_datetime(dict(year=yr, month=mo, day=1)) + pd.offsets.MonthEnd(0)
    P, D = pd.to_numeric(x["P"], errors="coerce"), pd.to_numeric(x["D"], errors="coerce")
    eq = (P + D / 12) / P.shift(1) - 1
    # government bonds: 10-year par bond from the yield, r = y/12 - D_mod * dy
    y = month_end(load_fred(["DGS10"])["DGS10"]) / 100
    dur = (1 - (1 + y / 2) ** -20) / y
    gb = y.shift(1) / 12 - dur.shift(1) * y.diff()
    # credit: Baa over Treasuries, excess return from spread changes, r = s/12 - D * ds
    baa = load_fred(["BAA"])["BAA"].dropna() / 100; baa.index = baa.index + pd.offsets.MonthEnd(0)
    s = (baa - y).dropna()
    cr = s.shift(1) / 12 - dur.reindex(s.index).shift(1) * s.diff()
    # commodities: World Bank monthly prices, equal-weight log change of the seven series
    wb = pd.read_csv(RAW / "l29_long" / "wb_commodities_monthly.csv", index_col=0, parse_dates=True)
    wb.index = wb.index + pd.offsets.MonthEnd(0)
    cm = np.log(wb).diff().mean(axis=1, skipna=True)
    # the dollar against majors: equal-weight log change of USD per foreign currency inverted (dollar up = positive)
    fx = {}
    for f, inv in [("DEXJPUS", False), ("DEXCAUS", False), ("DEXSZUS", False), ("DEXUSUK", True), ("DEXUSAL", True)]:
        z = pd.read_csv(RAW / "l29_fx" / f"{f}.csv", index_col=0, parse_dates=True).iloc[:, 0]
        z = month_end(pd.to_numeric(z, errors="coerce")); fx[f] = -np.log(z).diff() if inv else np.log(z).diff()
    de = month_end(pd.to_numeric(pd.read_csv(RAW / "l29_fx" / "EXGEUS.csv", index_col=0, parse_dates=True).iloc[:, 0], errors="coerce"))
    eu = month_end(pd.to_numeric(pd.read_csv(RAW / "l29_fx" / "DEXUSEU.csv", index_col=0, parse_dates=True).iloc[:, 0], errors="coerce"))
    fx["DEM/EUR"] = pd.concat([np.log(de).diff().loc[:"1998-12"], -np.log(eu).diff().loc["1999-02":]])
    dx = pd.DataFrame(fx).mean(axis=1, skipna=True)
    R = pd.DataFrame({"Equity": eq - bill / 12, "Government bonds": gb - bill.shift(1) / 12, "Credit": cr, "Commodities": cm, "Dollar": dx})
    return R.loc["1972-01":"2025-12"]


def trend_streams(R):
    """Each class's 12-month trend stream: sign of the past 12 months' return times the next month's return, scaled to unit risk
    on the past 36 months (known at the time)."""
    sig = np.sign(R.rolling(12).sum().shift(1))
    S = sig * R
    return S / S.rolling(36, min_periods=24).std().shift(1)


def corr(X, a, b):
    return X.loc[a:b].dropna().corr()


def avg_abs(C):
    m = np.abs(C.to_numpy()); n = len(m)
    return float((m.sum() - n) / (n * (n - 1)))


def stressed_ratio(C_recent, C):
    """Volatility of equal-risk weights under C, relative to the volatility they had under C_recent (the 10% target's matrix)."""
    w = np.ones(len(C)) / len(C)
    return float(np.sqrt(w @ C.to_numpy() @ w) / np.sqrt(w @ C_recent.to_numpy() @ w))


if __name__ == "__main__":
    R = classes()
    avail = {c: str(R[c].dropna().index[0].date()) for c in CLASSES}
    print("first month per class:", avail)
    S = trend_streams(R)
    out = {"first_month": avail, "windows": {}}
    Cr_a, Cr_t = corr(R, *RECENT), corr(S, *RECENT)
    for name, (a, b) in {**WINDOWS, "2023-2025 the baseline's three years": RECENT}.items():
        Ca, Ct = corr(R, a, b), corr(S, a, b)
        out["windows"][name] = dict(months=int(len(R.loc[a:b].dropna())), stock_bond_assets=float(Ca.loc["Equity", "Government bonds"]),
                                    stock_bond_trend=float(Ct.loc["Equity", "Government bonds"]), avg_abs_assets=avg_abs(Ca), avg_abs_trend=avg_abs(Ct),
                                    stress_ratio_trend=stressed_ratio(Cr_t, Ct), stress_ratio_assets=stressed_ratio(Cr_a, Ca),
                                    corr_assets=Ca.round(3).to_dict(), corr_trend=Ct.round(3).to_dict())
    # idea 2 for classes: each class's average |rho| with the others, recent three years against the worst window
    out["class_overlap"] = {}
    for c in CLASSES:
        rec = float(np.mean([abs(Cr_t.loc[c, o]) for o in CLASSES if o != c]))
        worst = max(float(np.mean([abs(corr(S, *WINDOWS[w]).loc[c, o]) for o in CLASSES if o != c])) for w in WORST)
        out["class_overlap"][c] = dict(recent=rec, worst=worst)
    (RES / "regimes.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"\n{'window':40s} {'n':>4s} {'stock-bond':>11s} {'(trend)':>8s} {'avg|rho|':>9s} {'(trend)':>8s} {'10% becomes':>12s}")
    for k, v in out["windows"].items():
        print(f"{k:40s} {v['months']:4d} {v['stock_bond_assets']:+11.2f} {v['stock_bond_trend']:+8.2f} {v['avg_abs_assets']:9.2f} {v['avg_abs_trend']:8.2f} {10 * v['stress_ratio_trend']:11.1f}%")
    print("\nclass overlap with the others (trend streams, mean |rho|): recent three years -> worst window")
    for c, v in out["class_overlap"].items(): print(f"  {c:18s} {v['recent']:.2f} -> {v['worst']:.2f}")


# --- idea 3, all pairs: total scaled to 10% on window A, volatility it would carry under window B (trend streams) ---------------------
def pairs():
    R = classes(); S = trend_streams(R); names = list(WINDOWS)
    C = {n: corr(S, *WINDOWS[n]) for n in names}
    M = pd.DataFrame({b: {a: 10 * stressed_ratio(C[a], C[b]) for a in names} for b in names})
    return M


# --- idea 2b: thematic ETFs through a long-history parent (French 49 industries) ------------------------------------------------------
FRENCH = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/49_Industry_Portfolios_CSV.zip"
THEMES = ["SMH", "SOXX", "IBB", "XBI", "ARKG", "ICLN", "TAN", "FAN", "LIT", "URA", "NLR", "GDX", "XME", "OIH", "ITB", "ITA", "PAVE", "PHO", "WOOD",
          "KWEB", "HACK", "CIBR", "SKYY", "CLOU", "FINX", "ARKK", "BOTZ", "ROBO", "AIQ", "IRBO", "DRIV", "BLOK", "ESPO", "UFO", "MJ"]


def french49():
    cache = RAW / "french_49_industries_monthly.csv"
    if not cache.exists():
        with urllib.request.urlopen(FRENCH, timeout=60) as r:
            z = zipfile.ZipFile(io.BytesIO(r.read()))
        txt = z.read(z.namelist()[0]).decode("latin-1").splitlines()
        start = next(i for i, l in enumerate(txt) if "Average Value Weighted Returns -- Monthly" in l) + 1
        rows = []
        for l in txt[start:]:
            if not l.strip(): break
            rows.append(l)
        df = pd.read_csv(io.StringIO("\n".join(rows)), index_col=0)
        df.index = pd.to_datetime(df.index.astype(str).str.strip(), format="%Y%m") + pd.offsets.MonthEnd(0)
        df.columns = [c.strip() for c in df.columns]
        df = df.apply(pd.to_numeric, errors="coerce").where(lambda x: x > -99) / 100
        df.to_csv(cache)
    return pd.read_csv(cache, index_col=0, parse_dates=True)


def themes():
    px = pd.read_csv(RAW / "portfolio" / "etf_daily.csv", header=[0, 1], index_col=0, parse_dates=True)["Close"]
    m = px.resample("ME").last().pct_change()
    F = french49(); spx = classes()["Equity"]
    out = {}
    for t in THEMES:
        if t not in m: continue
        r = m[t].dropna()
        if len(r) < 36: continue
        J = F.loc[r.index[0]:r.index[-1]].reindex(r.index)
        parent = J.corrwith(r).idxmax()                                         # rule fixed in advance: the most correlated industry
        own = float(abs(r.loc[RECENT[0]:RECENT[1]].corr(spx.reindex(r.index).loc[RECENT[0]:RECENT[1]])))
        P = F[parent]
        worst = max(float(abs(P.loc[a:b].corr(spx.loc[a:b]))) for a, b in (WINDOWS[w] for w in WORST))
        out[t] = dict(parent=parent, years=round(len(r) / 12, 1), own_recent=own, parent_worst=worst, track=float(r.corr(J[parent])))
    return out


if __name__ == "__main__":
    M = pairs()
    print("\n10% target set on window (rows), volatility under window (columns), trend streams:")
    print(M.round(1).to_string())
    T = themes()
    print(f"\nthemes: {len(T)}; parent tracks theme (median corr) {np.median([v['track'] for v in T.values()]):.2f}")
    print(f"|rho| with US equity: own last three years median {np.median([v['own_recent'] for v in T.values()]):.2f}; "
          f"parent in worst windows median {np.median([v['parent_worst'] for v in T.values()]):.2f}")
    print("above 0.8 with US equity: own recent", sum(v['own_recent'] > 0.8 for v in T.values()), "| parent worst", sum(v['parent_worst'] > 0.8 for v in T.values()))
    for t, v in sorted(T.items(), key=lambda kv: -kv[1]["parent_worst"])[:40]:
        print(f"  {t:5s} {v['years']:5.1f}y parent {v['parent']:6s} track {v['track']:.2f}  own {v['own_recent']:.2f}  parent-worst {v['parent_worst']:.2f}")
    j = json.loads((RES / "regimes.json").read_text(encoding="utf-8")); j["stress_pairs"] = M.round(2).to_dict(); j["themes"] = T
    (RES / "regimes.json").write_text(json.dumps(j, indent=1), encoding="utf-8")
