"""Lecture 25, what "the same market" means (after the first run, 2026-11-13): for every pair since 2007, the correlation of weekly returns, the
concordance of 26-week trend phases (sign ignored), its value for independent markets, and the drift a beta hedge leaves (Lecture 3, section 8.4).
Also the effective number of bets with risk spread equally per class, as classes are added. Output: results/pairs.parquet, results/class_bets.json."""
import json, sys, warnings; warnings.filterwarnings("ignore")
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l25 as L

if __name__ == "__main__":
    close, dv, R, PH, POS = L.load(); R, PH = R["2007":], PH["2007":]; names = list(R.columns); rows = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            ok = R[a].notna() & R[b].notna() & PH[a].notna() & PH[b].notna()
            if ok.sum() < L.WIN: continue
            x, y = R.loc[ok, a], R.loc[ok, b]; rho = x.corr(y); pa, pb = (PH.loc[ok, a] > 0).mean(), (PH.loc[ok, b] > 0).mean()
            c = (PH.loc[ok, a] == PH.loc[ok, b]).mean(); ind = pa * pb + (1 - pa) * (1 - pb)
            if rho < 0: c, ind = 1 - c, 1 - ind                                           # mirror images: the same bet for a long/short trader
            beta = np.cov(x, y)[0, 1] / y.var(); res = x - beta * y
            rows.append(dict(a=a, b=b, ca=L.CLASS[a], cb=L.CLASS[b], rho=rho, conc=c, conc_indep=ind, hedge_drift=52 * res.mean(), years=ok.sum() / 52))
    P = pd.DataFrame(rows); P.to_parquet(L.RESULTS / "pairs.parquet")
    for lo, hi in ((0.9, 1.01), (0.8, 0.9), (0.7, 0.8), (0.5, 0.7), (0, 0.5)):
        g = P[(P.rho.abs() >= lo) & (P.rho.abs() < hi)]
        print(f"|rho| {lo}-{hi}: {len(g)} pairs, concordance median {g.conc.median():.2f}, min {g.conc.min():.2f}, below 0.80 {(g.conc < 0.8).mean():.0%}")

    F = R.loc[:, R.notna().sum() >= L.WIN]; C = L.corr(F, L.MINW); allv = list(C.index); out = {"n": len(allv), "per_etf": L.enb(C), "per_class": L.enb(C, allv, "class")}
    order = list(L.CLASSES[:1]) + ["Rates", "Commodities", "FX", "Credit"]; out["adding"] = []
    for i in range(1, 6):
        nm = [n for n in allv if L.CLASS[n] in order[:i]]; out["adding"].append(dict(classes=order[:i], enb=L.enb(C, nm, "class")))
    out["within"] = {k: L.enb(C, [n for n in allv if L.CLASS[n] == k]) for k in L.CLASSES}
    out["one_each"] = L.enb(C, ["SPY", "IEF", "HYG", "DBC", "UUP"])
    (L.RESULTS / "class_bets.json").write_text(json.dumps(out, indent=1), encoding="utf-8"); print(json.dumps(out, indent=1))
