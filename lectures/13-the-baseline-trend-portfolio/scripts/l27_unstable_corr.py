"""Lecture 13 §4.5: weighing asset classes when correlations are unstable, a worked example.

Input: results/regimes.json (correlations of the five class trend streams, monthly, in eight regime windows 1973-2024).
Each class stream is taken at the same volatility (unit risk), as equal-risk sizing makes it. Methods:
  equal risk                        no correlations (the baseline)
  structured                        one average correlation for every pair (constant correlation), then equal risk contributions
  ERC / minimum variance, blended   on the month-weighted average of all windows: one matrix that blends the regimes
  ERC, crisis matrix                on the window in which the equal-risk portfolio carries the most risk (not the highest average |correlation|:
                                    in 2020 the large correlations were negative and lowered risk)
  min-max                           the long-only weights whose highest variance over the eight windows is lowest
Each method is scaled to 10% on the blended matrix, then its risk is read under each window's matrix.
Illustrative: all windows are used at once, so this is hindsight; a real review may use only past windows.
Output: results/unstable_corr.json. Usage: python l27_unstable_corr.py"""
import json
from pathlib import Path
import numpy as np
from scipy.optimize import minimize

HERE = Path(__file__).resolve().parent.parent
R = json.loads((HERE / "results" / "regimes.json").read_text(encoding="utf-8"))
W = R["windows"]
names = [n for n in W if not n.startswith("2023-2025")]           # the eight regimes; the baseline's own years excluded
CL = list(W[names[0]]["corr_trend"].keys())
mat = {n: np.array([[W[n]["corr_trend"][a][b] for b in CL] for a in CL]) for n in names}
months = {n: W[n]["months"] for n in names}
blend = sum(months[n] * mat[n] for n in names) / sum(months.values())
avg_abs = {n: np.mean(np.abs(mat[n][np.triu_indices(len(CL), 1)])) for n in names}
eq = np.ones(len(CL)) / len(CL)
crisis = max(names, key=lambda n: eq @ mat[n] @ eq)                  # the regime in which equal risk carries the most risk


def erc(C):
    n = len(C); b = np.ones(n) / n
    f = lambda w: 0.5 * w @ C @ w - b @ np.log(w)
    w = minimize(f, np.ones(n) / n, bounds=[(1e-9, None)] * n).x
    return w / w.sum()


def minvar(C):
    n = len(C)
    r = minimize(lambda w: w @ C @ w, np.ones(n) / n, bounds=[(0, 1)] * n, constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1}])
    return r.x


def minmax(Cs):
    n = len(Cs[0])
    # minimise t subject to w'Cw <= t for every regime matrix
    x0 = np.r_[np.ones(n) / n, 1.0]
    cons = [{"type": "eq", "fun": lambda x: x[:n].sum() - 1}] + [{"type": "ineq", "fun": (lambda x, C=C: x[n] - x[:n] @ C @ x[:n])} for C in Cs]
    r = minimize(lambda x: x[n], x0, bounds=[(0, 1)] * n + [(0, None)], constraints=cons, method="SLSQP")
    return r.x[:n]


rho_bar = blend[np.triu_indices(len(CL), 1)].mean()
struct = np.full_like(blend, rho_bar); np.fill_diagonal(struct, 1.0)
methods = {
    "Equal risk (no correlations)": np.ones(len(CL)) / len(CL),
    "Structured: one average correlation": erc(struct),
    "Equal risk contributions, blended matrix": erc(blend),
    "Minimum variance, blended matrix": minvar(blend),
    "Equal risk contributions, crisis matrix": erc(mat[crisis]),
    "Min-max over the regimes": minmax([mat[n] for n in names]),
}
out = {"classes": CL, "crisis_window": crisis, "average_correlation_blend": rho_bar,
       "stock_bond_trend": {n: W[n]["stock_bond_trend"] for n in names}, "stock_bond_trend_blend": blend[CL.index("Equity"), CL.index("Government bonds")],
       "avg_abs_overlap": avg_abs, "methods": {}}
for m, w in methods.items():
    scale = 0.10 / np.sqrt(w @ blend @ w)
    risk = {n: float(scale * np.sqrt(w @ mat[n] @ w)) for n in names}
    out["methods"][m] = {"weights": dict(zip(CL, map(float, w))), "risk_by_window": risk,
                         "worst": max(risk.values()), "best": min(risk.values()), "worst_window": max(risk, key=risk.get)}
(HERE / "results" / "unstable_corr.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
print("classes", CL, "| crisis window:", crisis, "| average correlation in the blend %.2f" % rho_bar)
print("stock-bond trend by window:", {n[:9]: round(v, 2) for n, v in out["stock_bond_trend"].items()}, "blend %.2f" % out["stock_bond_trend_blend"])
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l27 as M
from plotly.subplots import make_subplots
from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure
apply_theme()
fig = make_subplots(rows=1, cols=1)
show = (("Equal risk (no correlations)", INK, "circle"), ("Equal risk contributions, crisis matrix", SERIES[0], "diamond"), ("Min-max over the regimes", SERIES[1], "square"))
lab = [n.replace(" ", " ", 1) for n in names]
for m, c, sym in show:
    fig.add_scatter(x=[100 * out["methods"][m]["risk_by_window"][n] for n in names], y=lab, mode="markers", marker=dict(color=c, size=12, symbol=sym), name=m)
fig.add_vline(x=10, line=dict(color=MUTED, width=1, dash="dot"))
fig.update_xaxes(title_text="risk the portfolio would carry, % a year (target 10% on the blended matrix)", range=[0, 14])
fig.update_yaxes(autorange="reversed")
fig.update_layout(title="One target, eight regimes: the risk moves, whichever weights are chosen<br><sup>five asset-class trend streams at equal risk each; "
                        "weights from each method, scaled to 10% on the blended 1973-2024 matrix, then held under each regime's correlations</sup>",
                  height=520, width=1050, margin=dict(t=110, l=210, r=30, b=120), legend=dict(orientation="h", y=-0.2, x=0))
save_figure(fig, M.PREFIX + "27_unstable_corr", M.FIG)
for m, v in out["methods"].items():
    print(f"{m:44s}", " ".join(f"{100 * x:5.1f}" for x in v["weights"].values()), f"| risk {100 * v['best']:.1f}-{100 * v['worst']:.1f} worst in {v['worst_window'][:9]}")
