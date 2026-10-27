"""Lecture 16 §7: the rule built up, and its alternatives, all with the settings of l16_buildup.py. Steps: 0 the plain rule of §2 (market orders);
1 + the patient entry of §5 (the lecture's rule); 1x longs in spot (§6, not taken). Alternatives to the lecture's rule: sizing by the smoothed risk
forecast (§4); long or flat. Year by year: the long and short legs of the lecture's rule and of long-or-flat, and bitcoin. Equity lines for the
lecture's rule, long-or-flat and bitcoin held long scaled to the rule's volatility. Capacity: the rule's trades (count, typical size) for §7."""
import json, sys
from pathlib import Path
import numpy as np, polars as pl
import os, sys
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # tables print on any console; Jupyter handles its own
HERE = Path(__file__).resolve().parent                                     # lectures/16-.../scripts
sys.path[:0] = [str(HERE), str(HERE.parents[1] / "13-bars-not-cut-by-time" / "scripts"), str(HERE.parents[1] / "12-tick-data-the-tape"), str(HERE.parents[2])]
import tape
L16_RESULTS = tape.ROOT / "interim" / "l16"; L16_RESULTS.mkdir(parents=True, exist_ok=True)          # results: in the data folder, never committed
FIG = Path(os.environ.get("L16_FIG", HERE.parent / "figures")); FIG.mkdir(parents=True, exist_ok=True)
PREFIX = os.environ.get("L16_PREFIX", "nb_")                               # "nb_": the lecture's own figures are never overwritten
import l16_buildup as B

FC = B.forecast(B.dp_sd, [1, 2, 3]); PAT = B.TAKER + B.HALF - B.REPOST_SAVING; MKT = B.TAKER + B.HALF
LF = np.where(np.isfinite(FC), np.maximum(FC, 0.0), np.nan)
V = {"0 plain rule, market orders": (B.sig_plain, MKT, False, FC), "1 + patient entry (the lecture's rule)": (B.sig_plain, PAT, False, FC),
     "1x longs held in spot": (B.sig_plain, PAT, True, FC), "alternative: sizing by the smoothed risk forecast": (B.sig_smooth, PAT, False, FC),
     "alternative: long or flat": (B.sig_plain, PAT, False, LF)}
R = {"variants": {}, "by_year": {}}; series = {}
year = B.H["t_close"].dt.year().to_numpy()
for lab, (sig, cb, spot, fc) in V.items():
    net, parts = B.simulate(sig, cb, spot, fc=fc); series[lab] = net
    R["variants"][lab] = {"2021-2024": B.stats(net, parts, B.IS & B.live), "2025-2026": B.stats(net, parts, ~B.IS)}
    if lab in ("1 + patient entry (the lecture's rule)", "alternative: long or flat"):
        pos = parts["pos"]; held = np.r_[0.0, pos[:-1]]; prev = held
        cl = np.abs(np.maximum(pos, 0) - np.maximum(prev, 0)) * cb / 1e4; cs = np.abs(np.minimum(pos, 0) - np.minimum(prev, 0)) * cb / 1e4
        longn = np.where(held > 0, parts["gross"] - parts["funding"], 0.0) - cl; shortn = np.where(held < 0, parts["gross"] - parts["funding"], 0.0) - cs
        R["by_year"][lab] = {int(y): dict(long=round(float(longn[(year == y) & B.live].sum()), 3), short=round(float(shortn[(year == y) & B.live].sum()), 3),
                                          rule=round(float(net[(year == y) & B.live].sum()), 3)) for y in range(2022, 2027)}
        if lab.startswith("1 +"):
            d = np.abs(np.diff(np.r_[0.0, pos])); tr = d[B.live & (d > 0)]
            R["trades"] = dict(per_year=round(float(len(tr) / (B.live.sum() / B.PY)), 0), median_size=round(float(np.median(tr)), 3), mean_size=round(float(tr.mean()), 3),
                               turnover_per_year=round(float(tr.sum() / (B.live.sum() / B.PY)), 1), gross_per_unit_traded_bp=round(float(parts["gross"][B.IS & B.live].sum() / d[B.IS & B.live].sum() * 1e4), 1),
                               mean_abs_position=round(float(np.abs(pos[B.live]).mean()), 2))
R["bitcoin_by_year"] = {int(y): round(float(np.log(B.p[(year == y) & B.live][-1] / B.p[(year == y) & B.live][0])), 3) for y in range(2022, 2027)}
(L16_RESULTS / "l16_s7.json").write_text(json.dumps(R, indent=1))
rule = series["1 + patient entry (the lecture's rule)"]; m = B.live
btc = B.r * (rule[m].std() / B.r[m].std())                                     # bitcoin held long, scaled to the rule's volatility
pl.DataFrame({"t": B.H["t_close"], "rule": rule, "long_or_flat": series["alternative: long or flat"], "smoothed": series["alternative: sizing by the smoothed risk forecast"],
              "btc_scaled": btc}).filter(pl.Series(m)).write_parquet(B.tape.ROOT / "interim" / "l16_s7_series.parquet")
for k, v in R["variants"].items():
    a, z = v["2021-2024"], v["2025-2026"]
    print(f"{k:52} {a['sharpe']:+.2f}/{z['sharpe']:+.2f} maxdd {a['maxdd']:+.1%}/{z['maxdd']:+.1%} worst day {a['worst_day']:+.1f} costs {a['cost']:.1%} funding {a['funding']:+.1%}")
print(R["trades"]); print(R["by_year"]); print(R["bitcoin_by_year"])
