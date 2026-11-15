"""Lecture 28, §7 (exploratory, outside the Benjamini-Hochberg families, as fixed 2026-11-15): commodity trend by the shape of the futures curve.
For each commodity of the capstone futures (crude oil, natural gas, gold, corn, soybeans, wheat, cocoa) and each day: the front contract is the
nearest one more than five trading days before its last day in the data, the next is the following contract; the curve gap is the log of front
over next, annualised by the days between the two contracts' last days. Backwardation: gap > 0 (front above next); contango: gap < 0. Known the
day before. Each market's trend stream (the baseline's held speeds, equal weight, after costs) is split by its own curve state; the commodity
sleeve (markets at equal risk) is split by whether most of its markets are in backwardation. Descriptive: nothing is switched.
Output: results/curves.json, figures/28_curves.png."""
import json, re, sys
from pathlib import Path
import numpy as np, pandas as pd
import plotly.graph_objects as go
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l28 as L
from l28_scan import band
from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure
L26, FT = L.L26, L.FT
KAGGLE = Path(L.L25.DATA).parent / "kaggle"
MARKETS = {"nymex-cl": "Crude oil", "nymex-ng": "Natural gas", "comex-gc": "Gold", "cbot-corn": "Corn", "cbot-soybeans": "Soybeans",
           "cbot-wheat": "Wheat", "ice-cocoa": "Cocoa"}
CODES = "FGHJKMNQUVXZ"


def curve(market):
    """Daily annualised front-next gap, known at each day's close."""
    C = []
    for f in (KAGGLE / market).glob("*.csv"):
        m = re.search(r"([FGHJKMNQUVXZ])(\d{4})\.csv$", f.name)
        x = pd.read_csv(f, index_col=0, parse_dates=True)["Close"].sort_index().dropna(); x = x[x > 0]
        if len(x) > 20: C.append((int(m.group(2)) * 12 + CODES.index(m.group(1)), x))
    C.sort(key=lambda c: c[0]); last = [c[1].index[-1] for c in C]
    days = pd.bdate_range("2000-01-01", "2022-12-31"); out = pd.Series(np.nan, days)
    P = pd.DataFrame({i: c[1] for i, c in enumerate(C)}).reindex(days)
    pos = np.searchsorted(np.array(last, dtype="datetime64[ns]"), (days + pd.offsets.BDay(5)).to_numpy())   # first contract ending > 5 days ahead
    for k, d in enumerate(days):
        i = pos[k]
        if i + 1 < len(C):
            a, b = P.iat[k, i], P.iat[k, i + 1]; gap_days = (last[i + 1] - last[i]).days
            if np.isfinite(a) and np.isfinite(b) and gap_days > 0: out.iat[k] = np.log(a / b) * 365 / gap_days
    return out


def streams():
    S = pd.read_pickle(FT.CACHE); N = {}
    for t in MARKETS:
        x = S[t]["ratio"].dropna(); x = x[x > 0]; N[t] = L26.net(L26.stream_returns(x, x, x))[FT.HELD].mean(axis=1)
    return pd.DataFrame(N)


if __name__ == "__main__":
    apply_theme(); start, end = L.FUT_START, L.END["futures"]
    G = pd.DataFrame({t: curve(t) for t in MARKETS}).shift(1)                      # known the day before
    N = streams(); vol = N.rolling(756, min_periods=252).std().shift(1)
    Z = (N / vol).loc[start:end]                                                    # each market at equal risk
    out = {"markets": {}}
    for t, name in MARKETS.items():
        r = Z[t].dropna(); g = G[t].reindex(r.index); ok = g.notna(); r, back = r[ok], (g[ok] > 0)
        out["markets"][t] = dict(name=name, share_back=float(back.mean()), sharpe_back=L26.sharpe(r[back]), sharpe_contango=L26.sharpe(r[~back]),
                                 sharpe_all=L26.sharpe(r), ci90=band(r, ~back), median_gap=float(g[ok].median()))
        print(f"{name:12s} backwardation {back.mean():.0%} of days | trend Sharpe: backwardation {L26.sharpe(r[back]):+.2f}, contango {L26.sharpe(r[~back]):+.2f}, all {L26.sharpe(r):+.2f}", flush=True)
    sleeve = Z.mean(axis=1, skipna=True).dropna(); nb = (G.reindex(sleeve.index) > 0).sum(axis=1); na = G.reindex(sleeve.index).notna().sum(axis=1)
    ok = na >= 5; sleeve, most = sleeve[ok], (nb / na)[ok] > 0.5
    out["sleeve"] = dict(share_back=float(most.mean()), sharpe_back=L26.sharpe(sleeve[most]), sharpe_contango=L26.sharpe(sleeve[~most]), sharpe_all=L26.sharpe(sleeve),
                         ci90=band(sleeve, ~most))
    print("sleeve", {k: (round(v, 2) if isinstance(v, float) else v) for k, v in out["sleeve"].items()})
    (L.RESULTS / "curves.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    rows = list(out["markets"].values()) + [out["sleeve"]]
    names = [f"{m.get('name', '<b>Commodity<br>sleeve</b>')}<br><span style='font-size:11px'>{m['share_back']:.0%} of days<br>backwardated</span>" for m in rows]
    fig = go.Figure()
    for key, nm, col in (("sharpe_back", "curve in backwardation (front above next)", SERIES[0]), ("sharpe_contango", "curve in contango (front below next)", SERIES[1])):
        v = [m[key] for m in rows]
        fig.add_bar(x=names, y=v, name=nm, marker_color=col, text=[f"{x:+.2f}" for x in v], textposition="outside", textfont=dict(color=INK, size=12))
    fig.add_hline(y=0, line=dict(color=INK, width=1))
    fig.update_yaxes(title_text="Sharpe ratio of the trend stream, after costs", range=[-2.7, 1.2])
    fig.update_xaxes(tickangle=0)
    fig.update_layout(title="Commodity trend by the shape of the futures curve<br><sup>capstone futures 2006 to November 2022; each market's trend stream on the days its curve "
                            "was in backwardation or in contango, known the day before; <br>sleeve: by whether most markets were backwardated; exploratory, nothing switched</sup>",
                      barmode="group", height=680, width=1150, margin=dict(t=115, l=70, r=30, b=150), legend=dict(orientation="h", y=-0.25, x=0))
    save_figure(fig, L.PREFIX + "28_curves", L.FIG)
