"""Lecture 16: the long and short legs of the rule of §2 year by year (net of costs and funding, % of capital), with bitcoin's own return and the rule's
maximum drawdown in each year; and the long-or-flat version of the rule (the same forecast, no short positions) beside the full rule."""
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

FC = B.forecast(B.dp_sd, [1, 2, 3]); year = B.H["t_close"].dt.year().to_numpy()
out = {}
for lab, fc in (("long and short", FC), ("long or flat", np.where(np.isfinite(FC), np.maximum(FC, 0.0), np.nan))):
    net, parts = B.simulate(B.sig_plain, B.TAKER + B.HALF, False, fc=fc)
    pos = parts["pos"]; held = np.r_[0.0, pos[:-1]]; prev = held
    cl = np.abs(np.maximum(pos, 0) - np.maximum(prev, 0)) * (B.TAKER + B.HALF) / 1e4; cs = np.abs(np.minimum(pos, 0) - np.minimum(prev, 0)) * (B.TAKER + B.HALF) / 1e4
    longn = np.where(held > 0, parts["gross"] - parts["funding"], 0.0) - cl; shortn = np.where(held < 0, parts["gross"] - parts["funding"], 0.0) - cs
    rows = {}
    for y in range(2022, 2027):
        m = (year == y) & B.live
        w = np.cumsum(net[m]); dd = float((w - np.maximum.accumulate(w)).min())
        rows[y] = dict(long=round(float(longn[m].sum()), 3), short=round(float(shortn[m].sum()), 3), rule=round(float(net[m].sum()), 3),
                       bitcoin=round(float(np.log(B.p[m][-1] / B.p[m][0])), 3), maxdd=round(dd, 3))
    out[lab] = {"by_year": rows, "2021-2024": B.stats(net, parts, B.IS & B.live), "2025-2026": B.stats(net, parts, ~B.IS)}
(L16_RESULTS / "l16_legs_year.json").write_text(json.dumps(out, indent=1, default=str))
for lab, v in out.items():
    print(lab, "| Sharpe", v["2021-2024"]["sharpe"], "/", v["2025-2026"]["sharpe"], "| maxdd", v["2021-2024"]["maxdd"], "/", v["2025-2026"]["maxdd"], "| worst day", v["2021-2024"]["worst_day"], "| costs", v["2021-2024"]["cost"])
    for y, r in v["by_year"].items(): print("  ", y, r)
