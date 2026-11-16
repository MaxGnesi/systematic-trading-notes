"""Lecture 13, stress scenarios: today's portfolio (the end-2025 review: Lecture 11's markets, Lecture 12's held speeds, every scale from
2023-2025) replayed through the six S&P 500 falls of more than 15% since 2000, with and without the take-profit at k = 4. Markets without
data in an episode are left out and their class averages over the rest. Breakout on closes in both versions (as l27_takeprofit.py).
Per episode: return, worst drawdown inside it, each class's contribution. Output: results/stress.json."""
import json, sys, warnings; warnings.filterwarnings("ignore")
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l27 as M, l27_crisis as CR, l27_takeprofit as TP
L26 = M.L26

if __name__ == "__main__":
    EP = CR.episodes(CR.spx().loc["2000":]); close, high, low, dv, rf = L26.load_daily()
    uni = M.UNI["2025"]["sc_div"]; held = [k for k, v in M.SEL["2025"]["weights"]["one_set"].items() if v >= 0.2]
    B = {None: {}, 4.0: {}}
    for k in uni:
        for t in uni[k]:
            c = close[t].dropna(); x = L26.excess(c, high[t].reindex(c.index), low[t].reindex(c.index), rf)[0]; T = TP.streams_tp(x, held)
            for kk in B: B[kk][t] = T[kk][held].mean(axis=1)
    hist = slice("2023-01-01", "2025-12-31"); P0 = pd.DataFrame(B[None]); a = 1 / P0.loc[hist].std()
    sc = {k: (M.TARGET / np.sqrt(252)) / P0[m].mul(a[m]).mean(axis=1).loc[hist].std() for k, m in uni.items()}
    U0 = pd.DataFrame({k: P0[m].mul(a[m]).mean(axis=1) * sc[k] for k, m in uni.items()}).mean(axis=1); ct = (M.TARGET / np.sqrt(252)) / U0.loc[hist].std()
    res = {"markets": uni, "held": held, "episodes": []}
    for p, q in EP:
        rec = {"peak": str(p.date()), "trough": str(q.date()), "spx": float(CR.spx().loc[q] / CR.spx().loc[p] - 1)}
        for kk, nm in ((None, "plain"), (4.0, "take-profit 4")):
            P = pd.DataFrame(B[kk]).loc[p:q]; avail = [t for t in P if P[t].notna().mean() > 0.9]
            parts = {k: P[[t for t in m if t in avail]].mul(a).mean(axis=1) * sc[k] / len(uni) * ct for k, m in uni.items() if any(t in avail for t in m)}
            tot = pd.DataFrame(parts).sum(axis=1); v = (1 + tot).cumprod()
            rec[nm] = dict(ret=float(tot.sum()), drawdown=float((v / v.cummax() - 1).min()), worst_day=float(tot.min()),
                           by_class={k: float(x.sum()) for k, x in parts.items()}, markets=len(avail), of=sum(len(m) for m in uni.values()))
        res["episodes"].append(rec)
    (M.RESULTS / "stress.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    for e in res["episodes"]:
        print(f"{e['peak']} to {e['trough']} (S&P {e['spx']:.0%}):", " | ".join(f"{nm}: {e[nm]['ret']:+.1%}, drawdown {e[nm]['drawdown']:.1%}, worst day {e[nm]['worst_day']:.1%}, {e[nm]['markets']}/{e[nm]['of']} markets, "
                                                                            + ", ".join(f"{k} {v:+.1%}" for k, v in e[nm]["by_class"].items()) for nm in ("plain", "take-profit 4")))
