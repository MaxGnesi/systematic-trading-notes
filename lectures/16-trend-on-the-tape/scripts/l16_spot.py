"""Lecture 16 §6: the rule of §2 (plain sizing, patient entry) with its longs held in the perpetual or in spot (no funding; 10 bp spot fee on long trades;
the cash tied up forgoes the T-bill rate); shorts in the perpetual. Settings of l16_buildup.py."""
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

fc = B.forecast(B.dp_sd, [1, 2, 3]); R = {}
for lab, spot in (("longs in the perpetual", False), ("longs in spot", True)):
    net, parts = B.simulate(B.sig_plain, B.TAKER + B.HALF - B.REPOST_SAVING, spot, fc=fc)
    R[lab] = {"2021-2024": B.stats(net, parts, B.IS & B.live), "2025-2026": B.stats(net, parts, ~B.IS)}
(L16_RESULTS / "l16_spot.json").write_text(json.dumps(R, indent=1))
for k, v in R.items():
    a, z = v["2021-2024"], v["2025-2026"]
    print(f"{k:24} {a['sharpe']:+.2f}/{z['sharpe']:+.2f} costs {a['cost']:.1%}/{z['cost']:.1%} funding {a['funding']:+.1%}/{z['funding']:+.1%} lost interest {a['carry']:.1%}/{z['carry']:.1%}")
