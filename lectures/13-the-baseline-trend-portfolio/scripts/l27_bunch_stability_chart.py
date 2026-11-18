"""Lecture 13 §2.4 figure: inside a bunch (50, 60, 70 days and 200), how each method's weights move when one correlation inside the
bunch (50 against 60 days) shifts from -0.02 to +0.02 around its value. Output: figures/27_bunch_stability.png. Usage: python l27_bunch_stability_chart.py"""
import sys
import os
from pathlib import Path

import numpy as np
import pandas as pd
from plotly.subplots import make_subplots

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parents[2])]
import l27_edge_cases as E  # noqa: E402
from trading_models.allocation.hrp import hrp  # noqa: E402
from trading_models.plotting import INK, SERIES, apply_theme, save_figure  # noqa: E402

SP = [50, 60, 70, 200]; R = [[0, 1, 2], [3]]; C0 = E.corr(SP, [])
EPS = np.linspace(-0.02, 0.02, 41)


def hrp_w(C):
    cov = pd.DataFrame(C, index=range(4), columns=range(4))
    return hrp(cov, method="single").weights.reindex(cov.index).to_numpy()


M = {"Equal weight": lambda C: np.ones(4) / 4, "Equal risk contributions": E.erc, "Minimum variance": E.minvar, "HRP": hrp_w,
     "Grouped by region": lambda C: E.grouped(C, R)}
if __name__ == "__main__":
    apply_theme()
    f = make_subplots(rows=1, cols=5, shared_yaxes=True, subplot_titles=list(M), horizontal_spacing=0.035)
    cols = [SERIES[0], SERIES[1], SERIES[2], INK]
    for k, (m, fn) in enumerate(M.items()):
        W = []
        for e in EPS:
            C = C0.copy(); C[0, 1] = C[1, 0] = min(0.999, C0[0, 1] + e); W.append(fn(C))
        W = np.array(W) * 100
        for j in range(4):
            f.add_scatter(x=EPS, y=W[:, j], mode="lines", line=dict(color=cols[j], width=2.4), name=f"{SP[j]} days", showlegend=(k == 0), row=1, col=k + 1)
    f.update_xaxes(tickvals=[-0.015, 0, 0.015], ticktext=["−0.015", "0", "+0.015"], tickfont=dict(size=11))
    f.update_xaxes(title_text="change in the 50-60-day correlation", row=1, col=3)
    f.update_yaxes(range=[-2, 52], ticksuffix="%", row=1, col=1)
    f.update_layout(title="Inside a bunch: how the weights move when one correlation shifts slightly<br><sup>speeds of 50, 60 and 70 days (a bunch) and 200 days; the correlation of 50 and 60 days (0.933) moved by up to 0.02</sup>",
                    height=450, width=1250, margin=dict(t=110, l=60, r=20, b=110), legend=dict(orientation="h", y=-0.3, x=0))
    save_figure(f, os.environ.get("L27_PREFIX", "") + "27_bunch_stability", HERE.parent / "figures")
    print("ok")
