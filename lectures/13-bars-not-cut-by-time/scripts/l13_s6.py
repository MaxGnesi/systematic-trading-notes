"""Lecture 13 §6: imbalance bars. López de Prado's construction (2018, §2.3.2.1) against a fixed-band version, on two three-month windows.

Both run on orders: consecutive trades in the same millisecond on the same side are one order (a sweep through many prices is one decision).
Signed flow of an order: + dollars if the aggressor bought, - dollars if it sold.

López de Prado (dollar imbalance bars): close when |theta| >= E[T] * |E[b v]|, theta = signed dollars since the bar opened,
  E[T] = EWMA of past bars' lengths (orders, span `span` bars), E[b v] = EWMA of signed dollars per order (window span x E[T] orders).
  Started from the past 28 days: E[T] = orders a day / 48, E[b v] = average signed dollars per order. No limits on anything.
Fixed band: close when |theta| >= h, h fixed for the day, h = K_IMB * K * sqrt(Q / 48), Q = median over the past W days of the day's
  sum of squared net signed dollars per 5 minutes (the variance of the flow, persistence included, as rv_300 for the range bar).
  Wald's identity: about Q / h^2 bars a day when flow is balanced; one-sided flow closes bars sooner (about h / |drift| orders).
  Minimum length m seconds: a bar can close only once it has lasted m seconds (bars merged, moves never cut).
Grid: K in 0.5..2, W in 14/28/56 days, m in 0/1/5/10/30 s. López de Prado: span 3/10/30."""
import json, sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import numpy as np, polars as pl
from numba import njit
import os, sys
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # tables print on any console; Jupyter handles its own
HERE = Path(__file__).resolve().parent                                     # lectures/13-.../scripts
sys.path[:0] = [str(HERE), str(HERE.parents[1] / "12-tick-data-the-tape"), str(HERE.parents[2])]   # this folder, tape.py, trading_models
import tape
L13_RESULTS = tape.ROOT / "interim" / "l13"; L13_RESULTS.mkdir(parents=True, exist_ok=True)          # results: in the data folder, never committed
FIG = Path(os.environ.get("L13_FIG", HERE.parent / "figures")); FIG.mkdir(parents=True, exist_ok=True)
PREFIX = os.environ.get("L13_PREFIX", "nb_")                               # "nb_": the lecture's own figures are never overwritten
import tape

SYM = "BTCUSDT"; N = 48
WINDOWS = {"stress": (date(2022, 8, 1), date(2022, 10, 31)), "calm": (date(2023, 1, 1), date(2023, 3, 31))}
KS = (0.5, 0.71, 1.0, 1.41, 2.0); WS = (14, 28, 56); MS = (0, 1, 5, 10, 30); SPANS = (3, 10, 30)
K_IMB = 0.85                                                         # the burn-in constant for the 5-minute variance (l13_s6_horizon.py, October to December 2021)
MAX_STORE = 5000                                                    # bars a day beyond which a day's bars are counted, not stored (a collapsed clock)
OUT = tape.ROOT / "interim" / "bars_s6" / SYM


@njit(cache=True)
def _band(s, t, h, m, S, t0):
    out = np.empty(len(s), np.int64); k = 0
    for i in range(len(s)):
        S += s[i]
        if abs(S) >= h and t[i] - t0 >= m:
            out[k] = i; k += 1; S = 0.0; t0 = t[i]
    return out[:k], S, t0


@njit(cache=True)
def _ldp(s, S, n, ET, Ebv, span):
    out = np.empty(len(s), np.int64); k = 0; ab = 2.0 / (span + 1.0)
    for i in range(len(s)):
        S += s[i]; n += 1
        a = 2.0 / (span * ET + 1.0); Ebv += a * (s[i] - Ebv)
        if abs(S) >= ET * abs(Ebv):
            out[k] = i; k += 1
            ET += ab * (n - ET); S = 0.0; n = 0
    return out[:k], S, n, ET, Ebv


