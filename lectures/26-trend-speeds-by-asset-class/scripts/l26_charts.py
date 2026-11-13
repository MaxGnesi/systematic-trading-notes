"""Lecture 26, the areas and the random halves (results/select.json):
  26_halves  left: one real random split at the end-2025 review, quarters (x) by markets (y), coloured by half; right: the pass share of every
             stream at that review, one heatmap per class and for all markets together (rule by speed)
  26_areas   the pass share by speed (averaged over the three rules) at every yearly review 2012-2025, one heatmap per class: does the area stay?
Output: figures/26_*.png."""
import json, sys, warnings; warnings.filterwarnings("ignore")
from pathlib import Path
import numpy as np, pandas as pd
from plotly.subplots import make_subplots
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l26 as L
from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure

GROUPS = ("one_set",) + tuple(L.CLASSES); TITLE = {"one_set": "All markets, same vote per class", "Rates": "Government bonds", "FX": "Currencies"}
SCALE = [[0, "#fcfcfb"], [1, SERIES[0]]]

if __name__ == "__main__":
    apply_theme(); S = json.loads((L.RESULTS / "select.json").read_text(encoding="utf-8"))["reviews"]
    close, high, low, dv, rf = L.load_daily(); liq = L.L25.liquidity(dv, pd.Timestamp("2025-12-31"))
    mk = sorted([t for t in close.columns if liq.get(t, 0) >= L.FLOOR and close[t]["2007":"2025"].notna().sum() > 63 * 12], key=lambda t: (L.CLASSES.index(L.CLASS[t]), t))
    quarters = pd.period_range(L.START, "2025-12-31", freq="Q"); rng = np.random.default_rng(7)
    pm, pq = rng.permutation(len(mk)), rng.permutation(len(quarters)); A_m, A_q = set(pm[: len(mk) // 2]), set(pq[: len(quarters) // 2])
    G = np.array([[1 if (i in A_m and j in A_q) else (2 if (i not in A_m and j not in A_q) else 0) for j in range(len(quarters))] for i in range(len(mk))], float)
    fig = make_subplots(rows=3, cols=3, column_widths=[0.4, 0.3, 0.3], horizontal_spacing=0.08, vertical_spacing=0.12,
                        specs=[[{"rowspan": 3}, {}, {}], [None, {}, {}], [None, {}, {}]],
                        subplot_titles=["One random split, end of 2025: choose on blue, check on orange"] + [TITLE.get(g, g) for g in GROUPS])
    fig.add_heatmap(z=G, x=[str(q) for q in quarters], y=mk, colorscale=[[0, "#efeee8"], [0.5, SERIES[0]], [1, SERIES[1]]], zmin=0, zmax=2, showscale=False,
                    hovertemplate="%{y}, %{x}<extra></extra>", row=1, col=1)
    fig.update_yaxes(showticklabels=False, title_text=f"{len(mk)} markets above the floor", row=1, col=1)
    fig.update_xaxes(tickvals=[str(q) for q in quarters[::8]], tickangle=0, title_text="quarter", row=1, col=1)
    W = S["2025"]["weights"]
    for i, g in enumerate(GROUPS):
        r, c = divmod(i, 2); w = pd.Series(W[g]); Z = np.array([[w[f"{rule}_{h}"] for h in L.SPEEDS] for rule in L.RULES])
        fig.add_heatmap(z=Z, x=[str(h) for h in L.SPEEDS], y=["EWMA", "breakout", "return"], colorscale=SCALE, zmin=0, zmax=1, showscale=(i == 0),
                        colorbar=dict(title=dict(text="pass share", side="right"), x=1.01, len=0.9, thickness=10),
                        hovertemplate="%{y} %{x} days: %{z:.2f}<extra></extra>", row=r + 1, col=c + 2)
        fig.update_xaxes(type="category", title_text="speed, days" if r == 2 else None, tickfont=dict(size=9), row=r + 1, col=c + 2)
    fig.update_layout(title="Random halves and the areas they leave<br><sup>Left: grey cells are left out of this split; a stream works on a half if its Sharpe "
                            "ratio after costs is in the top half of the 36 there. Right: the share of 500 splits in which each stream works on both halves, "
                            "end-2025 review, excess returns, 5 bp</sup>", height=760, width=1250, margin=dict(t=110, l=70, r=60, b=60))
    save_figure(fig, L.PREFIX + "26_halves", L.FIG)

    years = sorted(S); fig = make_subplots(rows=2, cols=3, horizontal_spacing=0.06, vertical_spacing=0.18, subplot_titles=[TITLE.get(g, g) for g in GROUPS])
    for i, g in enumerate(GROUPS):
        r, c = divmod(i, 3)
        Z = np.array([[np.mean([S[y]["weights"][g][f"{rule}_{h}"] for rule in L.RULES]) for h in L.SPEEDS] for y in years])
        fig.add_heatmap(z=Z, x=[str(h) for h in L.SPEEDS], y=years, colorscale=SCALE, zmin=0, zmax=1, showscale=(i == 0),
                        colorbar=dict(title=dict(text="pass share", side="right"), x=1.01, thickness=10), hovertemplate="%{y}, %{x} days: %{z:.2f}<extra></extra>",
                        row=r + 1, col=c + 1)
        fig.update_xaxes(type="category", title_text="speed, days" if r == 1 else None, tickfont=dict(size=9), row=r + 1, col=c + 1); fig.update_yaxes(type="category", autorange="reversed", tickfont=dict(size=9), row=r + 1, col=c + 1)
    fig.update_layout(title="Does the area stay? Pass share by speed at each yearly review<br><sup>Average over the three rules; each row is one review, on all data "
                            "up to its year end; 500 random halves of quarters and markets</sup>", height=760, width=1250, margin=dict(t=110, l=60, r=60, b=60))
    save_figure(fig, L.PREFIX + "26_areas", L.FIG)
