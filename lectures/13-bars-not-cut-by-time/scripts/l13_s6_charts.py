"""Lecture 13 §6 charts: López de Prado's two failures against the fixed band, the Fed day, and the tails."""
import json, sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import numpy as np, polars as pl
from scipy.stats import norm
from plotly.subplots import make_subplots
import os, sys
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # tables print on any console; Jupyter handles its own
HERE = Path(__file__).resolve().parent                                     # lectures/13-.../scripts
sys.path[:0] = [str(HERE), str(HERE.parents[1] / "12-tick-data-the-tape"), str(HERE.parents[2])]   # this folder, tape.py, trading_models
import tape
L13_RESULTS = tape.ROOT / "interim" / "l13"; L13_RESULTS.mkdir(parents=True, exist_ok=True)          # results: in the data folder, never committed
FIG = Path(os.environ.get("L13_FIG", HERE.parent / "figures")); FIG.mkdir(parents=True, exist_ok=True)
PREFIX = os.environ.get("L13_PREFIX", "nb_")                               # "nb_": the lecture's own figures are never overwritten
import tape, bars, l13_s6 as m
from l13_s6_ldp_bar import _ldp_bar
from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure

apply_theme()
SYM = "BTCUSDT"; D = tape.ROOT / "interim" / "tape" / SYM
BAND = "band_H1800_m0"; C_BAND, C_DOLLAR, C_R1, C_R2 = SERIES[2], SERIES[0], SERIES[3], SERIES[1]
R = {}

# ---------------------------------------------------------------- 1. two failures: the bar length each construction ends up with, stress window
a, z = m.WINDOWS["stress"]
pre = [m.load_orders(a - timedelta(days=i)) for i in range(28, 0, -1)]
ET0 = float(np.median([len(o["u"]) for o in pre])) / m.N; Ebv0 = float(sum(o["s"].sum() for o in pre) / sum(len(o["u"]) for o in pre)); del pre
s1 = (0.0, 0, ET0, Ebv0); s2 = (0.0, 0, ET0, Ebv0); rows = []
for i in range((z - a).days + 1):
    d0 = a + timedelta(days=i); tape.wait_for_memory(1.5); o = m.load_orders(d0)
    e1, *s1 = m._ldp(o["s"], *s1, 10.0); e2, *s2 = _ldp_bar(o["s"], *s2, 10.0)
    rows.append(dict(day=d0, orders=len(o["u"]), r1_bars=len(e1), r1_ET=s1[2], r2_bars=len(e2), r2_ET=s2[2]))
L = pl.DataFrame(rows)
band = pl.read_parquet(m.OUT / f"stress_{BAND}.parquet").with_columns(pl.from_epoch("end_ms", time_unit="ms").alias("end"))
dol = pl.concat([pl.read_parquet(bars.bars_dir(SYM, "dollar") / f"{ym}.parquet") for ym in ("2022-08", "2022-09", "2022-10")]).with_columns(pl.from_epoch("end_ms", time_unit="ms").alias("end"))
cnt = lambda b: b.group_by(pl.col("end").dt.date().alias("day")).len()
L = L.join(cnt(band).rename({"len": "band"}), on="day", how="left").join(cnt(dol).rename({"len": "dollar"}), on="day", how="left").sort("day")
R["start"] = dict(ET0=round(ET0, 0), Ebv0=round(Ebv0, 1))
R["reading1_orders_per_bar_median"] = round(float((L["orders"] / L["r1_bars"]).median()), 1)
R["reading2_ET_end"] = round(float(L["r2_ET"][-1]), 0); R["reading2_days_without_bar"] = int((L["r2_bars"] == 0).sum()); R["days"] = L.height
R["band_orders_per_bar_median"] = round(float((L["orders"] / L["band"]).median()), 0); R["dollar_orders_per_bar_median"] = round(float((L["orders"] / L["dollar"]).median()), 0)
fig = make_subplots(rows=1, cols=1)
fig.add_scatter(x=L["day"], y=L["r2_ET"], mode="lines", line=dict(color=C_R2, width=2), name="López de Prado, reading 2: runaway (expected bar length)")
fig.add_scatter(x=L["day"], y=L["orders"] / L["dollar"], mode="lines", line=dict(color=C_DOLLAR, width=1.5), name="dollar bars (orders per bar)")
fig.add_scatter(x=L["day"], y=L["orders"] / L["band"], mode="lines", line=dict(color=C_BAND, width=2), name="fixed band (orders per bar)")
fig.add_scatter(x=L["day"], y=L["orders"] / L["r1_bars"], mode="lines", line=dict(color=C_R1, width=2), name="López de Prado, reading 1: collapse (orders per bar)")
fig.add_hline(y=ET0, line=dict(color=MUTED, dash="dot"))
fig.add_annotation(x=L["day"][0], y=np.log10(ET0), text="start: 48 bars a day", showarrow=False, xanchor="left", yanchor="top", yshift=-4, font=dict(size=11, color=MUTED))
fig.update_yaxes(type="log", title_text="orders per bar (log scale)", exponentformat="power")
fig.update_layout(title="Imbalance bars: López de Prado's construction collapses or runs away; the fixed band stays put<br><sup>BTCUSDT, August to October 2022; all start from the same "
                        "48 bars a day. Reading 1 averages the imbalance over recent orders, reading 2 over recent bars; both with a span of 10 bars</sup>",
                  height=500, width=1100, margin=dict(t=90), legend=dict(orientation="h", y=-0.15, x=0))
save_figure(fig, PREFIX + "13_13_imbalance_failures", FIG)

