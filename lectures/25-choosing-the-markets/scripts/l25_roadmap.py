"""Lecture 25, a roadmap for growing capital (results/hypotheses.md, addendum 3, fixed 2026-11-13 before the run). At the end-2025 review:
stage 1 = the chosen universe; stage 2 = more bets (greedy diversification beyond the cap, above the floor, until the gain is < 1%); stage 3 = every
other market above the floor, grouped with its most correlated stage 1-2 member. Capacity per market under a placeholder risk-only weighting and
Lecture 9's heaviest trading day. Output: results/roadmap.json."""
import json, sys, warnings; warnings.filterwarnings("ignore")
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l25 as L

END = pd.Timestamp("2025-12-31"); VOL_TARGET = 0.10; PARTICIPATION = 0.01; DAY_TRADE = 0.20   # 2 x lambda (0.1): a full reversal, Lecture 9


def weights(C, vol, units):
    """Notional per unit of capital: equal risk per class, equal within (units = markets or groups), inverse volatility, scaled to 10% a year.
    units: {market: (class, unit id, share of the unit)}; long-only placeholder (a trend follower's signs vary; the scale is what matters here)."""
    names = list(units); cls = pd.Series({n: units[n][0] for n in names}); unit = pd.Series({n: units[n][1] for n in names})
    k = cls.nunique(); per_unit = {u: 1 / k / unit[cls == cls[unit[unit == u].index[0]]].nunique() for u in unit.unique()}
    raw = pd.Series({n: per_unit[unit[n]] * units[n][2] / vol[n] for n in names})
    cov = C.loc[names, names].values * np.outer(vol[names], vol[names]); pv = np.sqrt(raw.values @ cov @ raw.values)
    return raw * VOL_TARGET / pv


if __name__ == "__main__":
    close, dv, R, PH, POS = L.load(); X = L.window(R, END); C = L.corr(X, L.MINW); P = PH.loc[X.index]; liq = L.liquidity(dv, END)
    vol = X.std() * np.sqrt(52)
    s1 = json.loads((L.RESULTS / "fill.json").read_text(encoding="utf-8"))["reviews"]["2025"]["hy"]
    def dup(x, y): return abs(C.loc[x, y]) >= L.DUP_R and L.concordance(P, x, y) >= L.DUP_C
    s2 = {}
    for k, mem in s1.items():
        mem = list(mem); add = []
        cand = [x for x in C.index if L.CLASS[x] == k and liq.get(x, 0) >= L.FLOOR and x not in mem]
        while True:
            opts = [x for x in cand if x not in mem and not any(dup(x, y) for y in mem)]
            if not opts: break
            b = max(opts, key=lambda x: L.dr_abs(C, mem + [x]))
            if L.dr_abs(C, mem + [b]) / L.dr_abs(C, mem) - 1 < 0.01: break
            mem.append(b); add.append(b)
        s2[k] = add
    core = [x for v in s1.values() for x in v]; more = [x for v in s2.values() for x in v]; base = core + more
    rest = [x for x in C.index if x not in base and liq.get(x, 0) >= L.FLOOR]
    twin = {x: max(base, key=lambda m: abs(C.loc[x, m])) for x in rest}
    def capacity(units):
        w = weights(C, vol, units); cap = {}
        for u in set(v[1] for v in units.values()):
            m = [n for n in units if units[n][1] == u]; cap[u] = PARTICIPATION * sum(liq.get(n, 0) for n in m) / (DAY_TRADE * w[m].sum())
        return w, cap
    stages = {}
    for name, members, groups in (("1 core", core, {}), ("2 more bets", base, {}), ("3 capacity", base + rest, twin)):
        units = {}
        for n in members:
            u = groups.get(n, n); grp = [n] + [r for r, t in groups.items() if t == n] if n in base else None
            tot = sum(liq.get(g, 0) for g in ([u] + [r for r, t in groups.items() if t == u]))
            units[n] = (L.CLASS[n], u, liq.get(n, 0) / tot if tot > 0 else 1.0)
        w, cap = capacity(units)
        stages[name] = dict(n=len(members), members=members, capacity_usd=float(min(cap.values())), binding=min(cap, key=cap.get),
                            explained_all=L.explained(C, members, list(C.index)), mean_abs=L.mean_abs(C, members),
                            per_unit={u: float(c) for u, c in sorted(cap.items(), key=lambda z: z[1])}, weights=w.round(4).to_dict())
    out = dict(review=str(END.date()), stage1=s1, stage2=s2, stage3={x: twin[x] for x in rest}, liquidity={x: liq.get(x, 0) for x in C.index},
               vol=vol.round(4).to_dict(), stages=stages, assumptions=dict(vol_target=VOL_TARGET, participation=PARTICIPATION, day_trade=DAY_TRADE))
    (L.RESULTS / "roadmap.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("stage 2 adds:", s2)
    print("stage 3 adds:", len(rest), "markets; twins:", pd.Series(twin).value_counts().head(8).to_dict())
    for k, s in stages.items():
        print(f"stage {k}: {s['n']} markets, explains {s['explained_all']:.1%} of all 116, mean |corr| {s['mean_abs']:.2f}, capacity USD {s['capacity_usd'] / 1e6:,.0f} m, bound by {s['binding']}")
        print("    tightest:", {u: f"{c / 1e6:,.0f} m" for u, c in list(s['per_unit'].items())[:6]})
