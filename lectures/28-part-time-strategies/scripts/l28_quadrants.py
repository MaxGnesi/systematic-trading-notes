"""Lecture 28, §6: level and direction in four quadrants (exploration on the ETFs and the futures, then the two expectations checked on 1990-2005).
Quadrant: level (VIX 21-day average; average absolute correlation across markets) above or below its own average to date, and its 3-month change
rising or falling, both known the day before. ETFs and futures: average to date over at least 1260 days, as in the exploration; 1990-2005 from
results/confirm.json (l28_confirm.py, at least 750 days, since the series start later). Output: results/quadrants.json, figures/28_quadrants.png."""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
from plotly.subplots import make_subplots
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l28 as L
from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure
L26 = L.L26
Q = ("below falling", "below rising", "above falling", "above rising")
LAB = ["below, falling", "below, rising", "above, falling", "above, rising"]

if __name__ == "__main__":
    apply_theme(); B = pd.read_parquet(L.OUT / "l28_base.parquet"); vix = L.fred("VIXCLS"); out = {}
    for tag, start in (("etf", L.ETF_START), ("futures", L.FUT_START)):
        base = B[tag].dropna().loc[start:L.END[tag]]; G = pd.read_parquet(L.OUT / f"l28_regimes_{tag}.parquet")
        v = vix.reindex(pd.bdate_range("1990-01-01", base.index[-1])).ffill(); c = G[("correlation", "measure")]
        for k, (lvl, chg) in {"volatility": (v.rolling(21).mean(), np.log(v) - np.log(v.shift(63))), "correlation": (c, c.diff(63))}.items():
            l = lvl.shift(1); above = (l > l.expanding(1260).mean()).reindex(base.index); up = (chg.shift(1) > 0).reindex(base.index)
            out.setdefault(tag, {})[k] = {f"{'above' if a else 'below'} {'rising' if u else 'falling'}":
                                          dict(sharpe=L26.sharpe(base.ret[(above == a) & (up == u)]), share=float(((above == a) & (up == u)).mean()))
                                          for a in (False, True) for u in (False, True)}
            print(tag, k, {s: (round(x["sharpe"], 2), f"{x['share']:.0%}") for s, x in out[tag][k].items()})
    C = json.loads((L.RESULTS / "confirm.json").read_text(encoding="utf-8")); out["1990-2005"] = {k: C[k] for k in ("volatility", "correlation")}
    (L.RESULTS / "quadrants.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    cols = (("etf", "ETFs 2013-26"), ("futures", "futures 2006-22"), ("1990-2005", "untouched 1990-2005"))
    fig = make_subplots(rows=2, cols=3, shared_yaxes=True, horizontal_spacing=0.04, vertical_spacing=0.2,
                        subplot_titles=[f"Volatility: {n}" for _, n in cols] + [f"Correlation: {n}" for _, n in cols])
    MARK = {"volatility": ("above falling", "above rising"), "correlation": ("below rising",)}   # E2 compares the two; E1 names one
    for r, k in enumerate(("volatility", "correlation")):
        for c, (tag, _) in enumerate(cols):
            T = out[tag][k]; colour = [SERIES[0] if s in MARK[k] else MUTED for s in Q]
            fig.add_bar(x=LAB, y=[T[s]["sharpe"] for s in Q], marker_color=colour, text=[f"{T[s]['share']:.0%} of days" for s in Q], textposition="outside",
                        textfont=dict(size=11, color=INK), showlegend=False, row=r + 1, col=c + 1)
            fig.update_xaxes(type="category", tickangle=0, title_text="level against its average to date, 3-month direction", title_font=dict(size=11), row=r + 1, col=c + 1)
        fig.update_yaxes(title_text="Sharpe ratio of the trend portfolio", row=r + 1, col=1)
    fig.update_yaxes(range=[-1.1, 2.6])
    fig.update_layout(title="Level and direction of volatility and correlation, found and checked<br><sup>trend portfolio's Sharpe ratio after costs by quadrant: level above or below "
                            "its own average to date, rising or falling over three months, both known the day before; blue: the quadrants of the two expectations "
                            "fixed before 1990-2005 was loaded</sup>", height=850, width=1300, margin=dict(t=110, l=70, r=30, b=60))
    save_figure(fig, L.PREFIX + "28_quadrants", L.FIG)
