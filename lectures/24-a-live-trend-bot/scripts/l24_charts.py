"""Lecture 24's figures. 24_architecture: the bot's layers and what flows between them (a diagram, not
data). 24_backtest: equity in BTC of the strategy and its rivals on Deribit, 2019-2026, from the capstone's
own backtest engine. Usage: python lectures/24-a-live-trend-bot/scripts/l24_charts.py"""
import os
import sys
from pathlib import Path

import plotly.graph_objects as go

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path[:0] = [str(REPO)]
from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure  # noqa: E402

FIG = HERE.parent / "figures"


def architecture():
    f = go.Figure()
    boxes = {  # name: (x, y, w, label, fill)
        "ex": (0.0, 3.0, 2.2, "<b>Deribit</b><br>the exchange", "#dbe8f7"),
        "conn": (3.6, 3.6, 2.4, "<b>connectors/</b><br>public feed (WebSocket)<br>REST: instruments, candles", "#e7f3ec"),
        "exe": (3.6, 2.2, 2.4, "<b>executors/</b><br>signed REST: orders,<br>position, fills", "#e7f3ec"),
        "strat": (7.4, 3.6, 2.4, "<b>strategies/trend/</b><br>signal.py + params.toml<br>(the same in the backtest)", "#fdecdf"),
        "bot": (7.4, 2.2, 2.4, "<b>run_bot.py</b><br>schedule, heartbeat,<br>reconcile, kill switch", "#fdecdf"),
        "db": (11.2, 2.9, 2.2, "<b>database/</b><br>orders, fills, decisions,<br>reconciliation, events", "#f6f5f1"),
    }
    for k, (x, y, w, lab, fill) in boxes.items():
        f.add_shape(type="rect", x0=x, x1=x + w, y0=y - 0.5, y1=y + 0.5, fillcolor=fill, line=dict(color=INK, width=1.2))
        f.add_annotation(x=x + w / 2, y=y, text=lab, showarrow=False, font=dict(size=12, color=INK))
    arrows = [  # (x0, y0, x1, y1, label, colour)
        (2.2, 3.35, 3.6, 3.6, "book, trades", SERIES[0]), (6.0, 3.6, 7.4, 3.6, "prices", SERIES[0]),
        (8.6, 3.1, 8.6, 2.7, "target", SERIES[1]), (7.4, 2.2, 6.0, 2.2, "order", SERIES[1]),
        (3.6, 2.2, 2.2, 2.65, "signed request", SERIES[1]), (2.2, 2.85, 3.6, 2.4, "fills, position", SERIES[2]),
        (9.8, 2.2, 11.2, 2.75, "record everything", MUTED), (11.2, 3.05, 9.8, 2.45, "our records", MUTED),
    ]
    for x0, y0, x1, y1, lab, c in arrows:
        f.add_annotation(x=x1, y=y1, ax=x0, ay=y0, xref="x", yref="y", axref="x", ayref="y", showarrow=True, arrowhead=3,
                         arrowsize=1.2, arrowwidth=2, arrowcolor=c, text="")
        dx, dy = 0.0, (0.17 if x1 > x0 else -0.2)          # labels of left-pointing arrows go below their line
        dx, dy = {"target": (0.35, 0.0), "record everything": (0.0, -0.33), "our records": (0.0, 0.33)}.get(lab, (dx, dy))
        f.add_annotation(x=(x0 + x1) / 2 + dx, y=(y0 + y1) / 2 + dy, text=lab, showarrow=False, font=dict(size=10, color=c))
    f.add_shape(type="rect", x0=3.4, x1=10.0, y0=1.35, y1=4.35, line=dict(color=MUTED, width=1, dash="dot"))
    f.add_annotation(x=6.7, y=1.15, text="the bot: each folder one job; only connectors/ and executors/ know the exchange",
                     showarrow=False, font=dict(size=11, color=MUTED))
    f.add_annotation(x=1.1, y=1.6, text="reconciliation:<br>exchange vs our records,<br>at start and after every trade",
                     showarrow=False, font=dict(size=10, color=INK))
    f.update_xaxes(visible=False, range=[-0.3, 13.7]); f.update_yaxes(visible=False, range=[0.9, 4.5])
    f.update_layout(title="The plumbing of a live trend bot<br><sup>data in from the exchange, decisions in the middle, signed orders out, and every step "
                          "recorded and checked against the exchange</sup>", height=470, width=1250, margin=dict(t=90, l=20, r=20, b=20), showlegend=False)
    save_figure(f, os.environ.get("L24_PREFIX", "") + "24_architecture", FIG)


def backtest():
    from capstone.backtest import engine
    from capstone.strategies.trend import params as P
    p = P.load(); c, fu = engine.load_minutes(); h = engine.hourly_frame(c, fu, p.decision_minute)
    runs = [("strategy: 2 + 7 days, 5-sigma take profit", p, INK, "solid"), ("2 days alone", p.replace(fast_spans_days=(2.0,)), SERIES[0], "dot"),
            ("7 days alone", p.replace(fast_spans_days=(7.0,)), SERIES[1], "dot"), ("without the take profit", p.replace(take_profit=False), SERIES[2], "dash")]
    f = go.Figure()
    for name, pp, col, dash in runs:
        eq = engine.run(h, pp).hourly["equity"].resample("D").last()
        f.add_scatter(x=eq.index, y=eq, mode="lines", name=name, line=dict(color=col, width=2.4 if dash == "solid" else 1.6, dash=dash))
    f.update_yaxes(title_text="equity, BTC (start 1 BTC)", type="log"); f.update_xaxes(title_text="date")
    f.update_layout(title="The strategy on Deribit, 2019-2026, out of sample for its settings<br><sup>BTC-PERPETUAL, hourly decisions at :23, "
                          "account in BTC; taker fee 3.5 bp, half a tick, recorded funding</sup>", height=520, width=1100,
                    margin=dict(t=90, l=70, r=30, b=110), legend=dict(orientation="h", y=-0.2, x=0))
    save_figure(f, os.environ.get("L24_PREFIX", "") + "24_backtest", FIG)


if __name__ == "__main__":
    apply_theme()
    architecture(); backtest()
    print("ok")
