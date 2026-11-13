"""Lecture 25, class-first selection (designed after the first run, 2026-11-13; results/hypotheses.md, addenda). Slots per class = factors above the
Marchenko-Pastur edge in that class (at least 1; ceiling 30 in all); duplicates = |rho| >= 0.9 and trend-phase concordance >= 0.85; the floor; members
leave if redundant, below the floor or over the cap at two reviews in a row, or when their data end; at least 2 per class (added after results;
from below the floor if need be, flagged). Ways to fill the slots:
  dr  greedy diversification ratio on |rho|, from the most liquid market
  pc  one market per factor: for each factor in turn, the liquid market with the largest |loading|
  ev  explained variance, step by step
  hy  the key market (largest |loading| on factor 1, protected from the over-cap rule), then greedy diversification
  dr_nocap  greedy diversification with the 1% stop and no cap, members never leave (the run before the size rules)
  pos_nocap the same on |corr| of trend-positioned returns (phase x next week's return) instead of returns
Out of sample: variance of each class explained next year, mean |corr| next year (returns; trend-positioned returns), effective bets over 3 years with
equal risk per class; against random selections with the same count per class. Output: results/fill.json."""
import json, sys, warnings; warnings.filterwarnings("ignore")
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l25 as L
SCORE_W = {"sc": (1 / 3, 1 / 3, 1 / 3), "sc_rep": (0.5, 0.25, 0.25), "sc_div": (0.25, 0.5, 0.25), "sc_liq": (0.25, 0.25, 0.5)}   # representativeness, diversification, liquidity
METHODS = ("dr", "pc", "ev", "hy") + tuple(SCORE_W) + ("dr_nocap", "pos_nocap"); NOCAP = ("dr_nocap", "pos_nocap"); GREEDY = ("dr", "hy") + NOCAP; NR = 300
LIQ = {}                                                                             # liquidity at the current review, set in the loop


def composite(meth, C, base, opts, names):
    """Average of percentile ranks among opts (the user's equity scoring): representativeness, diversification, liquidity; weights SCORE_W[meth]."""
    wr, wd, wl = SCORE_W[meth]; df = pd.DataFrame(index=opts)
    df["rep"] = [L.explained(C, base + [x], names) for x in opts]; df["liq"] = [np.log(max(LIQ.get(x, 0), 1.0)) for x in opts]
    if base: df["div"] = [L.dr_abs(C, base + [x]) for x in opts]
    else: wr, wd, wl = wr / (wr + wl), 0.0, wl / (wr + wl); df["div"] = 0.0                    # first pick: no diversification yet
    pr = df.rank(pct=True); return (wr * pr.rep + wd * pr["div"] + wl * pr.liq).sort_values(ascending=False)


def loadings(C, names):
    v, E = np.linalg.eigh(C.loc[names, names].values); o = np.argsort(v)[::-1]; return pd.DataFrame(np.abs(E[:, o]), names)


def pick_next(meth, C, mem, opts, names):
    if meth in SCORE_W: return composite(meth, C, mem, opts, names).index[0]
    if meth == "hy": meth = "pc" if not mem else "dr"
    if meth in ("dr",) + NOCAP: return max(opts, key=lambda x: L.dr_abs(C, mem + [x]))
    if meth == "ev": return max(opts, key=lambda x: L.explained(C, mem + [x], names))
    E = loadings(C, names)                                                          # pc: the first factor whose top market is not a member yet
    for j in E.columns:
        if E[j].idxmax() not in mem: return max(opts, key=lambda n: E.loc[n, j])
    return opts[0]


