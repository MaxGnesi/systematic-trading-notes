"""Lecture 16 §4 checks, on the rule of §2 (fast spans 1, 2, 3 days blended; settings of l16_buildup.py). (1) The long and the short leg: the rule's
hourly result split by the sign of the position held, with its gross return, trading costs (each trade charged to the side it trades) and funding;
against holding bitcoin long. (2) Forecast quality: the next 24 hours' realised variance forecast by the plain 36-day volatility, the raw and the
smoothed next-day forecast, and the larger of the two (asymmetric), each scaled on 2021-2024 to the same average level; QLIKE, lower is better.
(3) The asymmetric sizing in the backtest, against the plain one."""
import json, sys
from pathlib import Path
import numpy as np
import os, sys
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # tables print on any console; Jupyter handles its own
HERE = Path(__file__).resolve().parent                                     # lectures/16-.../scripts
sys.path[:0] = [str(HERE), str(HERE.parents[1] / "13-bars-not-cut-by-time" / "scripts"), str(HERE.parents[1] / "12-tick-data-the-tape"), str(HERE.parents[2])]
import tape
L16_RESULTS = tape.ROOT / "interim" / "l16"; L16_RESULTS.mkdir(parents=True, exist_ok=True)          # results: in the data folder, never committed
FIG = Path(os.environ.get("L16_FIG", HERE.parent / "figures")); FIG.mkdir(parents=True, exist_ok=True)
PREFIX = os.environ.get("L16_PREFIX", "nb_")                               # "nb_": the lecture's own figures are never overwritten
import l16_buildup as B

PY = B.PY; IS, live = B.IS, B.live; n = B.n
FC = B.forecast(B.dp_sd, [1, 2, 3])
net, parts = B.simulate(B.sig_plain, B.TAKER + B.HALF, False, fc=FC)
pos = parts["pos"]; held = np.r_[0.0, pos[:-1]]; prev = np.r_[0.0, pos[:-1]]
# (1) legs; a trade's cost goes to the side it trades: the long side for changes of the long part of the position, the short side likewise
lp, sp, lpp, spp = np.maximum(pos, 0), np.minimum(pos, 0), np.maximum(prev, 0), np.minimum(prev, 0)
cost_long = np.abs(lp - lpp) * (B.TAKER + B.HALF) / 1e4; cost_short = np.abs(sp - spp) * (B.TAKER + B.HALF) / 1e4
L, S = held > 0, held < 0


def leg(mask, cost, m):
    g = np.where(mask, parts["gross"], 0.0); f = np.where(mask, parts["funding"], 0.0); x = g - f - cost
    yrs = m.sum() / PY
    return dict(share_of_time=round(float(mask[m].mean()), 3), gross=round(float(g[m].sum() / yrs), 4), costs=round(float(cost[m].sum() / yrs), 4),
                funding=round(float(f[m].sum() / yrs), 4), net=round(float(x[m].sum() / yrs), 4),
                sharpe_of_contribution=round(float(x[m].mean() / x[m].std() * np.sqrt(PY)), 2),
                hit_rate_hours=round(float((parts["gross"][m & mask] > 0).mean()), 3))


R = {"legs": {}}
for smp, m in (("2021-2024", IS & live), ("2025-2026", ~IS)):
    yrs = m.sum() / PY
    R["legs"][smp] = {"long": leg(L, cost_long, m), "short": leg(S, cost_short, m),
                      "bitcoin held long": round(float(B.r[m].sum() / yrs), 4), "rule, total": round(float(net[m].sum() / yrs), 4)}
# (2) forecast quality for the next 24 hours' variance (per hour)
fwd = np.full(n, np.nan); c = np.r_[0.0, np.cumsum(B.rv)]; fwd[:-24] = (c[25:] - c[1:-24]) / 24
sig_asym = np.fmax(B.sig_har, B.sig_smooth)
cands = {"plain: past 36 days": B.sig_plain, "next-day forecast, raw": B.sig_har, "next-day forecast, smoothed": B.sig_smooth, "asymmetric: larger of raw and smoothed": sig_asym}
ok = live & np.isfinite(fwd) & (fwd > 0) & np.all(np.array([np.isfinite(v) for v in cands.values()]), axis=0)
R["forecast"] = {}
for k, sg in cands.items():
    v = sg ** 2 / PY; scale = np.mean(fwd[ok & IS] / v[ok & IS]); v = v * scale                  # same average level as the target, set on 2021-2024
    R["forecast"][k] = {smp: round(float(np.mean(fwd[ok & m] / v[ok & m] - np.log(fwd[ok & m] / v[ok & m]) - 1)), 4) for smp, m in (("2021-2024", IS), ("2025-2026", ~IS))}
# (3) backtest with the asymmetric sizing
R["sizing"] = {}
for k in ("plain: past 36 days", "next-day forecast, smoothed", "asymmetric: larger of raw and smoothed"):
    nt, pt = B.simulate(cands[k], B.TAKER + B.HALF, False, fc=FC)
    R["sizing"][k] = {"2021-2024": B.stats(nt, pt, IS & live), "2025-2026": B.stats(nt, pt, ~IS)}
(L16_RESULTS / "l16_legs_risk.json").write_text(json.dumps(R, indent=1))
print(json.dumps(R["legs"], indent=1)); print(json.dumps(R["forecast"], indent=1))
for k, v in R["sizing"].items():
    a, z = v["2021-2024"], v["2025-2026"]
    print(f"{k:42} {a['sharpe']:+.2f}/{z['sharpe']:+.2f} worst day {a['worst_day']:+.1f} spread {a['vol_cv']:.2f} costs {a['cost']:.1%} | 2025-26 worst {z['worst_day']:+.1f} maxdd {z['maxdd']:+.1%}")
