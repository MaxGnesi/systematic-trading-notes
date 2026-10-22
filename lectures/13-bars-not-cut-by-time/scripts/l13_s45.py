"""Lecture 13 §4-§5: do the clocks differ, and are their returns closer to normal? From the bars of bars.py, five years."""
import json, sys
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
import bars
from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure

apply_theme()
SYM = "BTCUSDT"
ORDER = ["time", "tick", "volume", "dollar", "range", "cusum"]
LABEL = {"time": "time", "tick": "tick", "volume": "volume", "dollar": "dollar", "range": "range", "cusum": "CUSUM"}
COLOR = {"time": INK, "tick": SERIES[4], "volume": SERIES[1], "dollar": SERIES[0], "range": SERIES[2], "cusum": SERIES[3]}
B = {k: pl.concat([pl.read_parquet(f) for f in sorted(bars.bars_dir(SYM, k).glob("*.parquet"))]).sort("end_ms") for k in ORDER}
R = {}

# ---------------------------------------------------------------- §4 do they differ? bar closes per hour, correlated across clocks
hours = pl.concat([B[k].select((pl.col("end_ms") // 3_600_000).alias("h")).with_columns(pl.lit(k).alias("clock")) for k in ORDER])
H = hours.group_by("h", "clock").len().pivot(on="clock", index="h", values="len").fill_null(0).sort("h")
C = np.corrcoef(np.vstack([H[k].to_numpy() for k in ORDER]))
R["hourly_count_corr"] = {a: {b: round(float(C[i, j]), 2) for j, b in enumerate(ORDER)} for i, a in enumerate(ORDER)}
# how much of the market's activity falls into each clock's bars: dollars per bar, dispersion across bars
R["usd_per_bar_cv"] = {k: round(float(B[k]["usd"].std() / B[k]["usd"].mean()), 2) for k in ORDER}
R["minutes_per_bar_median_p10_p90"] = {k: [round(float(x), 1) for x in ((B[k]["end_ms"] - B[k]["start_ms"]) / 60_000).quantile_list if False] for k in []}
dur = {k: ((B[k]["end_ms"] - B[k]["start_ms"]) / 60_000).to_numpy() for k in ORDER}
R["minutes_per_bar"] = {k: dict(p10=round(float(np.quantile(dur[k], 0.1)), 1), median=round(float(np.median(dur[k])), 1), p90=round(float(np.quantile(dur[k], 0.9)), 1)) for k in ORDER}

# ---------------------------------------------------------------- §5 are returns closer to normal?
stats = {}
fig = make_subplots(rows=1, cols=1)
grid = np.linspace(0, 8, 81)
for k in ORDER:
    r = np.diff(np.log(B[k]["close"].to_numpy()))
    z = (r - r.mean()) / r.std()
    ac = lambda x: float(np.corrcoef(x[:-1], x[1:])[0, 1])
    stats[k] = dict(bars=len(r), excess_kurtosis=round(float(np.mean(z ** 4) - 3), 1), skew=round(float(np.mean(z ** 3)), 2),
                    beyond_4sd_per_10000=round(float((np.abs(z) > 4).mean() * 1e4), 1), ac1_returns=round(ac(r), 3), ac1_squared=round(ac(r ** 2), 3),
                    ac1_abs=round(ac(np.abs(r)), 3))
    surv = np.array([(np.abs(z) > g).mean() for g in grid])
    fig.add_scatter(x=grid, y=np.where(surv > 0, surv, np.nan), mode="lines", line=dict(color=COLOR[k], width=2 if k != "time" else 1.5, dash="dash" if k == "time" else None), name=LABEL[k])
fig.add_scatter(x=grid, y=2 * norm.sf(grid), mode="lines", line=dict(color=MUTED, width=1.5, dash="dot"), name="normal distribution")
fig.update_yaxes(type="log", range=[-5.5, 0.1], title_text="share of bars with a larger move", exponentformat="power")
fig.update_xaxes(title_text="size of the move, in standard deviations of the clock's returns")
fig.update_layout(title="How fat are the tails? Bar returns on six clocks against the normal distribution<br><sup>Every clock at about 48 bars a day, five years of BTCUSDT; "
                        "a line above the dotted curve means more large moves than a normal distribution has</sup>",
                  height=500, width=1100, margin=dict(t=90), legend=dict(orientation="h", y=-0.15, x=0))
save_figure(fig, PREFIX + "13_04_tails", FIG)
R["returns"] = stats
R["normal_beyond_4sd_per_10000"] = round(float(2 * norm.sf(4) * 1e4), 2)
(L13_RESULTS / "l13_s45.json").write_text(json.dumps(R, indent=1)); print(json.dumps(R, indent=1))
