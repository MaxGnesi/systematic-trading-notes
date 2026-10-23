"""Lecture 14 §5: the forecasting test as one chart. For each yardstick (target built from 1-minute returns, 5-minute returns, 5-minute ranges):
how much each measure reduces the forecast loss (QLIKE, out of sample) against the bar's own squared hourly returns, by horizon."""
import json, sys
from pathlib import Path
from plotly.subplots import make_subplots
import os, sys
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # tables print on any console; Jupyter handles its own
HERE = Path(__file__).resolve().parent                                     # lectures/14-.../scripts
sys.path[:0] = [str(HERE), str(HERE.parents[1] / "13-bars-not-cut-by-time" / "scripts"), str(HERE.parents[1] / "12-tick-data-the-tape"), str(HERE.parents[2])]
import tape
L14_RESULTS = tape.ROOT / "interim" / "l14"; L14_RESULTS.mkdir(parents=True, exist_ok=True)          # results: in the data folder, never committed
FIG = Path(os.environ.get("L14_FIG", HERE.parent / "figures")); FIG.mkdir(parents=True, exist_ok=True)
PREFIX = os.environ.get("L14_PREFIX", "nb_")                               # "nb_": the lecture's own figures are never overwritten
from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure

apply_theme()
FILES = [("realised_1_min", "Yardstick: realised variance, 1 min"), ("realised_5_min", "Yardstick: realised variance, 5 min"), ("range_of_5-min_bars", "Yardstick: ranges of 5-min bars")]
MEAS = ["realised, 1 min", "realised, 5 min", "hourly ranges (Parkinson)", "duration (range-bar count)", "bipower, 1 min"]
HOR = [("next 1 h", "next hour", SERIES[0]), ("next 4 h", "next 4 hours", SERIES[1]), ("next 24 h", "next 24 hours", SERIES[3])]
fig = make_subplots(rows=1, cols=3, shared_yaxes=True, horizontal_spacing=0.03, subplot_titles=[t for _, t in FILES])
out = {}
for c, (f, _) in enumerate(FILES, start=1):
    R = json.loads((L14_RESULTS / f"l14_forecast_{f}.json").read_text(encoding="utf-8")); out[f] = {}
    for h, lab, col in HOR:
        q0 = R[h]["squared hourly returns"]["qlike"]
        x = [100 * (q0 - R[h][m]["qlike"]) / q0 for m in MEAS]; out[f][h] = dict(zip(MEAS, [round(v, 1) for v in x]))
        fig.add_scatter(x=x, y=MEAS, mode="markers", marker=dict(size=11, color=col), name=lab, legendgroup=lab, showlegend=(c == 1), row=1, col=c)
fig.update_yaxes(categoryorder="array", categoryarray=MEAS[::-1])
fig.update_xaxes(title_text="less forecast error than squared hourly returns, %", range=[0, 30])
fig.update_layout(title="Using the inside of the bar cuts the forecast error by 7% to 26%; which form matters little<br><sup>Risk of the next 1, 4 and 24 hours on hourly bars, "
                        "out of sample July 2023 to September 2026, scored against three yardsticks built in different ways; each measure does best against the yardstick built like itself</sup>",
                  height=430, width=1100, margin=dict(t=100, l=170), legend=dict(orientation="h", y=-0.22, x=0))
save_figure(fig, PREFIX + "14_10_forecasts", FIG)
print(json.dumps(out, indent=1))