def weakest(meth, C, mem, names):
    if meth in SCORE_W:                                                             # the member whose loss costs least: percentile ranks among members
        wr, wd, wl = SCORE_W[meth]; full_ev, full_dr = L.explained(C, mem, names), L.dr_abs(C, mem)
        df = pd.DataFrame({"rep": [full_ev - L.explained(C, [o for o in mem if o != m], names) for m in mem],
                           "div": [full_dr - L.dr_abs(C, [o for o in mem if o != m]) for m in mem],
                           "liq": [np.log(max(LIQ.get(m, 0), 1.0)) for m in mem]}, index=mem).rank(pct=True)
        return (wr * df.rep + wd * df["div"] + wl * df.liq).idxmin()
    if meth == "hy": return max(mem[1:], key=lambda m: L.dr_abs(C, [o for o in mem if o != m]))
    if meth == "dr": return max(mem, key=lambda m: L.dr_abs(C, [o for o in mem if o != m]))
    return max(mem, key=lambda m: L.explained(C, [o for o in mem if o != m], names))


if __name__ == "__main__":
    rng = np.random.default_rng(L.SEED); close, dv, R, PH, POS = L.load()
    members = {m: {k: [] for k in L.CLASSES} for m in METHODS}; strikes = {m: {} for m in METHODS}; out = {"reviews": {}, "oos": [], "knee": []}
    for end in L.REVIEWS:
        X = L.window(R, end); C0 = L.corr(X, L.MINW); Cp = L.corr(POS.loc[X.index, list(C0.index)], L.MINW); C = C0; P = PH.loc[X.index]; liq = L.liquidity(dv, end); LIQ.clear(); LIQ.update(liq); recent = R.loc[X.index[-8:]].notna().any(); memo = {}
        def dup(x, y):
            if abs(C.loc[x, y]) < L.DUP_R: return False
            if (x, y) not in memo: memo[(x, y)] = L.concordance(P, x, y) >= L.DUP_C
            return memo[(x, y)]
        byc = {k: [x for x in C.index if L.CLASS[x] == k] for k in L.CLASSES}; byc = {k: v for k, v in byc.items() if v}
        caps = {k: L.mp_count(C.loc[v, v], len(X)) for k, v in byc.items()}
        while sum(caps.values()) > L.CEIL: caps[max(caps, key=caps.get)] -= 1
        rec = {"caps": caps, "n_eligible": len(C)}
        for meth in METHODS:
            log = []; S = Cp if meth == "pos_nocap" else C0
            for k, cap in caps.items():
                if meth not in NOCAP: cap = max(cap, L.MIN_PER_CLASS)
                mem = [m for m in members[meth][k] if m in C.index and recent.get(m, False)]
                log += [f"{m} out (data end)" for m in members[meth][k] if m not in mem]
                cand = sorted([x for x in byc[k] if liq.get(x, 0) >= L.FLOOR], key=lambda x: -liq.get(x, 0))
                if meth == "pos_nocap": cand = [x for x in cand if x in Cp.index]; mem = [m for m in mem if m in Cp.index]
                if meth not in NOCAP:
                    flag = {}
                    for m in mem:
                        if liq.get(m, 0) < L.FLOOR and len(mem) > L.MIN_PER_CLASS: flag[m] = "below floor"
                        elif any(dup(m, o) and liq.get(o, 0) > liq.get(m, 0) for o in mem if o != m): flag[m] = "redundant"
                    if len(mem) > cap: flag.setdefault(weakest(meth, C, mem, byc[k]), "over cap")
                    for m in list(mem):
                        if m in flag:
                            strikes[meth][m] = strikes[meth].get(m, 0) + 1
                            if strikes[meth][m] >= 2: mem.remove(m); log.append(f"{m} out ({flag[m]})"); strikes[meth][m] = 0
                        else: strikes[meth][m] = 0
                if not mem and cand and meth in ("dr",) + NOCAP: mem = [cand[0]]
                while meth in NOCAP or len(mem) < cap:
                    opts = [x for x in cand if x not in mem and not any(dup(x, y) for y in mem)]
                    if not opts: break
                    b = pick_next(meth, S, mem, opts, byc[k])
                    if meth in GREEDY and len(mem) > 1 and L.dr_abs(S, mem + [b]) <= L.dr_abs(S, mem): break
                    if meth in NOCAP and len(mem) > 1 and L.dr_abs(S, mem + [b]) / L.dr_abs(S, mem) - 1 < 0.01: break
                    mem.append(b); log.append(f"{b} in")
                while meth not in NOCAP and len(mem) < L.MIN_PER_CLASS:                 # the minimum per class, from below the floor if need be
                    thin = sorted([x for x in byc[k] if x not in mem and not any(dup(x, y) for y in mem)], key=lambda x: -liq.get(x, 0))
                    if not thin: break
                    mem.append(thin[0]); log.append(f"{thin[0]} in (minimum per class" + (", below the floor)" if liq.get(thin[0], 0) < L.FLOOR else ")"))
                members[meth][k] = mem
                if meth == "dr":                                                        # knee: the full greedy curve in this class, no cap
                    seq, curve = cand[:1], [1.0]
                    while opts := [x for x in cand if x not in seq and not any(dup(x, y) for y in seq)]:
                        b = max(opts, key=lambda x: L.dr_abs(C, seq + [x])); seq.append(b); curve.append(L.dr_abs(C, seq))
                    out["knee"].append(dict(year=end.year, cls=k, cap=cap, curve=curve))
            rec[meth] = {k: list(v) for k, v in members[meth].items() if v}; rec[meth + "_log"] = log
        out["reviews"][str(end.year)] = rec
        print(end.year, caps, {m: sum(len(v) for v in rec[m].values()) for m in METHODS}, "| log:", "; ".join(rec.get("hy_log", rec[METHODS[0] + "_log"])), flush=True)

        n1 = R.index[(R.index > end) & (R.index <= end + pd.DateOffset(years=1))]; n3 = R.index[(R.index > end) & (R.index <= end + pd.DateOffset(years=3))]
        if len(n1) < 40: continue
        C1, P1 = L.corr(R.loc[n1], 40), L.corr(POS.loc[n1], 40); C3 = L.corr(R.loc[n3], L.MINW) if len(n3) >= L.MINW else None
        def scores(sel):
            flat = [x for v in sel.values() for x in v]
            s = dict(ev=float(np.nanmean([L.explained(C1, v, [x for x in C1.index if L.CLASS[x] == k]) for k, v in sel.items()])),
                     abs=L.mean_abs(C1, [x for x in flat if x in C1.index]), pos=L.mean_abs(P1, [x for x in flat if x in P1.index]))
            if C3 is not None: s["enb3"] = L.enb(C3, [x for x in flat if x in C3.index], "class")
            s["liq"] = float(np.median([np.log10(max(liq.get(x, 0), 1.0)) for x in flat]))   # log10 USD a day, at the review
            return s
        row = dict(year=end.year + 1)
        for meth in METHODS:
            sel = rec[meth]; s = scores(sel); rand = []
            for _ in range(NR):
                rs = {}
                for k, v in sel.items():
                    pool = [x for x in byc[k] if liq.get(x, 0) >= L.FLOOR] or v; rs[k] = list(rng.choice(pool, size=min(len(v), len(pool)), replace=False))
                rand.append(scores(rs))
            for key, val in s.items():
                rv = np.array([r[key] for r in rand]); better = (rv < val) if key in ("ev", "enb3", "liq") else (rv > val)
                row.update({f"{meth}_{key}": val, f"{meth}_{key}_rand": float(np.nanmedian(rv)), f"{meth}_{key}_beats": float(better.mean())})
        out["oos"].append(row)
    (L.RESULTS / "fill.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    D = pd.DataFrame(out["oos"])
    for key, lab in (("ev", "variance explained next year (higher better)"), ("abs", "mean |corr| next year (lower better)"),
                     ("pos", "mean |corr| trend-positioned next year (lower better)"), ("enb3", "effective bets over 3 years (higher better)"),
                     ("liq", "median liquidity of the selection, log10 USD a day (higher better)")):
        print(lab)
        for m in METHODS:
            c = f"{m}_{key}"; d = D[c].notna()
            print(f"   {m:9s} {D.loc[d, c].median():.3f}  random {D.loc[d, c + '_rand'].median():.3f}  beats random median {int((D.loc[d, c + '_beats'] > .5).sum())}/{int(d.sum())}")
    print("2025:", {m: out["reviews"]["2025"][m] for m in ("hy", "ev", "dr", "sc", "sc_liq")})
