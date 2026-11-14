"""Lecture 27, crisis speeds (results/hypotheses.md, fixed 2026-11-14 before any result). Episodes: falls of the S&P 500 of more than 15%,
peak to trough, 2000-2026. Per episode, each of the 36 streams' return (all speeds), averaged over markets with each class the same weight,
on the ETFs (Lecture 26's streams) and on the capstone futures (Lecture 11, observed rolls; breakout on closes); per speed the average over
the rules, against Lecture 26's held set at equal weights. A speed works in crises if it beats the held set in >= 2/3 of the episodes on
both datasets. If any does, a sleeve of those speeds at 0-30% of each market's weight, evaluated out of sample (ETFs 2013-2026 with the
rule's structure; futures 2003-2022). Output: results/crisis.json."""
import json, sys, warnings; warnings.filterwarnings("ignore")
from pathlib import Path
import numpy as np, pandas as pd, yfinance as yf
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l27 as M, l27_futures_test as FT
L26 = M.L26; SLEEVES = (0.0, 0.1, 0.2, 0.3)


def episodes(p, fall=0.15):
    out, peak, pt, low, lt, inep = [], p.iloc[0], p.index[0], None, None, False
    for t, v in p.items():
        if not inep:
            if v > peak: peak, pt = v, t
            elif v <= (1 - fall) * peak: inep, low, lt = True, v, t
        else:
            if v < low: low, lt = v, t
            if v >= peak: out.append((pt, lt)); inep, peak, pt = False, v, t
    if inep: out.append((pt, lt))
    return out


def class_mean(df, cls):
    """Average over markets with each class the same total weight (df: markets x streams)."""
    g = pd.Series(cls).reindex(df.index); return df.groupby(g).mean().mean()


def futures_streams():
    S = pd.read_pickle(FT.CACHE); px = {k: S[k]["ratio"] for k in S if k in FT.CLASS}
    tb = pd.to_numeric(pd.read_csv(FT.RAW / "fred_DTB3.csv", index_col=0, parse_dates=True).iloc[:, 0], errors="coerce")
    fx = yf.download(["VFITX", "VUSTX"], start="1998-01-01", end="2023-01-01", auto_adjust=True, progress=False)["Close"]
    for t in ("VFITX", "VUSTX"):
        r = fx[t].pct_change() - (tb.reindex(fx.index).ffill() / 100 / 252).shift(1); px[t] = 100 * (1 + r.fillna(0)).cumprod()
    out = {}
    for t, p in px.items():
        x = p.dropna(); x = x[x > 0]; out[t] = L26.net(L26.stream_returns(x, x, x))
    return out


def evaluate(NET, cls, held, sleeve, reviews, uni_of):
    """Daily total for each sleeve share: markets equal risk in a class, classes equal risk, total 10%, scales from the plain held set."""
    rows = []
    for y in reviews:
        hist, nxt = slice(f"{y - 2}-01-01", f"{y}-12-31"), slice(f"{y + 1}-01-01", f"{y + 1}-12-31"); uni = uni_of(y); h = held(y)
        base = pd.DataFrame({t: NET[t][h].mean(axis=1) for k in uni for t in uni[k]}); a = 1 / base.loc[hist].std(); row = {}
        sc = {k: (M.TARGET / np.sqrt(252)) / base[m].mul(a[m]).mean(axis=1).loc[hist].std() for k, m in uni.items()}
        U0 = pd.DataFrame({k: base[m].mul(a[m]).mean(axis=1) * sc[k] for k, m in uni.items()}).mean(axis=1); ct = (M.TARGET / np.sqrt(252)) / U0.loc[hist].std()
        for s in SLEEVES:
            B = pd.DataFrame({t: (1 - s) * NET[t][h].mean(axis=1) + (s * NET[t][sleeve].mean(axis=1) if sleeve else 0) for k in uni for t in uni[k]})
            row[s] = pd.DataFrame({k: B[m].mul(a[m]).mean(axis=1) * sc[k] for k, m in uni.items()}).mean(axis=1) * ct
        rows.append(pd.DataFrame(row).loc[nxt])
    D = pd.concat(rows).dropna(); mo = D.index.to_period("M"); worst = D[0.0].groupby(mo).sum().nsmallest(12).index
    dd = lambda x: float(((1 + x).cumprod() / (1 + x).cumprod().cummax() - 1).min())
    return {str(s): dict(sharpe=L26.sharpe(D[s]), drawdown=dd(D[s]), worst12=float(D[s][mo.isin(worst)].sum()), vol=float(D[s].std() * np.sqrt(252))) for s in SLEEVES}


