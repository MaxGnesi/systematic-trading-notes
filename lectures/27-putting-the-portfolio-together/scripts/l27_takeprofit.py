"""Lecture 27, take-profit per speed (results/hypotheses.md, fixed 2026-11-14 before any result). For each held stream: the open gain since
its signal last changed (sum of sign x daily return) in units of that speed's risk (six-month daily volatility at entry x sqrt(speed));
above k units the stream is flat until its signal changes. Positions as Lecture 26 (10% / volatility, a tenth of the way each day, 5 bp).
k = 2, 3, 4, 5 and none. ETFs out of sample 2013-2026 with the rule's structure; capstone futures 2003-2022 (end-2025 held set).
Output: results/takeprofit.json."""
import json, sys, warnings; warnings.filterwarnings("ignore")
from pathlib import Path
import numpy as np, pandas as pd
from numba import njit
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l27 as M, l27_futures_test as FT, l27_crisis as CR
L26 = M.L26; KS = (None, 2.0, 3.0, 4.0, 5.0, "2r", "3r", "4r", "5r")                     # "3r": k = 3 with re-entry after a one-unit pullback


@njit(cache=True)
def run(sig, r, vol, h, k, reenter, lam, vt, cost):
    """k <= 0: no take-profit. reenter: after a take-profit, back in after a pullback of one unit from the best level since the exit."""
    n = len(sig); pos = 0.0; out = np.zeros(n); flat = False; gain = 0.0; unit = np.nan; prev = 0.0; best = 0.0
    for t in range(1, n):
        out[t] = pos * r[t]                                                           # position held over day t
        s = sig[t]
        if np.isnan(s) or np.isnan(vol[t]) or vol[t] <= 0:
            s = 0.0
        if s != prev:                                                                 # new signal: a new trade
            flat = False; gain = 0.0; unit = vol[t] / np.sqrt(252) * np.sqrt(h); prev = s
        else:
            gain += s * r[t]
            if flat:
                best = max(best, gain)
                if reenter and best - gain >= unit:                                   # pulled back one unit: a new trade
                    flat = False; gain = 0.0; unit = vol[t] / np.sqrt(252) * np.sqrt(h)
            elif k > 0 and unit > 0 and gain > k * unit:
                flat = True; best = gain
        target = 0.0 if (flat or s == 0.0 or np.isnan(vol[t]) or vol[t] <= 0) else s * vt / vol[t]
        new = pos + lam * (target - pos); out[t] -= cost * abs(new - pos); pos = new
    return out


def streams_tp(x, held):
    """Net daily returns of the held streams of one market (x: excess-return price) for each k."""
    r = x.pct_change().fillna(0).to_numpy(); vol = np.sqrt((x.pct_change() ** 2).ewm(span=L26.VOL_SPAN, min_periods=60).mean() * 252).to_numpy()
    c = x.to_frame("x"); out = {k: {} for k in KS}
    for h in sorted({int(s.split("_")[1]) for s in held}):
        S = L26.signals(c, c, c, h)
        for rule in L26.RULES:
            nm = f"{rule}_{h}"
            if nm not in held: continue
            sg = S[rule]["x"].to_numpy().astype(float)
            for k in KS:
                kk = -1.0 if k is None else float(str(k).rstrip("r")); out[k][nm] = run(sg, r, vol, float(h), kk, isinstance(k, str), L26.LAMBDA, L26.VOL_TARGET, L26.COST_BP / 1e4)
    return {k: pd.DataFrame(v, x.index) for k, v in out.items()}


def portfolio(B, uni_of, reviews):
    """B[k][market]: blended daily return; the rule's structure with the scales of k = None."""
    rows = []
    for y in reviews:
        hist, nxt = slice(f"{y - 2}-01-01", f"{y}-12-31"), slice(f"{y + 1}-01-01", f"{y + 1}-12-31"); uni = uni_of(y)
        base = pd.DataFrame({t: B[None][t] for k in uni for t in uni[k]}); a = 1 / base.loc[hist].std()
        sc = {k: (M.TARGET / np.sqrt(252)) / base[m].mul(a[m]).mean(axis=1).loc[hist].std() for k, m in uni.items()}
        U0 = pd.DataFrame({k: base[m].mul(a[m]).mean(axis=1) * sc[k] for k, m in uni.items()}).mean(axis=1); ct = (M.TARGET / np.sqrt(252)) / U0.loc[hist].std()
        row = {}
        for kk in KS:
            X = pd.DataFrame({t: B[kk][t] for k in uni for t in uni[k]})
            row[str(kk)] = pd.DataFrame({k: X[m].mul(a[m]).mean(axis=1) * sc[k] for k, m in uni.items()}).mean(axis=1) * ct
        rows.append(pd.DataFrame(row).loc[nxt])
    return pd.concat(rows).dropna()


