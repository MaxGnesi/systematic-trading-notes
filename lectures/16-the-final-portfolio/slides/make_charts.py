"""Charts for the Lecture 16 slides, drawn from the lecture's own tables (§4, §5, §6, §7).
Every number is checked against lecture.md before drawing, so the slides cannot drift from the lecture.
Usage: python lectures/16-the-final-portfolio/slides/make_charts.py"""
from pathlib import Path

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure

HERE = Path(__file__).resolve().parent
LECTURE = (HERE.parent / "lecture.md").read_text(encoding="utf-8")
FIG = HERE / "figures"
P1, P2 = "1990-2005 (untouched years)", "2006-2022 (reference)"
C1, C2 = SERIES[0], SERIES[1]


def check(*values):
    for v in values:
        s = f"{v:.2f}" if isinstance(v, float) else str(v)
        assert s in LECTURE, f"{s} not in lecture.md"


def bars(fig, x, y, name, col, row=None, col_=None, fmt="{:.2f}"):
    kw = dict(row=row, col=col_) if row else {}
    fig.add_bar(x=x, y=y, name=name, marker=dict(color=col, line=dict(color="#fcfcfb", width=2)),
                text=[fmt.format(v) for v in y], textposition="outside", cliponaxis=False, **kw)


def layout(fig, title, h=640, w=860):
    fig.update_xaxes(type="category")
    fig.update_layout(title=title, height=h, width=w, barmode="group", bargap=0.3, font=dict(size=19),
                      legend=dict(orientation="h", y=-0.14, x=0), margin=dict(t=70, l=70, r=30, b=90))


if __name__ == "__main__":
    apply_theme()
    # §4 Results: Sharpe ratio by portfolio
    names = ["Trend", "Carry", "Trend + carry<br>(the rule)", "Rival:<br>+ value", "US equities", "60/40"]
    s1, s2 = [0.78, 0.99, 1.11, 0.89, 0.57, 0.71], [0.67, 0.54, 0.84, 0.81, 0.56, 0.66]
    check(*s1, *s2)
    f = go.Figure(); bars(f, names, s1, P1, C1); bars(f, names, s2, P2, C2)
    layout(f, "Sharpe ratio by portfolio, after costs"); f.update_yaxes(title_text="Sharpe ratio", range=[0, 1.3])
    save_figure(f, "16s_results", FIG)

    # §5 The investor's view: 60/40 with a share of its risk in the rule
    share = ["0% (60/40)", "20%", "30%", "50%"]
    sh1, sh2, dd1, dd2 = [0.71, 0.97, 1.10, 1.31], [0.66, 0.84, 0.93, 1.04], [-24.6, -19.4, -16.4, -9.7], [-30.0, -27.4, -25.0, -20.7]
    check(*sh1, *sh2); [check(f"{v:.1f}%".replace("-", "−")) for v in dd1 + dd2]
    f = make_subplots(rows=1, cols=2, subplot_titles=("Sharpe ratio", "Worst drawdown, %"), horizontal_spacing=0.12)
    bars(f, share, sh1, P1, C1, 1, 1); bars(f, share, sh2, P2, C2, 1, 1)
    bars(f, share, dd1, P1, C1, 1, 2, "{:.1f}"); bars(f, share, dd2, P2, C2, 1, 2, "{:.1f}")
    for t in f.data[2:]: t.showlegend = False
    layout(f, "60/40 with part of its risk in the rule", w=1000)
    f.update_yaxes(range=[0, 1.5], row=1, col=1); f.update_yaxes(range=[-34, 0], row=1, col=2)
    save_figure(f, "16s_investor", FIG)

    # §6 Costs: the rule's Sharpe ratio when carry's trades cost more
    cost = ["5 bp (the rule)", "10 bp", "20 bp"]
    c1, c2 = [1.11, 1.01, 0.82], [0.84, 0.68, 0.36]
    check(*c1, *c2, 0.67)
    f = go.Figure(); bars(f, cost, c1, P1, C1); bars(f, cost, c2, P2, C2)
    f.add_hline(y=0.67, line=dict(color=INK, dash="dash", width=1.5), annotation_text="trend alone, 2006-2022: 0.67", annotation_position="top right", annotation_yshift=95)
    layout(f, "Trend + carry, Sharpe ratio by cost per carry trade"); f.update_yaxes(title_text="Sharpe ratio", range=[0, 1.3])
    pass
    save_figure(f, "16s_costs", FIG)

    # §7 The realistic number: haircuts, one source at a time
    per = ["1990-2005", "2006-2022", "2013-2026 (ETFs)"]
    bt, daily, cst = [1.11, 0.84, 0.45], [1.10, 0.78, 0.43], [1.00, 0.64, None]
    check(*bt, *daily, 1.00, 0.64)
    f = go.Figure(); bars(f, per, bt, "Backtest (monthly)", MUTED); bars(f, per, daily, "Measured on daily returns", C1)
    f.add_bar(x=per[:2], y=cst[:2], name="With carry's costs at 10 bp", marker=dict(color=C2, line=dict(color="#fcfcfb", width=2)),
              text=[f"{v:.2f}" for v in cst[:2]], textposition="outside", cliponaxis=False)
    f.add_hline(y=0.69, line=dict(color=INK, dash="dash", width=1.5), annotation_text="average after haircuts: about 0.69", annotation_position="top right", annotation_yshift=150)
    layout(f, "The rule's Sharpe ratio, cut one source at a time"); f.update_yaxes(title_text="Sharpe ratio", range=[0, 1.3])
    save_figure(f, "16s_realistic", FIG)
    print("ok")
