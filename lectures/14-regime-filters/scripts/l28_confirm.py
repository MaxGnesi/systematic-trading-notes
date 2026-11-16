"""Lecture 14: the two quadrant expectations (E1 correlation below average and rising is the best correlation quadrant; E2 with volatility above
average, falling beats rising) checked on 1990-2005, untouched years, as fixed in results/hypotheses.md before this data was loaded.
A small trend portfolio from free long series, with the baseline's rules; quadrants of VXO (FRED, the original VIX) and of the average absolute
pairwise correlation of the portfolio's markets, level against its own average to date (at least three years), direction over 63 days.
Output: results/confirm.json."""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l28 as L
L26, M27 = L.L26, L.M27
HELD = [k for k, v in M27.SEL["2025"]["weights"]["one_set"].items() if v >= 0.2]
EQUITY = ("^GSPC", "^N225", "^FTSE", "^GDAXI"); FX = {"DEXJPUS": -1, "DEXUSUK": 1, "DEXSZUS": -1, "DEXCAUS": -1}   # sign: holding the foreign currency
CLASS = {**{t: "Equity" for t in EQUITY}, "UST10": "Rates", "UST2": "Rates", **{k: "FX" for k in FX}, "OIL": "Commodities", "GAS": "Commodities"}
START, END = "1990-01-01", "2005-12-31"


def yahoo():
    f = L.RT / "l28_long_equity.csv"
    if not f.exists():
        import yfinance as yf
        yf.download(list(EQUITY), start="1980-01-01", end="2006-01-01", auto_adjust=True, progress=False)["Close"].to_csv(f)
    return pd.read_csv(f, index_col=0, parse_dates=True)


def returns():
    """Daily returns over cash where the series allow (rates: carry minus duration x change in yield); spot or price returns otherwise."""
    rf = L.fred("DTB3") / 100 / 252; R = {}
    eq = yahoo()
    for t in EQUITY: R[t] = eq[t].dropna().pct_change()
    for code, dur, name in (("DGS10", 7.0, "UST10"), ("DGS2", 1.9, "UST2")):
        y = L.fred(code) / 100; R[name] = (y.shift(1) / 252 - rf.reindex(y.index).ffill().shift(1)) - dur * y.diff()
    for code, sgn in FX.items():
        x = L.fred(code); R[code] = (x / x.shift(1)) ** sgn - 1
    R["OIL"] = L.fred("DCOILWTICO").where(lambda s: s > 0).pct_change(); R["GAS"] = L.fred("DHHNGSP").where(lambda s: s > 0).pct_change()
    return pd.DataFrame(R).loc["1983-01-01":END]


def portfolio(R):
    N = {}
    for t in R:
        r = R[t].dropna(); r = r[np.isfinite(r) & (r.abs() < 0.5)]; x = 100 * (1 + r).cumprod()
        N[t] = L26.net(L26.stream_returns(x, x, x))[HELD].mean(axis=1)
    N = pd.DataFrame(N); days = []
    for y in range(1989, 2005):
        hist, nxt = slice(f"{y - 2}-01-01", f"{y}-12-31"), slice(f"{y + 1}-01-01", f"{y + 1}-12-31"); a = 1 / N.loc[hist].std(); pe = {}
        for k in sorted(set(CLASS.values())):
            m = [t for t in N if CLASS[t] == k and N[t].loc[hist].notna().sum() > 500]
            if m: be = N[m].mul(a[m]).mean(axis=1); pe[k] = be * (M27.TARGET / np.sqrt(252)) / be.loc[hist].std()
        U = pd.DataFrame(pe).mean(axis=1); days.append((U * (M27.TARGET / np.sqrt(252)) / U.loc[hist].std()).loc[nxt])
    return pd.concat(days).dropna()


def quadrants(level, change, idx):
    l = level.shift(1); above = (l > l.expanding(750).mean()).where(l.expanding(750).mean().notna()); up = change.shift(1) > 0
    q = pd.Series(np.where(above.astype(float) == 1, "above", "below"), l.index).where(above.notna()) + pd.Series(np.where(up, " rising", " falling"), l.index)
    return q.reindex(idx)


def band(r, a, b, n=2000, seed=20261115):
    mo = r.index.to_period("M"); um = mo.unique(); idx = {u: np.where(mo == u)[0] for u in um}; rng = np.random.default_rng(seed); out = []
    for _ in range(n):
        ii = np.concatenate([idx[um[i]] for i in rng.choice(len(um), len(um))]); rr, aa, bb = r.iloc[ii], a.iloc[ii], b.iloc[ii]
        out.append(L26.sharpe(rr[aa]) - L26.sharpe(rr[bb]))
    return [float(np.quantile(out, .05)), float(np.quantile(out, .95))]


if __name__ == "__main__":
    R = returns(); base = portfolio(R).loc[START:END]
    print(f"1990-2005 trend portfolio: {R.shape[1]} markets, Sharpe {L26.sharpe(base):.2f}, volatility {base.std() * np.sqrt(252):.1%}", flush=True)
    v = L.fred("VXOCLS"); vq = quadrants(v.rolling(21).mean(), np.log(v) - np.log(v.shift(63)), base.index)
    X = R.loc["1985-01-01":END]; vals = X.to_numpy(); cr = pd.Series(np.nan, X.index)
    for i in range(125, len(X)):
        w = vals[i - 125: i + 1]; ok = np.isnan(w).mean(axis=0) <= 0.1
        if ok.sum() >= 5: c = pd.DataFrame(w[:, ok]).corr(min_periods=100).to_numpy(); cr.iloc[i] = np.nanmean(np.abs(c[np.triu_indices(ok.sum(), 1)]))
    cq = quadrants(cr, cr.diff(63), base.index)
    out = {"sharpe": L26.sharpe(base), "markets": list(R.columns)}
    for k, q in (("volatility", vq), ("correlation", cq)):
        out[k] = {s: dict(sharpe=L26.sharpe(base[q == s]), share=float((q == s).mean())) for s in ("below falling", "below rising", "above falling", "above rising")}
        print(k, {s: (round(x["sharpe"], 2), f"{x['share']:.0%}") for s, x in out[k].items()})
    c = out["correlation"]; best = max(c, key=lambda s: c[s]["sharpe"])
    out["E1"] = dict(best_quadrant=best, holds=best == "below rising",
                     diff_vs_rest=L26.sharpe(base[cq == "below rising"]) - L26.sharpe(base[(cq != "below rising") & cq.notna()]),
                     ci90=band(base, cq == "below rising", (cq != "below rising") & cq.notna()))
    out["E2"] = dict(above_falling=out["volatility"]["above falling"]["sharpe"], above_rising=out["volatility"]["above rising"]["sharpe"],
                     holds=out["volatility"]["above falling"]["sharpe"] > out["volatility"]["above rising"]["sharpe"],
                     ci90=band(base, vq == "above falling", vq == "above rising"))
    print("E1:", out["E1"]); print("E2:", out["E2"])
    (L.RESULTS / "confirm.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