# ---------------------------------------------------------------- 2. the Fed day
d0 = date(2022, 9, 21); t0, t1 = datetime(2022, 9, 21), datetime(2022, 9, 22)
m1 = pl.read_parquet(D / "2022-09" / "m1.parquet", columns=["time", "close"]).filter(pl.col("time").is_between(t0, t1, closed="left"))
tb = pl.read_parquet(bars.bars_dir(SYM, "time") / "2022-09.parquet").with_columns(pl.from_epoch("end_ms", time_unit="ms").alias("end"))
rows = {"time (30 minutes)": (tb, INK), "dollar": (dol, C_DOLLAR), "imbalance, fixed band": (band, C_BAND)}
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.5, 0.5], vertical_spacing=0.04)
fig.add_scatter(x=m1["time"], y=m1["close"], mode="lines", line=dict(color=INK, width=1), showlegend=False, row=1, col=1)
R["fed_day"] = {}
for lab, (b, col) in rows.items():
    e = b.filter(pl.col("end").is_between(t0, t1, closed="left"))["end"]; R["fed_day"][lab] = len(e)
    fig.add_scatter(x=e, y=[lab] * len(e), mode="markers", marker=dict(symbol="line-ns", size=14, line=dict(width=1.2, color=col)), showlegend=False,
                    hovertemplate="%{x|%H:%M:%S}<extra>" + lab + "</extra>", row=2, col=1)
fed = L.filter(pl.col("day") == d0).row(0, named=True); R["fed_day"]["ldp_reading1"] = fed["r1_bars"]; R["fed_day"]["ldp_reading2"] = fed["r2_bars"]
fig.add_vline(x=datetime(2022, 9, 21, 18), line=dict(color=MUTED, width=1, dash="dot"))
fig.update_yaxes(categoryorder="array", categoryarray=list(rows)[::-1], showgrid=False, row=2, col=1); fig.update_yaxes(title_text="price, USDT", row=1, col=1)
fig.add_annotation(text=f"bars that day: time {R['fed_day']['time (30 minutes)']}, dollar {R['fed_day']['dollar']}, fixed band {R['fed_day']['imbalance, fixed band']}; "
                        f"López de Prado {fed['r1_bars']:,} (reading 1) and {fed['r2_bars']} (reading 2)", xref="paper", yref="paper", x=0, y=-0.17, showarrow=False, xanchor="left", font=dict(size=11, color=MUTED))
fig.update_layout(title="The Fed day, 21 September 2022: where the imbalance clock ticks<br><sup>One mark for every bar that closes; the dotted line is the decision at 18:00 UTC. "
                        "The imbalance clock bunches where the flow turns one-sided and goes quiet for hours when buying and selling balance</sup>",
                  height=580, width=1100, margin=dict(t=90, b=110, l=150))
save_figure(fig, PREFIX + "13_14_imbalance_fed_day", FIG)

# ---------------------------------------------------------------- 3. tails: both windows, each standardised in its own window
MONTHS = {"stress": ("2022-08", "2022-09", "2022-10"), "calm": ("2023-01", "2023-02", "2023-03")}
grid = np.linspace(0, 8, 81); fig = make_subplots(rows=1, cols=1); R["tails"] = {}
def z_of(b):
    r = np.diff(np.log(b.sort("end_ms")["close"].to_numpy())); return (r - r.mean()) / r.std()
for lab, col, dash, get in (("time (30 minutes)", INK, "dash", lambda w, lo, hi: pl.concat([pl.read_parquet(bars.bars_dir(SYM, "time") / f"{ym}.parquet") for ym in MONTHS[w]])),
                            ("dollar", C_DOLLAR, None, lambda w, lo, hi: pl.concat([pl.read_parquet(bars.bars_dir(SYM, "dollar") / f"{ym}.parquet") for ym in MONTHS[w]])),
                            ("imbalance, fixed band", C_BAND, None, lambda w, lo, hi: pl.read_parquet(m.OUT / f"{w}_{BAND}.parquet"))):
    zs = []
    for w, (lo, hi) in m.WINDOWS.items():
        lo_ms = int(datetime(lo.year, lo.month, lo.day, tzinfo=timezone.utc).timestamp() * 1000); hi_ms = int(datetime(hi.year, hi.month, hi.day, tzinfo=timezone.utc).timestamp() * 1000) + 86_400_000
        zs.append(z_of(get(w, lo, hi).filter(pl.col("end_ms").is_between(lo_ms, hi_ms, closed="left"))))
    zz = np.concatenate(zs); surv = np.array([(np.abs(zz) > g).mean() for g in grid])
    R["tails"][lab] = dict(bars=len(zz), beyond_4sd_per_10000=round(float((np.abs(zz) > 4).mean() * 1e4), 1), excess_kurtosis=round(float(np.mean(zz ** 4) - 3), 1))
    fig.add_scatter(x=grid, y=np.where(surv > 0, surv, np.nan), mode="lines", line=dict(color=col, width=2 if dash is None else 1.5, dash=dash), name=lab)
fig.add_scatter(x=grid, y=2 * norm.sf(grid), mode="lines", line=dict(color=MUTED, width=1.5, dash="dot"), name="normal distribution")
fig.update_yaxes(type="log", range=[-4.5, 0.1], title_text="share of bars with a larger move", exponentformat="power")
fig.update_xaxes(title_text="size of the move, in standard deviations of the clock's returns")
fig.update_layout(title="How fat are the tails? The imbalance clock against dollar and time bars<br><sup>August to October 2022 and January to March 2023, each window standardised on its own; "
                        "no bar is capped or cut</sup>", height=480, width=1100, margin=dict(t=90), legend=dict(orientation="h", y=-0.15, x=0))
save_figure(fig, PREFIX + "13_15_imbalance_tails", FIG)
(L13_RESULTS / "l13_s6_charts.json").write_text(json.dumps(R, indent=1, default=str)); print(json.dumps(R, indent=1, default=str))
