"""Lecture 27, timing the speeds inside the plateau (the user, 2026-11-14): momentum (tilt towards the speeds that did best over the past
quarter, relative to the plateau) and reversal (towards the worst), against equal weights. Each market's weights at the start of each quarter:
w_i = (1 + k * c_i) / n, with c_i the stream's rank over the past window centred to [-1, 1] (momentum: +rank, reversal: -rank) and k = 0.5 or 1,
so weights stay within [0, 2/n]. Reweighting costs 5 bp of the change in each stream's position. Markets, classes and total as the rule, with
the scales of the equal blend (so only the tilt differs). Out of sample 2013-2026. Usage: python l27_timing.py. Output: results/timing.json."""
import json, sys, warnings; warnings.filterwarnings("ignore")
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l27 as M
L26 = M.L26; KS = (0.5, 1.0); WINDOWS = (3, 6)

if __name__ == "__main__":
    close, high, low, dv, rf = L26.load_daily()
    names = sorted({t for y in range(2012, 2026) for k, mk in M.UNI[str(y)]["sc_div"].items() for t in mk})
    NET, POS = {}, {}
    for t in names:
        c = close[t].dropna(); x = L26.excess(c, high[t].reindex(c.index), low[t].reindex(c.index), rf)
        NET[t] = L26.net(pd.read_parquet(L26.OUT / "streams" / f"{t}.parquet")); POS[t] = M.positions(*x)
    variants = ["equal"] + [f"{d}_{w}m_k{k}" for d in ("momentum", "reversal") for w in WINDOWS for k in KS]
    days = []
    for y in range(2012, 2026):
        held = [k for k, v in M.SEL[str(y)]["weights"]["one_set"].items() if v >= 0.2]; n = len(held)
        uni = M.UNI[str(y)]["sc_div"]; mk = [t for k in uni for t in uni[k]]
        hist, nxt = slice(f"{y - 2}-01-01", f"{y}-12-31"), slice(f"{y + 1}-01-01", f"{y + 1}-12-31")
        blends = {v: {} for v in variants}
        for t in mk:
            Nt, Pt = NET[t][held], POS[t][held]; idx = Nt.loc[nxt].index
            if len(idx) == 0: continue
            q = idx.to_period("Q"); blends["equal"][t] = Nt.mean(axis=1)
            for d in ("momentum", "reversal"):
                for w in WINDOWS:
                    for k in KS:
                        out = pd.Series(0.0, idx); wprev = None
                        for qq in q.unique():
                            dq = idx[q == qq]; start = dq[0]
                            past = Nt.loc[:start - pd.Timedelta(days=1)].iloc[-21 * w:]
                            sh = past.mean() / past.std(); r = sh.rank(); cen = (2 * (r - 1) / (n - 1) - 1).fillna(0)
                            wq = (1 + k * (cen if d == "momentum" else -cen)) / n
                            ret = (Nt.loc[dq] * wq).sum(axis=1)
                            if wprev is not None: ret.iloc[0] -= L26.COST_BP / 1e4 * float((Pt.loc[start] * (wq - wprev)).abs().sum())
                            out.loc[dq] = ret; wprev = wq
                        blends[f"{d}_{w}m_k{k}"][t] = out
        Req = pd.DataFrame({t: NET[t][held].mean(axis=1) for t in mk}); a = 1 / Req.loc[hist].std(); row = {}
        cls_scale = {k2: (M.TARGET / np.sqrt(252)) / Req[m].mul(a[m]).mean(axis=1).loc[hist].std() for k2, m in uni.items()}
        Ueq = pd.DataFrame({k2: Req[m].mul(a[m]).mean(axis=1) * cls_scale[k2] for k2, m in uni.items()}).mean(axis=1); ctot = (M.TARGET / np.sqrt(252)) / Ueq.loc[hist].std()
        for v in variants:
            B = pd.DataFrame(blends[v]).reindex(columns=mk)
            row[v] = pd.DataFrame({k2: B[m].mul(a[m]).mean(axis=1) * cls_scale[k2] for k2, m in uni.items()}).mean(axis=1) * ctot
        days.append(pd.DataFrame(row).loc[nxt]); print(y, "done", flush=True)
    D = pd.concat(days); D.to_parquet(M.OUT / "l27_timing_daily.parquet")
    mo = D.index.to_period("M"); um = mo.unique(); idx = {u: np.where(mo == u)[0] for u in um}; rng = np.random.default_rng(20261113); res = {}
    for v in variants:
        b = []
        if v != "equal":
            for _ in range(2000):
                ii = np.concatenate([idx[um[i]] for i in rng.choice(len(um), len(um))]); b.append(L26.sharpe(D[v].iloc[ii]) - L26.sharpe(D.equal.iloc[ii]))
        res[v] = dict(sharpe=L26.sharpe(D[v]), diff=(L26.sharpe(D[v]) - L26.sharpe(D.equal)) if v != "equal" else 0.0,
                      ci90=[float(np.quantile(b, .05)), float(np.quantile(b, .95))] if b else None)
    (M.RESULTS / "timing.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(pd.DataFrame(res).T.to_string())
