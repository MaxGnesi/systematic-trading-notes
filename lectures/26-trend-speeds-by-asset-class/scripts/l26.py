"""Settings and helpers shared by the Lecture 26 scripts. Markets, classes and data come from Lecture 25 (scripts/l25.py: PORTFOLIO_DATA).
L26_OUT: where the daily streams are written (default PORTFOLIO_DATA/l26); L26_RESULTS: summaries (default results/ next to this folder);
L26_PREFIX: put before figure names."""
import os, sys
from pathlib import Path
import numpy as np, pandas as pd

LECTURE = Path(__file__).resolve().parents[1]; REPO = LECTURE.parents[1]
sys.path.insert(0, str(REPO / "lectures" / "25-choosing-the-markets" / "scripts")); import l25 as L25
sys.path.insert(0, str(REPO)); from trading_models.momentum import donchian_state, past_return

RESULTS = Path(os.environ.get("L26_RESULTS", LECTURE / "results")); FIG = LECTURE / "figures"; RESULTS.mkdir(parents=True, exist_ok=True)
OUT = Path(os.environ.get("L26_OUT", L25.DATA / "l26")); OUT.mkdir(parents=True, exist_ok=True)
PREFIX = os.environ.get("L26_PREFIX", "")
CLASS, CLASSES, FLOOR = L25.CLASS, L25.CLASSES, L25.FLOOR

SPEEDS = (11, 17, 23, 31, 43, 61, 89, 127, 179, 251, 359, 503)              # trading days, primes about sqrt(2) apart (hypotheses.md)
RULES = ("ewma", "breakout", "return")
STREAMS = [f"{r}_{h}" for r in RULES for h in SPEEDS]                     # 36 streams per market
VOL_TARGET, LAMBDA, COST_BP = 0.10, 0.10, 5.0                              # cost per unit of value traded, bp (10 and 20 reported)
VOL_SPAN = int(os.environ.get("L26_VOL_SPAN", 126)) or None             # six months (the rule); 0: each stream's own speed; 36: the first version
START = "2007-01-01"
RATE = L25.DATA / "DTB3.csv"                                                # 3-month bill rate, FRED (l26_fetch_rate.py)


def load_daily():
    """Daily adjusted close, high, low and dollar volume of the Lecture 25 ETFs (total-return prices), and the daily cash return."""
    raw = pd.read_csv(L25.RAW, header=[0, 1], index_col=0, parse_dates=True)
    close = raw["Close"]; keep = [t for t in close.columns if close[t].notna().any()]
    rf = pd.read_csv(RATE, index_col=0, parse_dates=True).iloc[:, 0]
    rf = pd.to_numeric(rf, errors="coerce").reindex(close.index).ffill() / 100 / 252                 # yearly percent to a daily rate, trading days
    return close[keep], raw["High"][keep], raw["Low"][keep], (close * raw["Volume"])[keep], rf


def excess(close, high, low, rf):
    """Excess-return price index (total return less cash, as a futures position earns), with high and low scaled by the same daily factor."""
    r = close.pct_change() - rf.reindex(close.index)
    idx = (1 + r.fillna(0.0)).cumprod() * close.iloc[0]; f = idx / close
    return idx, high * f, low * f


def signals(close, high, low, h):
    """The three rules at horizon h, each +1/-1 (breakout also 0 when flat), known at the close of day t."""
    lp = np.log(close)
    ewma = np.sign(lp.ewm(span=max(h // 4, 2), min_periods=h).mean() - lp.ewm(span=h, min_periods=h).mean())
    brk = donchian_state(high, low, close, entry=h, exit_=max(h // 2, 2))
    ret = np.sign(past_return(close, h))
    return {"ewma": ewma, "breakout": brk, "return": ret}


def stream_returns(close, high, low):
    """Call with excess-return prices (excess()), so that signals and profits are both over cash."""
    """Daily gross returns (g_*) and value traded (t_*) of the 36 streams for one market (Series inputs): position = sign x 10% / six-month volatility,
    partial trading lambda = 0.1, traded at the close; the position held over day t+1 earns that day's return; net() charges the cost."""
    c, hi, lo = close.to_frame("x"), high.to_frame("x"), low.to_frame("x")
    r = close.pct_change()
    out = {}
    for h in SPEEDS:
        span = VOL_SPAN if VOL_SPAN else h                                     # risk measured over the stream's own speed (VOL_SPAN = None)
        vol = np.sqrt((r ** 2).ewm(span=span, min_periods=min(span, 60)).mean() * 252)
        sig = signals(c, hi, lo, h)
        for name, s in sig.items():
            target = (s["x"] * VOL_TARGET / vol).fillna(0.0).to_numpy()
            pos = np.zeros_like(target)
            for t in range(1, len(target)): pos[t] = pos[t - 1] + LAMBDA * (target[t] - pos[t - 1])
            pos = pd.Series(pos, close.index); trade = pos.diff().abs().fillna(0.0)
            out[f"g_{name}_{h}"] = (pos.shift(1) * r).astype("float32"); out[f"t_{name}_{h}"] = trade.astype("float32")
    return pd.DataFrame(out)


def net(S, cost_bp=COST_BP):
    """Net daily returns of the 36 streams from a stored frame of gross returns (g_*) and trades (t_*)."""
    return pd.DataFrame({k: S[f"g_{k}"] - cost_bp / 1e4 * S[f"t_{k}"] for k in STREAMS})


def sharpe(x):
    x = x.dropna(); return float(x.mean() / x.std() * np.sqrt(252)) if len(x) > 20 and x.std() > 0 else np.nan
