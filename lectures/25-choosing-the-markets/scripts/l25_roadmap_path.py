"""Lecture 25, the roadmap as a path (results/roadmap.json): markets added one at a time (x) against the share of the variance of all 116 ETFs they
explain (top) and the mean |correlation| among them (bottom). Stage 1 is drawn in the order that explains most at each step; stage 2 in its own order
(explained variance, to 85%); stage 3 most liquid first. Output: figures/25_roadmap_path.png."""
import json, sys, warnings; warnings.filterwarnings("ignore")
from pathlib import Path
import pandas as pd
from plotly.subplots import make_subplots
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l25 as L
sys.path.insert(0, str(L.REPO)); from trading_models.plotting import INK, MUTED, GRID, SERIES, apply_theme, save_figure

if __name__ == "__main__":
    apply_theme(); R = json.loads((L.RESULTS / "roadmap.json").read_text(encoding="utf-8"))
    close, dv, Rw, PH, POS = L.load(); C = L.corr(L.window(Rw, pd.Timestamp(R["review"])), L.MINW); allm = list(C.index)
    core = [x for v in R["stage1"].values() for x in v]; seq, path1 = [], []
    while len(seq) < len(core):                                             # stage 1, ordered by what explains most at each step
        b = max([x for x in core if x not in seq], key=lambda x: L.explained(C, seq + [x], allm)); seq.append(b)
        path1.append(dict(n=len(seq), added=b, explained=L.explained(C, seq, allm), mean_abs=L.mean_abs(C, seq)))
    p2 = [p for p in R["stage2_path"] if "added" in p]; p3 = R["stage3_path"]
    stages = (("Stage 1: core", path1, SERIES[0]), ("Stage 2: more bets", p2, SERIES[1]), ("Stage 3: capacity", p3, MUTED))
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.07, row_heights=[0.68, 0.32],
                        subplot_titles=("Share of the variance of all 116 ETFs explained by the markets chosen so far", "Mean correlation among them (sign ignored)"))
    last = None
    for name, P, c in stages:
        x = ([last["n"]] if last else []) + [p["n"] for p in P]; y1 = ([last["explained"]] if last else []) + [p["explained"] for p in P]
        y2 = ([last["mean_abs"]] if last else []) + [p["mean_abs"] for p in P]
        fig.add_vrect(x0=x[0] + (0.5 if last else -0.5), x1=x[-1] + 0.5, fillcolor=c, opacity=0.08, line_width=0, layer="below")
        fig.add_scatter(x=x, y=y1, mode="lines+markers", line=dict(color=c, width=2), marker=dict(size=5), name=name, row=1, col=1,
                        text=([""] if last else []) + [p["added"] for p in P], hovertemplate="%{x} markets, + %{text}: %{y:.1%}<extra></extra>")
        k = [i for i, n in enumerate(x) if n >= 2]                          # a single market has no correlation to average
        fig.add_scatter(x=[x[i] for i in k], y=[y2[i] for i in k], mode="lines", line=dict(color=c, width=2), showlegend=False, row=2, col=1)
        last = P[-1]
    for p in path1[:6]:
        fig.add_annotation(x=p["n"], y=p["explained"], text=p["added"], showarrow=False, xshift=-16, yshift=4, font=dict(size=10, color=INK), row=1, col=1)
    fig.add_annotation(x=25, y=0.42, text="<b>added in stage 2</b>, in order:<br>" + "<br>".join(", ".join(q["added"] for q in p2[i:i + 4]) for i in range(0, len(p2), 4)),
                       showarrow=False, align="left", font=dict(size=11, color=SERIES[1]), bgcolor="rgba(252,252,251,0.9)", row=1, col=1)
    fig.add_annotation(x=56, y=0.7, text="<b>stage 3</b>, most liquid first:<br>" + ", ".join(q["added"] for q in p3[:6]) + ", ...",
                       showarrow=False, align="left", font=dict(size=11, color=INK), bgcolor="rgba(252,252,251,0.9)", row=1, col=1)
    for P, txt in ((path1, "core: {n} markets, {e:.0%}"), (p2, "more bets: {n} markets, {e:.0%}"), (p3, "capacity: {n} markets, {e:.0%}")):
        fig.add_annotation(x=P[-1]["n"], y=P[-1]["explained"], text=txt.format(n=P[-1]["n"], e=P[-1]["explained"]), showarrow=True, ax=0, ay=60,
                           font=dict(size=11, color=INK), bgcolor="rgba(252,252,251,0.9)", row=1, col=1)
    fig.add_hline(y=0.85, line=dict(color=INK, width=1, dash="dot"), row=1, col=1)
    fig.update_yaxes(tickformat=".0%", range=[0.2, 1], title_text="explained", row=1, col=1); fig.update_yaxes(range=[0, 0.45], title_text="mean |correlation|", row=2, col=1)
    fig.update_xaxes(title_text="number of markets", row=2, col=1)
    fig.update_layout(title="The roadmap as a path: new bets first, then capacity<br><sup>End-2025 review, weekly log returns 2023-2025; dotted line: the 85% target of stage 2; "
                            "stage 3 adds the most liquid near-duplicates first, each sharing the risk budget of its twin</sup>",
                      height=820, width=1250, margin=dict(t=110, l=80, r=30, b=60), legend=dict(orientation="h", y=1.07, x=0))
    save_figure(fig, "25_roadmap_path", L.FIG)
    print([(p["added"], round(p["explained"], 3)) for p in path1])
