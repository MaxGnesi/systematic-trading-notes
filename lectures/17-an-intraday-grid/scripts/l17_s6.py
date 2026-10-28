"""Lecture 17 §6: the grid next to the trend rule of Lecture 16 (step 2, re-posted entry, perpetual), daily nets in % of capital.
(1) Correlation of daily results. (2) The grid's result by the size of the trend forecast at the start of the day (the last finished hour before
00:00 UTC; flat / medium / strong, thirds cut on 2021-24): known in advance. (3) Portfolios: the grid scaled to the trend rule's volatility, given
10% or 25% of the weight; the rule: adding a strategy raises the Sharpe ratio only if its Sharpe ratio exceeds the correlation x the existing one."""
import json, sys
from pathlib import Path
import numpy as np, polars as pl
import os, sys
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # tables print on any console; Jupyter handles its own
HERE = Path(__file__).resolve().parent                                     # lectures/17-.../scripts
sys.path[:0] = [str(HERE), str(HERE.parents[1] / "16-trend-on-the-tape" / "scripts"), str(HERE.parents[1] / "13-bars-not-cut-by-time" / "scripts"),
                str(HERE.parents[1] / "12-tick-data-the-tape"), str(HERE.parents[2])]
import tape
L17_RESULTS = Path(os.environ.get("L17_RESULTS", tape.ROOT / "interim" / "l17")); L17_RESULTS.mkdir(parents=True, exist_ok=True)   # results: in the data folder, never committed
ONE_YEAR = os.environ.get("L17_ONE_YEAR")                                # a check: run the tape scripts on one year only
FIG = Path(os.environ.get("L17_FIG", HERE.parent / "figures")); FIG.mkdir(parents=True, exist_ok=True)
PREFIX = os.environ.get("L17_PREFIX", "nb_")                               # "nb_": the lecture's own figures are never overwritten
import tape, l16_buildup as L


T = pl.read_parquet(tape.ROOT / "interim" / "l16_buildup.parquet")
T = T.select(((pl.col("t").dt.epoch("s") - 1) // 86400).alias("day"), (pl.col("2 + re-posted entry") * 100).alias("r")).group_by("day").agg(pl.col("r").sum().alias("trend"))
tc = L.H["t_close"].dt.epoch("s").to_numpy(); fc = np.nan_to_num(L.FC)
G = pl.read_parquet(L17_RESULTS / "l17_directions.parquet").filter(pl.col("rule").is_in(["vol switch (base)", "skew, sign"]) & pl.col("step").is_in([50, 100, 200]))
G = G.select(pl.col("day").cast(pl.Int64), "rule", "step", "net", "year").join(T, on="day")
d0 = G["day"].to_numpy() * 86400; i = np.searchsorted(tc, d0, side="right") - 1
G = G.with_columns(pl.Series("f", np.abs(fc[np.maximum(i, 0)])), pl.when(pl.col("year") <= 2024).then(pl.lit("2021-24")).otherwise(pl.lit("2025-26")).alias("p"))
cuts = np.quantile(G.filter(pl.col("p") == "2021-24").unique("day")["f"].to_numpy(), [1 / 3, 2 / 3])
G = G.with_columns(pl.col("f").cut(list(cuts), labels=["flat", "medium", "strong"]).cast(pl.Utf8).alias("trend_size"))
sr = lambda x: float(np.mean(x) / np.std(x) * np.sqrt(365))
out = []
for (rule, step, p), d in G.group_by("rule", "step", "p"):
    g, t = d["net"].to_numpy(), d["trend"].to_numpy(); rho = float(np.corrcoef(g, t)[0, 1]); gs = g / g.std() * t.std()
    rec = dict(rule=rule, step=step, p=p, sr_trend=sr(t), sr_grid=sr(g), rho=rho, needed=sr(g) / sr(t), w10=sr(0.9 * t + 0.1 * gs), w25=sr(0.75 * t + 0.25 * gs))
    for k, e in d.group_by("trend_size"):
        rec[f"grid_{k[0]}"] = e["net"].mean(); rec[f"se_{k[0]}"] = e["net"].std() / np.sqrt(len(e)); rec[f"trend_{k[0]}"] = e["trend"].mean()
    out.append(rec)
O = pl.DataFrame(out).sort("rule", "step", "p")
(L17_RESULTS / "l17_s6.json").write_text(json.dumps(O.to_dicts(), indent=1))
pl.Config.set_tbl_rows(30); pl.Config.set_tbl_width_chars(250); pl.Config.set_tbl_cols(20); pl.Config.set_float_precision(3)
print(O.select("rule", "step", "p", "sr_trend", "sr_grid", "rho", "needed", "w10", "w25"))
print(O.select("rule", "step", "p", "grid_flat", "se_flat", "grid_medium", "grid_strong", "se_strong", "trend_flat", "trend_strong"))
