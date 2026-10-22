"""López de Prado's bars from different starting values: two weeks of September 2022, bars per day at the end."""
import sys
from datetime import date, timedelta
from pathlib import Path
import numpy as np
import os, sys
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # tables print on any console; Jupyter handles its own
HERE = Path(__file__).resolve().parent                                     # lectures/13-.../scripts
sys.path[:0] = [str(HERE), str(HERE.parents[1] / "12-tick-data-the-tape"), str(HERE.parents[2])]   # this folder, tape.py, trading_models
import tape
L13_RESULTS = tape.ROOT / "interim" / "l13"; L13_RESULTS.mkdir(parents=True, exist_ok=True)          # results: in the data folder, never committed
FIG = Path(os.environ.get("L13_FIG", HERE.parent / "figures")); FIG.mkdir(parents=True, exist_ok=True)
PREFIX = os.environ.get("L13_PREFIX", "nb_")                               # "nb_": the lecture's own figures are never overwritten
import l13_s6 as m
days = [date(2022, 9, 5) + timedelta(days=i) for i in range(14)]
O = [m.load_orders(d) for d in days]
n0 = len(O[0]["u"]) / 48; s_abs = np.mean(np.abs(O[0]["s"]))
for ET0 in (n0 / 10, n0, n0 * 10, 20000):
    for frac in (0.001, 0.01, 0.1, 0.5):
        st = (0.0, 0, ET0, frac * s_abs); per = []
        for o in O:
            e, *st = m._ldp(o["s"], *st, 10.0); per.append(len(e))
        print(f"E[T] start {ET0:8.0f} orders, E[bv] start {frac:5} x mean |order|: bars/day first {per[0]:7} last {per[-1]:7}  E[T] end {st[2]:10.1f}")