def load_orders(d0):
    a = int(datetime(d0.year, d0.month, d0.day, tzinfo=timezone.utc).timestamp() * 1000)
    t = (pl.scan_parquet(tape.source(SYM, d0.strftime("%Y-%m"))).filter(pl.col("transact_time").is_between(a, a + 86_400_000, closed="left"))
           .select("transact_time", "price", "quantity", "is_buyer_maker").collect())
    side = np.where(t["is_buyer_maker"].to_numpy(), -1, 1); tm = t["transact_time"].to_numpy()
    new = np.r_[True, (tm[1:] != tm[:-1]) | (side[1:] != side[:-1])]; oid = np.cumsum(new) - 1
    usd = (t["price"] * t["quantity"]).to_numpy()
    o_usd = np.bincount(oid, usd); last = np.r_[np.nonzero(new)[0][1:] - 1, len(tm) - 1]
    return dict(t=tm[last], p=t["price"].to_numpy()[last], u=o_usd, s=o_usd * side[last], trades=len(tm))


def q5(o):
    b = (o["t"] - o["t"][0] // 86_400_000 * 86_400_000) // 300_000
    return float(np.sum(np.bincount(b, o["s"]) ** 2))


class Clock:
    """Bars of one variant: end time, close, dollars, signed dollars, orders; the unfinished bar carried across days."""
    def __init__(self, name): self.name = name; self.st = None; self.pu = self.ps = self.pn = 0.0; self.rows = []; self.count = {}; self.prev_end = None
    def add(self, d0, x, ends):
        CU = self.pu + np.cumsum(x["u"]); CS = self.ps + np.cumsum(x["s"]); CN = self.pn + np.arange(1, len(x["u"]) + 1)
        self.count[d0.isoformat()] = int(len(ends))
        if len(ends):
            u = np.diff(np.r_[0.0, CU[ends]]); s = np.diff(np.r_[0.0, CS[ends]]); n = np.diff(np.r_[0.0, CN[ends]])
            if len(ends) <= MAX_STORE:
                self.rows.append(pl.DataFrame({"end_ms": x["t"][ends], "close": x["p"][ends], "usd": u, "signed_usd": s, "orders": n}))
            self.pu, self.ps, self.pn = CU[-1] - CU[ends[-1]], CS[-1] - CS[ends[-1]], CN[-1] - CN[ends[-1]]
        else:
            self.pu, self.ps, self.pn = CU[-1], CS[-1], CN[-1]


def run(wname, start, end):
    first = start - timedelta(days=max(WS)); days = [first + timedelta(days=i) for i in range((end - first).days + 1)]
    hist = []                                                       # per day: orders, sum of squared order dollars, signed dollars
    band = {(k, w, m): Clock(f"band_K{k}_W{w}_m{m}") for k in KS for w in WS for m in MS}; ldp = {sp: Clock(f"ldp_span{sp}") for sp in SPANS}
    S_band = {key: (0.0, 0) for key in band}
    for d0 in days:
        tape.wait_for_memory(2.0)
        o = load_orders(d0)
        if d0 >= start:
            H = pl.DataFrame(hist, schema=["n", "q", "s"], orient="row")
            for (k, w, m), c in band.items():
                h = K_IMB * k * np.sqrt(float(H["q"].tail(w).median()) / N)
                ends, *st = _band(o["s"], o["t"], h, m * 1000, *S_band[(k, w, m)]); S_band[(k, w, m)] = tuple(st); c.add(d0, o, ends)
            for sp, c in ldp.items():
                if c.st is None: c.st = (0.0, 0, float(H["n"].tail(28).median()) / N, float(H["s"].tail(28).sum() / H["n"].tail(28).sum()))
                ends, *st = _ldp(o["s"], *c.st, float(sp)); c.st = tuple(st); c.add(d0, o, ends)
        hist.append((len(o["u"]), q5(o), float(o["s"].sum())))
        if d0 >= start: print(wname, d0, "orders", len(o["u"]), "ldp10 bars", ldp[10].count[d0.isoformat()] if 10 in ldp else "-",
                              "band K1 W28", band[(1.0, 28, 0)].count[d0.isoformat()], tape.peak_private_gb(), "GB", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    res = {}
    for c in list(band.values()) + list(ldp.values()):
        if c.rows: pl.concat(c.rows).write_parquet(OUT / f"{wname}_{c.name}.parquet")
        res[c.name] = dict(bars_per_day=c.count, last_state=[float(v) for v in c.st] if c.st else None)
    res["_days"] = dict(orders=[h[0] for h in hist[-len([d for d in days if d >= start]):]], trades_note="orders = same-ms same-side trades merged")
    return res


if __name__ == "__main__":
    R = {w: run(w, *WINDOWS[w]) for w in WINDOWS}
    (L13_RESULTS / "l13_s6_raw.json").write_text(json.dumps(R))
