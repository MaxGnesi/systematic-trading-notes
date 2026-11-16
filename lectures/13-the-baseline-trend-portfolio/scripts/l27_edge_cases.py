"""Lecture 13 §2.2: edge cases for weighting speeds. Four sets of speeds (even, bunched, a near-copy, two bunches), correlations from the
speed ratio (corr = exp(-0.38 |ln ratio|), close to the overlap measured in §2.1: about 0.88 at a ratio of 1.4, 0.45 at 8; a near-copy 0.99).
Methods: equal weight, equal risk contributions, minimum variance long only, grouped (equal risk between regions, then within).
Measures: each region's share of the risk, and how far the weights move (largest change, points) when one correlation inside a region
moves by 0.01 up or down. Illustrative, not estimates. Output: results/edge_cases.json. Usage: python l27_edge_cases.py"""
import json
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

K = 0.38
CASES = {  # name: (speeds, regions as index lists, near-copy pairs)
    "Even: 50, 100, 200": ([50, 100, 200], [[0], [1], [2]], []),
    "Bunched: 50, 60, 70 and 200": ([50, 60, 70, 200], [[0, 1, 2], [3]], []),
    "A near-copy: 50, 50, 100, 200": ([50, 50, 100, 200], [[0, 1], [2], [3]], [(0, 1)]),
    "Two bunches: 50, 55, 60 and 180, 200, 220": ([50, 55, 60, 180, 200, 220], [[0, 1, 2], [3, 4, 5]], []),
}


def corr(sp, copies):
    C = np.array([[np.exp(-K * abs(np.log(a / b))) for b in sp] for a in sp])
    for i, j in copies: C[i, j] = C[j, i] = 0.99
    return C


def erc(C):
    n = len(C); f = lambda w: (0.5 * w @ C @ w - np.log(w).sum() / n, C @ w - 1 / (n * w))
    r = minimize(f, np.ones(n) / n, jac=True, bounds=[(1e-9, None)] * n, method="L-BFGS-B", options=dict(gtol=1e-14))
    return r.x / r.x.sum()


def minvar(C):
    n = len(C)
    r = minimize(lambda w: w @ C @ w, np.ones(n) / n, bounds=[(0, 1)] * n, constraints={"type": "eq", "fun": lambda w: w.sum() - 1},
                 method="SLSQP", options=dict(ftol=1e-14, maxiter=500))
    return np.clip(r.x, 0, None) / np.clip(r.x, 0, None).sum()


def grouped(C, regions):
    w = np.zeros(len(C))
    for g in regions:
        Cg = C[np.ix_(g, g)]; wg = erc(Cg) if len(g) > 1 else np.ones(1); w[g] = wg / np.sqrt(wg @ Cg @ wg)
    return w / w.sum()


METHODS = {"Equal weight": lambda C, R: np.ones(len(C)) / len(C), "Equal risk contributions": lambda C, R: erc(C),
           "Minimum variance, long only": lambda C, R: minvar(C), "Grouped by region": grouped}


def shares(w, C, regions):
    rc = w * (C @ w); rc = rc / rc.sum()
    return [float(rc[g].sum()) for g in regions]


if __name__ == "__main__":
    out = {}
    for name, (sp, R, copies) in CASES.items():
        C = corr(sp, copies); out[name] = {}
        g = next((g for g in R if len(g) > 1), None)                     # perturb one correlation inside the first region with several speeds
        for m, f in METHODS.items():
            w = f(C, R); moves = []
            if g:
                for eps in (0.01, -0.01):
                    C2 = C.copy(); i, j = g[0], g[1]; C2[i, j] = C2[j, i] = min(0.999, C[i, j] + eps)
                    moves.append(float(np.abs(f(C2, R) - w).max()))
            out[name][m] = dict(weights=[round(float(x), 4) for x in w], region_risk=[round(x, 3) for x in shares(w, C, R)],
                                max_move=round(max(moves), 4) if moves else None)
            print(f"{name:44s} {m:28s} weights {np.round(w * 100, 1)}  region risk {np.round(np.array(shares(w, C, R)) * 100).astype(int)}"
                  + (f"  max move {100 * max(moves):.1f} pts" if moves else ""))
    (Path(__file__).resolve().parent.parent / "results" / "edge_cases.json").write_text(json.dumps(out, indent=1), encoding="utf-8")


# --- how to space the speeds: same ratio, same day difference, U-shaped, erratic (40 to 400 days, six speeds) -------------------------
def spacing():
    lo, hi = 40, 400
    grids = {"Same ratio (geometric)": [int(x) for x in np.round(np.geomspace(lo, hi, 6))],
             "Same day difference (arithmetic)": [int(x) for x in np.round(np.linspace(lo, hi, 6))],
             "U-shaped: dense at both ends, none in the middle": [40, 45, 52, 310, 355, 400],
             "Erratic": [40, 48, 57, 90, 230, 400]}
    edges = np.geomspace(lo, hi, 4); out = {}                            # thirds of the range by ratio
    for name, sp in grids.items():
        C = corr(sp, []); lab = [min(2, int(np.searchsorted(edges, s, side="right") - 1)) for s in sp]
        R = [[i for i, l in enumerate(lab) if l == k] for k in range(3)]
        out[name] = {"speeds": sp, "per_third": [len(g) for g in R]}
        for m, f in [("Equal weight", lambda C: np.ones(len(C)) / len(C)), ("Equal risk contributions", erc),
                     ("Grouped by third", lambda C: grouped(C, [g for g in R if g]))]:
            w = f(C); rc = w * (C @ w); rc = rc / rc.sum()
            out[name][m] = [round(float(rc[g].sum()), 3) if g else 0.0 for g in R]
    (Path(__file__).resolve().parent.parent / "results" / "spacing.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    return out


if __name__ == "__main__":
    for k, v in spacing().items(): print(k, v)