if __name__ == "__main__":
    spx = yf.download("^GSPC", start="1999-06-01", end="2026-12-31", auto_adjust=True, progress=False)["Close"].squeeze()
    EP = episodes(spx.loc["2000":]); print("episodes:", [(str(a.date()), str(b.date())) for a, b in EP], flush=True)
    close, high, low, dv, rf = L26.load_daily()
    ETF = {t: L26.net(pd.read_parquet(L26.OUT / "streams" / f"{t}.parquet")) for t in close.columns if (L26.OUT / "streams" / f"{t}.parquet").exists()}
    FUT = futures_streams()
    held25 = [k for k, v in M.SEL["2025"]["weights"]["one_set"].items() if v >= 0.2]
    res = {"episodes": [], "speeds": [str(h) for h in L26.SPEEDS]}
    for a, b in EP:
        rec = {"peak": str(a.date()), "trough": str(b.date()), "spx_fall": float(spx.loc[b] / spx.loc[a] - 1)}
        for nm, NET, cls in (("etf", ETF, L26.CLASS), ("futures", FUT, FT.CLASS)):
            X = pd.DataFrame({t: N.loc[a:b].sum() for t, N in NET.items() if N.loc[a:b].notna().sum().min() > 0.8 * len(N.loc[a:b]) and len(N.loc[a:b]) > 5}).T
            if len(X) < 5: continue
            m = class_mean(X, cls)
            held = held25 if nm == "futures" else [k for k, v in M.SEL[str(min(max(a.year - 1, 2012), 2025))]["weights"]["one_set"].items() if v >= 0.2]
            hv = float(class_mean(X[held].mean(axis=1).to_frame("h"), cls)["h"])
            rec[nm] = dict(markets=len(X), held=hv, by_speed={str(h): float(np.mean([m[f"{r}_{h}"] for r in L26.RULES])) for h in L26.SPEEDS})
        res["episodes"].append(rec)
    beat = {}
    for nm in ("etf", "futures"):
        E = [e[nm] for e in res["episodes"] if nm in e]
        beat[nm] = {str(h): float(np.mean([e["by_speed"][str(h)] > e["held"] for e in E])) for h in L26.SPEEDS}; beat[nm + "_n"] = len(E)
    res["beat_share"] = beat
    works = [h for h in L26.SPEEDS if beat["etf"][str(h)] >= 2 / 3 and beat["futures"][str(h)] >= 2 / 3]; res["works"] = works
    print(pd.DataFrame({e["peak"] + " to " + e["trough"] + f" ({e['spx_fall']:.0%})": {**{f"etf {h}": e.get("etf", {}).get("by_speed", {}).get(str(h)) for h in L26.SPEEDS}, "etf held": e.get("etf", {}).get("held")} for e in res["episodes"]}).round(3).to_string())
    print(pd.DataFrame({e["peak"]: {**{f"fut {h}": e.get("futures", {}).get("by_speed", {}).get(str(h)) for h in L26.SPEEDS}, "fut held": e.get("futures", {}).get("held")} for e in res["episodes"]}).round(3).to_string())
    print("share of episodes beating the held set:", {k: v for k, v in beat.items()}); print("works in crises on both:", works, flush=True)
    if works:
        sleeve = [f"{r}_{h}" for r in L26.RULES for h in works]
        res["eval_etf"] = evaluate(ETF, L26.CLASS, lambda y: [k for k, v in M.SEL[str(y)]["weights"]["one_set"].items() if v >= 0.2], sleeve, range(2012, 2026), lambda y: M.UNI[str(y)]["sc_div"])
        fut_uni = {}
        for t, k in FT.CLASS.items(): fut_uni.setdefault(k, []).append(t)
        res["eval_futures"] = evaluate(FUT, FT.CLASS, lambda y: held25, sleeve, range(2002, 2022), lambda y: {k: [t for t in m if FUT[t].loc[f"{y - 2}":f"{y}"].notna().sum().min() > 500] for k, m in fut_uni.items() if any(FUT[t].loc[f"{y - 2}":f"{y}"].notna().sum().min() > 500 for t in m)})
        sc = pd.concat([pd.read_parquet(L26.OUT / "streams" / f"{t}.parquet")[[f"t_{s}" for s in sleeve]].loc["2013":].mean() for t in ETF]).mean() * 252 * L26.COST_BP / 1e4
        res["sleeve_cost_a_year_per_unit_weight"] = float(sc)
        print("ETFs:", pd.DataFrame(res["eval_etf"]).round(3).to_string()); print("futures:", pd.DataFrame(res["eval_futures"]).round(3).to_string())
    (M.RESULTS / "crisis.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
