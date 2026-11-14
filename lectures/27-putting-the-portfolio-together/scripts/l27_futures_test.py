"""Lecture 27, the independent test fixed in results/hypotheses.md before any futures result: the volatility-state tilt inside Lecture 26's
end-2025 held set (20 streams, 43-359 days; no new selection), on the capstone markets (Lecture 11: 12 futures with observed rolls, ratio
back-adjusted, 2000-2022, plus the Treasury funds VFITX and VUSTX over the bill rate). Fast = 43-89 days, slow = 179-359. Each day a market's
six-month volatility over its three-year median above 1.33 tilts towards fast, below 0.75 towards slow, otherwise equal: weights (1 + c_i)/n,
c_i the stream's speed rank centred to [-1, 1] (fast +1 in a storm, slow +1 in calm), reached a tenth of the way each day; 5 bp on every
change. Against equal weights in the same set. Markets equal risk in a class, classes equal risk, total to 10%, each scaled at every year end
on the past three years. Deviation: the cache holds closes only, so the breakout uses closes for high and low.
Output: results/futures_test.json."""
import json, sys, warnings; warnings.filterwarnings("ignore")
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l27 as M
L26 = M.L26
CACHE = Path(M.L25.DATA).parents[1] / "interim" / "l11_series99.pkl"; RAW = Path(M.L25.DATA).parent
CLASS = {"cme-es": "eq", "cme-nasdaq": "eq", "cme-euro": "fx", "cme-jpy": "fx", "ice-us-dollar-index": "fx", "nymex-cl": "en", "nymex-ng": "en",
         "comex-gc": "mt", "cbot-corn": "ag", "cbot-soybeans": "ag", "cbot-wheat": "ag", "ice-cocoa": "ag", "VFITX": "bd", "VUSTX": "bd"}
HELD = [k for k, v in M.SEL["2025"]["weights"]["one_set"].items() if v >= 0.2]
SPEED = pd.Series({k: int(k.split("_")[1]) for k in HELD})

if __name__ == "__main__":
    S = pd.read_pickle(CACHE); px = {k: S[k]["ratio"] for k in S if k in CLASS}
    tb = pd.to_numeric(pd.read_csv(RAW / "fred_DTB3.csv", index_col=0, parse_dates=True).iloc[:, 0], errors="coerce")
    import yfinance as yf
    fx = yf.download(["VFITX", "VUSTX"], start="1998-01-01", end="2023-01-01", auto_adjust=True, progress=False)["Close"]
    for t in ("VFITX", "VUSTX"):
        r = fx[t].pct_change() - (tb.reindex(fx.index).ffill() / 100 / 252).shift(1); px[t] = 100 * (1 + r.fillna(0)).cumprod()
    c = SPEED.rank(method="dense"); c = 2 * (c - c.min()) / (c.max() - c.min()) - 1          # -1 fastest ... +1 slowest held speed
    tilt_fast, tilt_slow = (1 - c) / len(HELD), (1 + c) / len(HELD)                            # storm: towards fast; calm: towards slow
    eq = pd.Series(1 / len(HELD), HELD)
    R = {"equal": {}, "tilt": {}}
    for t, p in px.items():
        x = p.dropna(); x = x[x > 0]; Sx = L26.stream_returns(x, x, x); N = L26.net(Sx)[HELD]
        P = M.positions(x, x, x)[HELD]; r = x.pct_change()
        vol = np.sqrt((r ** 2).ewm(span=126, min_periods=60).mean()); rel = (vol / vol.rolling(756, min_periods=252).median()).shift(1)
        target = np.where((rel > 1.33).to_numpy()[:, None], tilt_fast.to_numpy(), np.where((rel < 0.75).to_numpy()[:, None], tilt_slow.to_numpy(), eq.to_numpy()))
        w = np.zeros_like(target); w[0] = target[0]
        for i in range(1, len(w)): w[i] = w[i - 1] + 0.1 * (target[i] - w[i - 1])
        W = pd.DataFrame(w, N.index, HELD); cost = L26.COST_BP / 1e4 * (P * W.diff().abs()).abs().sum(axis=1)
        R["equal"][t] = N.mean(axis=1); R["tilt"][t] = (N * W.shift(1).fillna(eq)).sum(axis=1) - cost
        R.setdefault("state", {})[t] = pd.Series(np.where(rel > 1.33, "storm", np.where(rel < 0.75, "calm", "normal")), rel.index).where(rel.notna())
    days = []; Req = pd.DataFrame(R["equal"]); Rtl = pd.DataFrame(R["tilt"])
    for y in range(2002, 2022):
        hist, nxt = slice(f"{y - 2}-01-01", f"{y}-12-31"), slice(f"{y + 1}-01-01", f"{y + 1}-12-31")
        a = 1 / Req.loc[hist].std(); pe, pt = {}, {}
        for k in sorted(set(CLASS.values())):
            m = [t for t in Req if CLASS[t] == k and Req[t].loc[hist].notna().sum() > 500]
            if not m: continue
            be = Req[m].mul(a[m]).mean(axis=1); sc = (M.TARGET / np.sqrt(252)) / be.loc[hist].std()      # the equal blend's scales, used for both
            pe[k], pt[k] = be * sc, Rtl[m].mul(a[m]).mean(axis=1) * sc
        Ue, Ut = pd.DataFrame(pe).mean(axis=1), pd.DataFrame(pt).mean(axis=1); ct = (M.TARGET / np.sqrt(252)) / Ue.loc[hist].std()
        days.append(pd.DataFrame({"equal": Ue * ct, "tilt": Ut * ct}).loc[nxt])
    D = pd.concat(days).dropna()
    mo = D.index.to_period("M"); um = mo.unique(); idx = {u: np.where(mo == u)[0] for u in um}; rng = np.random.default_rng(20261114); b = []
    for _ in range(2000):
        ii = np.concatenate([idx[um[i]] for i in rng.choice(len(um), len(um))]); b.append(L26.sharpe(D.tilt.iloc[ii]) - L26.sharpe(D.equal.iloc[ii]))
    dd = lambda x: float(((1 + x).cumprod() / (1 + x).cumprod().cummax() - 1).min())
    worst = D.equal.groupby(mo).sum().nsmallest(12).index
    st = pd.DataFrame(R["state"]).loc["2003":"2022"]
    out = dict(held=HELD, years="2003-2022", markets=list(px), sharpe={v: L26.sharpe(D[v]) for v in ("equal", "tilt")},
               vol={v: float(D[v].std() * np.sqrt(252)) for v in ("equal", "tilt")}, drawdown={v: dd(D[v]) for v in ("equal", "tilt")},
               worst12={v: float(D[v][mo.isin(worst)].sum()) for v in ("equal", "tilt")},
               diff=L26.sharpe(D.tilt) - L26.sharpe(D.equal), ci90=[float(np.quantile(b, .05)), float(np.quantile(b, .95))],
               state_share={s: float((st == s).sum().sum() / st.notna().sum().sum()) for s in ("calm", "normal", "storm")})
    (M.RESULTS / "futures_test.json").write_text(json.dumps(out, indent=1), encoding="utf-8"); print(json.dumps({k: v for k, v in out.items() if k != "held"}, indent=1))