def measures(D, EP):
    mo = D.index.to_period("M"); worst = D["None"].groupby(mo).sum().nsmallest(12).index
    dd = lambda x: float(((1 + x).cumprod() / (1 + x).cumprod().cummax() - 1).min())
    out = {}
    for c in D:
        m = D[c].groupby(mo).sum()
        out[c] = dict(sharpe=L26.sharpe(D[c]), drawdown=dd(D[c]), worst12=float(D[c][mo.isin(worst)].sum()), skew_monthly=float(m.skew()),
                      episodes={f"{a.date()} to {b.date()}": float(D[c].loc[a:b].sum()) for a, b in EP if a >= D.index[0] and b <= D.index[-1]})
    return out


if __name__ == "__main__":
    import yfinance as yf
    spx = yf.download("^GSPC", start="1999-06-01", end="2026-12-31", auto_adjust=True, progress=False)["Close"].squeeze(); EP = CR.episodes(spx.loc["2000":])
    close, high, low, dv, rf = L26.load_daily(); res = {}
    names = sorted({t for y in range(2012, 2026) for k, mk in M.UNI[str(y)]["sc_div"].items() for t in mk})
    heldy = {y: [k for k, v in M.SEL[str(y)]["weights"]["one_set"].items() if v >= 0.2] for y in range(2012, 2026)}
    allheld = sorted(set().union(*heldy.values())); per = {}
    for t in names:
        c = close[t].dropna(); x = L26.excess(c, high[t].reindex(c.index), low[t].reindex(c.index), rf)[0]
        per[t] = streams_tp(x, allheld)                                                # breakout on closes here too, for like-for-like grids
    def uni_of(y): return M.UNI[str(y)]["sc_div"]
    rowsD = []
    for y in range(2012, 2026):
        Bk = {k: {t: per[t][k][heldy[y]].mean(axis=1) for t in names} for k in KS}
        rowsD.append(portfolio(Bk, uni_of, [y]))
    D = pd.concat(rowsD); res["etf"] = measures(D, EP); print("ETFs 2013-2026:"); print(pd.DataFrame({c: {k: v for k, v in d.items() if k != "episodes"} for c, d in res["etf"].items()}).round(3).to_string())
    print(pd.DataFrame({c: d["episodes"] for c, d in res["etf"].items()}).round(3).to_string(), flush=True)
    # futures
    S = pd.read_pickle(FT.CACHE); px = {k: S[k]["ratio"] for k in S if k in FT.CLASS}
    tb = pd.to_numeric(pd.read_csv(FT.RAW / "fred_DTB3.csv", index_col=0, parse_dates=True).iloc[:, 0], errors="coerce")
    fx = yf.download(["VFITX", "VUSTX"], start="1998-01-01", end="2023-01-01", auto_adjust=True, progress=False)["Close"]
    for t in ("VFITX", "VUSTX"):
        r = fx[t].pct_change() - (tb.reindex(fx.index).ffill() / 100 / 252).shift(1); px[t] = 100 * (1 + r.fillna(0)).cumprod()
    held25 = heldy[2025]; BF = {k: {} for k in KS}
    for t, p in px.items():
        x = p.dropna(); x = x[x > 0]; T = streams_tp(x, held25)
        for k in KS: BF[k][t] = T[k].mean(axis=1)
    fu = {}
    for t, k in FT.CLASS.items(): fu.setdefault(k, []).append(t)
    uf = lambda y: {k: [t for t in m if BF[None][t].loc[f"{y - 2}":f"{y}"].notna().sum() > 500] for k, m in fu.items() if any(BF[None][t].loc[f"{y - 2}":f"{y}"].notna().sum() > 500 for t in m)}
    DF = portfolio(BF, uf, range(2002, 2022)); res["futures"] = measures(DF, EP)
    print("futures 2003-2022:"); print(pd.DataFrame({c: {k: v for k, v in d.items() if k != "episodes"} for c, d in res["futures"].items()}).round(3).to_string())
    print(pd.DataFrame({c: d["episodes"] for c, d in res["futures"].items()}).round(3).to_string())
    (M.RESULTS / "takeprofit.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
