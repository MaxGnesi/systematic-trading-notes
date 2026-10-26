"""Lecture 15 §4 charts, from l15_cascades.json. 15_05: the chance that the next hour is a cascade, by the last hour's volatility (fifths), 2021-2024 and
2025-2026. 15_06: what each warning adds to that chance beyond the last hour's volatility, with 95% intervals (days as clusters; within 24 h: weeks),
in-sample and out of sample."""
import json, sys
from pathlib import Path
from plotly.subplots import make_subplots
import os, sys
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # tables print on any console; Jupyter handles its own
HERE = Path(__file__).resolve().parent                                     # lectures/15-.../scripts
sys.path[:0] = [str(HERE), str(HERE.parents[1] / "13-bars-not-cut-by-time" / "scripts"), str(HERE.parents[1] / "12-tick-data-the-tape"), str(HERE.parents[2])]
import tape
L15_RESULTS = tape.ROOT / "interim" / "l15"; L15_RESULTS.mkdir(parents=True, exist_ok=True)          # results: in the data folder, never committed
FIG = Path(os.environ.get("L15_FIG", HERE.parent / "figures")); FIG.mkdir(parents=True, exist_ok=True)
PREFIX = os.environ.get("L15_PREFIX", "nb_")                               # "nb_": the lecture's own figures are never overwritten
from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure

apply_theme()

R = json.loads((L15_RESULTS / "l15_cascades.json").read_text())

# ---------------------------------------------------------------- 15_05: risk clusters
X = ["calmest fifth", "2nd", "3rd", "4th", "most volatile fifth"]
fig = make_subplots(rows=1, cols=1)
for lab, col in (("2021-2024", SERIES[0]), ("2025-2026", SERIES[1])):
    y = [R["control"][lab][str(k)] for k in range(5)]
    fig.add_bar(x=X, y=y, name=lab + (" (cut-offs set here)" if lab == "2021-2024" else " (out of sample)"), marker=dict(color=col, line=dict(width=0)),
                text=[f"{v:.2f}%" for v in y], textposition="outside")
fig.add_hline(y=R["cascade_rate_is"], line=dict(color=MUTED, dash="dot"), annotation_text="average: 1 hour in 100", annotation_position="top left")
fig.update_xaxes(title_text="the last hour's realised variance against its 28-day median")
fig.update_yaxes(title_text="chance that the next hour is a cascade, %", range=[0, 3.6])
fig.update_layout(title="Risk clusters: a cascade hour almost always follows an hour that was already turbulent<br><sup>Cascade: an hourly move of at least "
                        f"{R['cascade_cut']:.1f} times its typical size (the top 1% of 2021-2024). Five years of BTCUSDT</sup>",
                  barmode="group", bargap=0.25, height=460, width=1000, margin=dict(t=100), legend=dict(orientation="h", y=-0.22, x=0))
save_figure(fig, PREFIX + "15_05_risk_clusters", FIG)

# ---------------------------------------------------------------- 15_06: what the warnings add
W = [r for r in R["warnings"]]
NAMES = {"F1 open interest": "Open interest high", "F2 funding": "Funding far from 0.01%", "F3 crowding": "Long/short accounts lopsided", "F4a quiet": "Quiet day",
         "F4b complacency": "Weeks of calm (complacency)", "F5 time in band": "Long time in a tight band", "S1 open interest change": "Open interest falling fast",
         "S2 one-sided flow": "Flow on one side, minutes in a row", "S3 impact per dollar": "Price moves more per dollar", "S4 sweep": "A sweep of 10 bp or more"}
ORDER = list(NAMES)
fig = make_subplots(rows=1, cols=2, shared_yaxes=True, horizontal_spacing=0.03, subplot_titles=("A cascade in the next hour", "A cascade within the next 24 hours (fuel only)"))
for c, hz in enumerate(("1 h", "24 h"), start=1):
    for k, (lab, col, sym) in enumerate((("2021-2024", SERIES[0], "circle"), ("2025-2026", SERIES[1], "diamond"))):
        rr = {r["warning"]: r for r in W if r["horizon"] == hz and r["sample"] == lab}
        ys = [w for w in ORDER if w in rr]
        x = [rr[w]["added_pp"] for w in ys]; e = [1.96 * abs(rr[w]["added_pp"] / rr[w]["t"]) if rr[w]["t"] else 0 for w in ys]
        yy = [len(ORDER) - 1 - ORDER.index(w) + (0.15 if k == 0 else -0.15) for w in ys]      # the two periods side by side on each row
        fig.add_scatter(x=x, y=yy, mode="markers", marker=dict(color=col, size=9, symbol=sym), error_x=dict(type="data", array=e, thickness=1.4, width=3),
                        name=lab + (" (cut-offs set here)" if k == 0 else " (out of sample)"), legendgroup=lab, showlegend=(c == 1), row=1, col=c)
    fig.add_vline(x=0, line=dict(color=INK, dash="dot", width=1), row=1, col=c)
fig.update_yaxes(tickvals=list(range(len(ORDER))), ticktext=[NAMES[w] for w in ORDER][::-1], range=[-0.6, len(ORDER) - 0.4])
fig.update_xaxes(title_text="added chance, percentage points (± 95%)")
fig.update_layout(title="Beyond the last hour's volatility, the fuel measures add nothing; only a recent sweep points to more risk<br><sup>What each warning adds to the chance of a cascade, beyond the last hour's volatility.<br>Each warning: its top (bottom) fifth, cut-offs from "
                        "2021-2024; linear probability model with the last hour's volatility fifths as controls, days (24 h: weeks) as clusters</sup>",
                  height=580, width=1150, margin=dict(t=120, l=250), legend=dict(orientation="h", y=-0.18, x=0))
save_figure(fig, PREFIX + "15_06_warnings", FIG)
