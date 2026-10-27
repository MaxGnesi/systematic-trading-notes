"""Lecture 16 §2: the plain rule with the plateau speeds blended (fast spans 1, 2 and 3 days, equal weights), settings of l16_buildup.py."""
import json, sys
from pathlib import Path
import os, sys
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # tables print on any console; Jupyter handles its own
HERE = Path(__file__).resolve().parent                                     # lectures/16-.../scripts
sys.path[:0] = [str(HERE), str(HERE.parents[1] / "13-bars-not-cut-by-time" / "scripts"), str(HERE.parents[1] / "12-tick-data-the-tape"), str(HERE.parents[2])]
import tape
L16_RESULTS = tape.ROOT / "interim" / "l16"; L16_RESULTS.mkdir(parents=True, exist_ok=True)          # results: in the data folder, never committed
FIG = Path(os.environ.get("L16_FIG", HERE.parent / "figures")); FIG.mkdir(parents=True, exist_ok=True)
PREFIX = os.environ.get("L16_PREFIX", "nb_")                               # "nb_": the lecture's own figures are never overwritten
import l16_buildup as B

net, parts = B.simulate(B.sig_plain, B.TAKER + B.HALF, False, fc=B.forecast(B.dp_sd, [1, 2, 3]))
R = {"2021-2024": B.stats(net, parts, B.IS & B.live), "2025-2026": B.stats(net, parts, ~B.IS)}
(L16_RESULTS / "l16_blend.json").write_text(json.dumps(R, indent=1)); print(json.dumps(R, indent=1))
