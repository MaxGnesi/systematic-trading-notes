"""Lecture 28, exploration after the filter results (labelled as such in results/hypotheses.md): why the patterns arise.
  1. Volatility (the user): trend should earn when volatility expands and suffer when it is extreme. Baseline Sharpe ratio by VIX quintile (of its
     own history to date) crossed with the 63-day change of the VIX (rising or falling), both known the day before.
  2. Fed on hold and dollar still: which asset classes earned the difference (ETFs, class returns of Lecture 27), and which years.
Descriptive only; nothing switched. Output: results/why.json, figures/28_volatility.png."""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
from plotly.subplots import make_subplots
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l28 as L
from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure
L26, M27 = L.L26, L.M27
CLASSES = ("Equity", "Rates", "Credit", "Commodities", "FX")

if __name__ == "__main__":
    apply_theme(); B = pd.read_parquet(L.OUT / "l28_base.parquet"); out = {}
    vix = L.fred("VIXCLS")
    fig = make_subplots(rows=2, cols=2, shared_yaxes="rows", horizontal_spacing=0.05, vertical_spacing=0.2,
                        subplot_titles=("Volatility (VIX): ETFs, out of sample 2013-2026", "Volatility (VIX): capstone futures 2006-2022",
                                        "Correlation across markets: ETFs", "Correlation across markets: capstone futures"))
    FIFTHS = ["lowest fifth", "second", "middle", "fourth", "highest fifth"]
    for c, (tag, start) in enumerate((("etf", L.ETF_START), ("futures", L.FUT_START))):
        base = B[tag].dropna().loc[start:L.END[tag]]; G = pd.read_parquet(L.OUT / f"l28_regimes_{tag}.parquet")
        v = vix.reindex(pd.bdate_range("1990-01-01", base.index[-1])).ffill()
        series = {"volatility": (v.rolling(21).mean(), np.log(v) - np.log(v.shift(63))),                 # level; 3-month change
                  "correlation": (G[("correlation", "measure")], G[("correlation", "measure")].diff(63))}
        for r_, (k, (lvl, chg)) in enumerate(series.items()):
            pct = lvl.shift(1).expanding(1260).rank(pct=True)
            q = pd.cut(pct, [0, .2, .4, .6, .8, 1.0], labels=FIFTHS).reindex(base.index)
            d = np.where(chg.shift(1).reindex(base.index) > 0, "rising (3 months)", "falling (3 months)")
            T = {dir_: {str(b): dict(sharpe=L26.sharpe(base.ret[(q == b) & (d == dir_)]), share=float(((q == b) & (d == dir_)).mean())) for b in FIFTHS}
                 for dir_ in ("rising (3 months)", "falling (3 months)")}
            out.setdefault(tag, {})[k] = T
            for dir_, col in (("rising (3 months)", SERIES[1]), ("falling (3 months)", SERIES[0])):
                fig.add_bar(x=FIFTHS, y=[T[dir_][b]["sharpe"] for b in FIFTHS], marker_color=col, name=dir_, legendgroup=dir_, showlegend=(c == 0 and r_ == 0), row=r_ + 1, col=c + 1)
            fig.update_xaxes(type="category", title_text=("VIX level" if k == "volatility" else "average correlation") + ", fifth of its own history to date", row=r_ + 1, col=c + 1)
            print(tag, k, {dir_: {b: (round(x["sharpe"], 2), f"{x['share']:.0%}") for b, x in T[dir_].items()} for dir_ in T})
    for r_ in (1, 2): fig.update_yaxes(title_text="Sharpe ratio of the baseline", row=r_, col=1)
    fig.update_layout(title="Trend by the level and direction of volatility and correlation<br><sup>the baseline trend portfolio's Sharpe ratio after costs by the level "
                            "(fifth of its history to date) and whether it rose or fell over the past three months, both known the day before; exploration after the filter results</sup>",
                      barmode="group", height=900, width=1250, margin=dict(t=110, l=70, r=30, b=110), legend=dict(orientation="h", y=-0.1, x=0))
    save_figure(fig, L.PREFIX + "28_volatility", L.FIG)
    # Fed and dollar: classes and years, ETFs
    D = pd.read_parquet(M27.OUT / "l27_daily.parquet"); base = B["etf"].dropna().loc[L.ETF_START:]
    G = pd.read_parquet(L.OUT / "l28_regimes_etf.parquet").reindex(base.index); share = lambda x: float(x.sum())
    for k, flag in (("fed", G[("fed", "hold")]), ("dollar", G[("dollar", "0.33")])):
        f = flag.astype(float).fillna(0).astype(bool); tot = D["rule"].reindex(base.index)
        cls = {c: {"still": float(D[f"ret_{c}"].reindex(base.index)[f].mean() * 252 / 5), "moving": float(D[f"ret_{c}"].reindex(base.index)[~f].mean() * 252 / 5)} for c in CLASSES}
        yrs = {str(y): dict(share_still=float(f[str(y)].mean()), ret_still=float(tot[str(y)][f[str(y)]].sum()), ret_moving=float(tot[str(y)][~f[str(y)]].sum())) for y in range(2013, 2027)}
        out["etf"][k] = dict(classes=cls, years=yrs)
        print(k, "class contribution a year (still / moving):", {c: (f"{v['still']:+.1%}", f"{v['moving']:+.1%}") for c, v in cls.items()})
        print(k, "years (share still, return still, return moving):", {y: (f"{v['share_still']:.0%}", f"{v['ret_still']:+.1%}", f"{v['ret_moving']:+.1%}") for y, v in yrs.items()})
    (L.RESULTS / "why.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
