"""Lecture 16 §5: the patient entry of Lecture 15 §6 (rest one tick inside, re-post every 5 s, market order after a minute: 1.96 bp cheaper per unit
traded than a market order, measured on the tick tape) applied to the rule of §2, plain sizing, every speed and the blend; then figure 16_08."""
import json, sys
from pathlib import Path
from plotly.subplots import make_subplots
import os, sys
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # tables print on any console; Jupyter handles its own
HERE = Path(__file__).resolve().parent                                     # lectures/16-.../scripts
sys.path[:0] = [str(HERE), str(HERE.parents[1] / "13-bars-not-cut-by-time" / "scripts"), str(HERE.parents[1] / "12-tick-data-the-tape"), str(HERE.parents[2])]
import tape
L16_RESULTS = tape.ROOT / "interim" / "l16"; L16_RESULTS.mkdir(parents=True, exist_ok=True)          # results: in the data folder, never committed
FIG = Path(os.environ.get("L16_FIG", HERE.parent / "figures")); FIG.mkdir(parents=True, exist_ok=True)
PREFIX = os.environ.get("L16_PREFIX", "nb_")                               # "nb_": the lecture's own figures are never overwritten
from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure


J = L16_RESULTS / "l16_s5.json"
SETS = {f"{d} d": [d] for d in (0.25, 0.5, 1, 2, 3, 5, 8, 13, 21)}; SETS["blend 1-2-3 d"] = [1, 2, 3]
if not J.exists():
    import l16_buildup as B
    R = {}
    for name, ds in SETS.items():
        fc = B.forecast(B.dp_sd, ds); R[name] = {}
        for lab, cb in (("market orders", B.TAKER + B.HALF), ("patient entry", B.TAKER + B.HALF - B.REPOST_SAVING)):
            net, parts = B.simulate(B.sig_plain, cb, False, fc=fc)
            R[name][lab] = {"2021-2024": B.stats(net, parts, B.IS & B.live), "2025-2026": B.stats(net, parts, ~B.IS)}
    J.write_text(json.dumps(R, indent=1))
R = json.loads(J.read_text())

apply_theme()
SP = [k for k in SETS if k != "blend 1-2-3 d"]; X = ["6 h", "12 h", "1 d", "2 d", "3 d", "5 d", "8 d", "13 d", "21 d", "blend 1-3 d"]
fig = make_subplots(rows=1, cols=3, horizontal_spacing=0.06, subplot_titles=("Sharpe ratio, 2021-2024", "Sharpe ratio, 2025-2026", "Trading costs, % of capital a year"))
for c, (smp, key) in enumerate((("2021-2024", "sharpe"), ("2025-2026", "sharpe"), ("2021-2024", "cost")), start=1):
    for lab, col, sym in (("market orders", SERIES[0], "circle"), ("patient entry", SERIES[1], "diamond")):
        f = 100 if key == "cost" else 1
        fig.add_scatter(x=X[:-1], y=[f * R[s][lab][smp][key] for s in SP], mode="lines+markers", line=dict(color=col, width=2.2), marker=dict(size=8, symbol=sym),
                        name=lab if lab == "market orders" else "patient entry: rest one tick inside, re-post every 5 s, market order after a minute",
                        legendgroup=lab, showlegend=(c == 1), row=1, col=c)
        fig.add_scatter(x=[X[-1]], y=[f * R["blend 1-2-3 d"][lab][smp][key]], mode="markers", marker=dict(size=12, symbol=sym, color=col, line=dict(width=1.2, color=INK)),
                        showlegend=False, legendgroup=lab, row=1, col=c)
    fig.update_xaxes(type="category", categoryorder="array", categoryarray=X, tickangle=-45, row=1, col=c)
    fig.add_shape(type="rect", xref=("x" if c == 1 else f"x{c}"), yref=("y domain" if c == 1 else f"y{c} domain"), x0=1.5, x1=4.5, y0=0, y1=1, fillcolor="rgba(27,175,122,0.12)",
                  line_width=0, layer="below")
    if key == "sharpe": fig.add_hline(y=0, line=dict(color=INK, dash="dot", width=1), row=1, col=c)
fig.update_yaxes(type="log", title_text="% a year (log scale)", row=1, col=3)
fig.update_layout(title="A patient entry saves most where the rule trades most: at the fast speeds<br><sup>The rule of §2 with plain sizing and funding; the patient "
                        "entry's saving of 1.96 bp per unit traded is Lecture 15's measurement; shaded: the plateau; right of each panel: the blend</sup>",
                  height=480, width=1200, margin=dict(t=110, l=60), legend=dict(orientation="h", y=-0.3, x=0))
save_figure(fig, PREFIX + "16_08_patient_entry", FIG)
for s, v in R.items():
    print(f"{s:>14} market {v['market orders']['2021-2024']['sharpe']:+.2f}/{v['market orders']['2025-2026']['sharpe']:+.2f} c {v['market orders']['2021-2024']['cost']:.1%}"
          f" | patient {v['patient entry']['2021-2024']['sharpe']:+.2f}/{v['patient entry']['2025-2026']['sharpe']:+.2f} c {v['patient entry']['2021-2024']['cost']:.1%}")
