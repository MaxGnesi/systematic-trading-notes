"""Lecture 29, §1 key chart: the value of 100 invested, monthly, futures period 2006 to October 2022: trend (Lecture 27's baseline across all its
markets, with both Treasury funds), carry (the four groups together, the rule), and the two at equal risk, scaled on their past to trend's risk.
Excess returns over cash, after costs. Output: figures/29_key.png, results/key.json."""
import json, os, sys
from pathlib import Path
import numpy as np, pandas as pd
import plotly.graph_objects as go
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); import l29_combined as M, l29_grids as Gr, l29_bonds_g10 as G, l29 as L
RESD = Path(os.environ.get("L29_RESULTS", HERE.parent / "results")); RESD.mkdir(parents=True, exist_ok=True)
from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure
FIG, RES = HERE.parent / "figures", RESD; FIG.mkdir(exist_ok=True)
A, B = "2006-01", "2022-10"

if __name__ == "__main__":
    apply_theme(); Gs = M.groups()
    W = {g: Gr.sig(Gs[g]["C"], Gs[g]["R"]) for g in Gs}
    carry = M.scale_total(pd.DataFrame({g: G.stream(W[g], Gs[g]["R"]) for g in Gs}).mean(axis=1, skipna=True)).loc[A:B]
    trend = M.compound(pd.read_parquet(L.RAW / "l29_trend_futures_fixed.parquet")["ret"]).loc[A:B]
    comb = M.with_trend(carry, trend); idx = comb.index
    lines = (("Trend + carry (equal risk)", comb, SERIES[0], "solid"), ("Trend (the baseline portfolio)", trend.loc[idx], INK, "solid"),
             ("Carry alone", carry.loc[idx], SERIES[1], "dot"))
    fig = go.Figure(); out = {}
    for (name, r, col, dash), dy in zip(lines, (0, 14, -14)):
        st = Gr.stats(r); w = 100 * (1 + r).cumprod(); x = w.index.to_timestamp(how="end")
        out[name] = dict({k: float(v) for k, v in st.items()}, ret=float((1 + r).prod() ** (12 / len(r)) - 1))
        fig.add_scatter(x=x, y=w, name=name, line=dict(color=col, width=2.6 if dash == "solid" else 2, dash=dash))
        fig.add_annotation(x=x[-1], y=w.iloc[-1], text=f"<b>{name.split(' (')[0]}</b><br>Sharpe {st['sharpe']:.2f} · {out[name]['ret']:.1%} a year",
                           showarrow=False, xanchor="left", xshift=8, yshift=dy, align="left", font=dict(size=12, color=col))
    fig.update_yaxes(title_text="value of 100 invested (excess return over cash)")
    fig.update_xaxes(range=[idx[0].to_timestamp(), idx[-1].to_timestamp() + pd.Timedelta(days=40)])
    fig.update_layout(title="Carry next to trend<br><sup>capstone futures period, monthly, after costs; trend = the whole baseline portfolio; carry = currencies, commodities, "
                            "government bonds and equity indices of ten to fifteen countries</sup>",
                      height=560, width=1250, margin=dict(t=90, l=80, r=210, b=110), legend=dict(orientation="h", y=-0.12, x=0))
    save_figure(fig, os.environ.get("L29_PREFIX", "") + "29_key", FIG)
    out["corr_trend_carry"] = float(carry.loc[idx].corr(trend.loc[idx])); out["start"] = str(idx[0]); out["end"] = str(idx[-1])
    (RES / "key.json").write_text(json.dumps(out, indent=1), encoding="utf-8"); print(json.dumps(out, indent=1))
