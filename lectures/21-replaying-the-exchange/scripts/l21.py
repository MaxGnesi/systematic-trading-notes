"""Settings shared by the Lecture 21 scripts. Environment variables: BYBIT_ROOT, the Bybit data folder of Lecture 18 (default: data/bybit at the
top of the repository), whose parquet/ holds the converted book and trades; L19_OUT, where Lecture 19 wrote its results (default:
BYBIT_ROOT/interim/l19), read here: the book state after every update; L21_OUT, where results are written (default: BYBIT_ROOT/interim/l21);
L21_PREFIX, put before the names of the figures (the notebook uses nb_, so that the lecture's own figures are never overwritten). Results are
read from L21_OUT if there, otherwise from results/ next to this folder: the results shipped with the lecture."""
import os, sys
from pathlib import Path
import numpy as np, polars as pl, pyarrow.parquet as pq

LECTURE = Path(__file__).resolve().parents[1]; REPO = LECTURE.parents[1]
sys.path.insert(0, str(REPO))
SYM = "BTCUSDT"
ROOT = Path(os.environ.get("BYBIT_ROOT", REPO / "data" / "bybit"))
PARQUET = ROOT / "parquet"; BOOK, TRADES = PARQUET / "orderbook" / SYM, PARQUET / "trades" / SYM
STATE = Path(os.environ.get("L19_OUT", ROOT / "interim" / "l19")) / "state"
OUT = Path(os.environ.get("L21_OUT", ROOT / "interim" / "l21"))
KEY = OUT / "key"
for p in (KEY,): p.mkdir(parents=True, exist_ok=True)
RESULTS, FIG = LECTURE / "results", LECTURE / "figures"
PREFIX = os.environ.get("L21_PREFIX", "")
TICK = 0.1                                                                         # dollars per tick
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8")


def result_path(folder, name):
    """A result file: the one computed here (folder/name) if it exists, otherwise the one shipped with the lecture (results/<folder>/name)."""
    p = folder / name
    return p if p.exists() else RESULTS / folder.name / name


def ms(day, hms="00:00:00"):
    return int(np.datetime64(f"{day}T{hms}", "ms").astype(np.int64))


def window(day, t_a, t_b, side=1):
    """The book updates of one side between t_a and t_b (ms, engine time cts), the trades and Lecture 19's book state in the same window.
    Only the row groups that cover the window are read. Each book update gives the new size at its price (0: the level is gone)."""
    f = pq.ParquetFile(BOOK / f"{day}.parquet"); m = f.metadata
    rgs = [i for i in range(m.num_row_groups) if m.row_group(i).column(1).statistics.max >= t_a and m.row_group(i).column(1).statistics.min <= t_b]
    B = pl.from_arrow(f.read_row_groups(rgs, columns=["cts", "side", "tick", "size"])).filter(
        pl.col("cts").is_between(t_a, t_b) & (pl.col("side") == side)).drop("side")
    T = pl.scan_parquet(TRADES / f"{day}.parquet").select("ts", "side", "tick", "size").filter(pl.col("ts").is_between(t_a, t_b)).collect()
    S = pl.scan_parquet(STATE / f"{day}.parquet").filter(pl.col("ts").is_between(t_a, t_b)).collect()
    return B, T, S


class Bid:
    """A resting buy order of size S posted at the best bid that stands at t0 + L, held without re-posting for HOLD ms. Fill times under the
    three rules of the lecture: Q0, touch (the first seller-initiated trade at or through our price); Q1, trade-through (the first trade below our
    price); Q2, queue (we join behind the displayed size; trades at our price reduce the size ahead; a decrease of the level beyond those trades is
    a cancellation, a share x^a of it ahead of us, x = ahead / (ahead + behind), the rest behind us, except that no more can be cancelled
    behind us than stands there; trades at our price beyond the size ahead fill us; a trade below
    our price fills what is left). Trades between two book updates are applied before the update."""

    def __init__(self, B, T, S, t0, L=50, size=0.001, a=1.0, hold=120_000):
        st = S["ts"].to_numpy(); i = int(np.searchsorted(st, t0 + L, "right")) - 1
        self.t0, self.ta, self.p = t0, t0 + L, int(S["bid"][i])
        bc, btk, bsz = (B[c].to_numpy() for c in ("cts", "tick", "size"))
        lv = np.nonzero(btk == self.p)[0]; k0 = np.searchsorted(bc[lv], self.ta, "right") - 1
        self.ok = k0 >= 0
        if not self.ok: return
        self.q = float(bsz[lv[k0]])                                                # displayed size when we join
        ups = lv[k0 + 1:]; ups = ups[bc[ups] <= self.ta + hold]
        tt, ts_, tk, tz = (T[c].to_numpy() for c in ("ts", "side", "tick", "size"))
        tr = np.nonzero((tt > self.ta) & (tt <= self.ta + hold) & (ts_ == -1) & (tk <= self.p))[0]
        self.q0 = int(tt[tr[0]]) if len(tr) else None
        thr = [j for j in tr if tk[j] < self.p]; self.q1 = int(tt[thr[0]]) if thr else None
        self.q2 = None; V, qlev, tsum = self.q, self.q, 0.0; path = [(self.ta, V, qlev)]
        for t, kind, j in sorted([(tt[j], 0, j) for j in tr] + [(bc[u], 1, u) for u in ups]):
            if kind == 0:
                if tk[j] < self.p or tz[j] > V: self.q2 = int(t); break
                V -= tz[j]; tsum += tz[j]
            else:
                new = float(bsz[j]); d = qlev - tsum - new
                if d > 0:                                                          # a cancellation: a share x^a ahead of us, the rest behind,
                    x = min(V / max(qlev - tsum, 1e-12), 1.0)                      # but no more behind us than stands there; the excess
                    behind = (1 - x ** a) * d if a != np.inf else d                # was ahead of us
                    behind = min(behind if x < 1 else 0.0, qlev - tsum - V)
                    V = max(V - (d - behind), 0.0)
                qlev, tsum = new, 0.0
            path.append((int(t), V, qlev))
        self.path = path                                                           # (time, size ahead of us, displayed size) under Q2
