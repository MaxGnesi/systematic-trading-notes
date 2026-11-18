"""The backtest (Lecture 24 §10): the strategy's own decisions, replayed hour by hour on Deribit's history.

The account is kept as the testnet account is: equity in BTC (the contract is inverse: amounts in USD,
profit and loss in BTC), starting at 1 BTC. Each hour, at `decision_minute` past the hour:
  1. the signal is read from the hourly closes so far (strategies/trend/signal.py, the live bot's code);
  2. the target in USD = target_x_equity x equity in BTC x price; trade only beyond the buffer, in whole
     contracts of 10 USD;
  3. the order is filled after the random delay, at the close of the minute in which the delay ends,
     plus half a tick against us, and pays the taker fee (or the maker fee, for the patient rival);
  4. profit and loss from one fill to the next, in BTC: amount x (1/price_before - 1/price_after);
     funding each hour as Deribit recorded it.
Only the past is used at each hour. Drawdowns are reported, not acted on: the strategy has no drawdown stop.
The hard limit on the position (`max_position_x_equity`) is applied, as live.
"""
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from capstone.strategies.trend.params import Params
from capstone.strategies.trend.signal import targets

HIST = Path(__file__).resolve().parents[1] / "data" / "history"
TAKER, MAKER, TICK, CONTRACT = 0.00035, 0.00015, 0.5, 10.0     # Deribit BTC-PERPETUAL, checked live 18 Nov 2026


def load_minutes() -> pd.DataFrame:
    files = sorted(HIST.glob("candles_1m_*.parquet"))
    if not files:
        raise FileNotFoundError("no history: run python -m capstone.backtest.download first")
    c = pd.concat([pd.read_parquet(f) for f in files]).drop_duplicates("ts").sort_values("ts")
    c.index = pd.to_datetime(c.ts, unit="ms", utc=True)
    f = pd.concat([pd.read_parquet(x) for x in sorted(HIST.glob("funding_1h_*.parquet"))]).drop_duplicates("ts").sort_values("ts")
    f.index = pd.to_datetime(f.ts, unit="ms", utc=True)
    return c, f


def hourly_frame(c: pd.DataFrame, f: pd.DataFrame, minute: int) -> pd.DataFrame:
    """One row per decision hour: the signal price (close of the minute before the decision), the closes of
    the two minutes after it (fills), their lows and highs (patient rival), and the hour's funding."""
    m = c["close"]
    dec = m.index[(m.index.minute == (minute - 1) % 60)] + pd.Timedelta(minutes=1)   # decision times hh:mm:00
    h = pd.DataFrame(index=dec)
    h["price"] = m.reindex(dec - pd.Timedelta(minutes=1)).to_numpy()
    for k in (0, 1):
        t = dec + pd.Timedelta(minutes=k)
        h[f"close{k}"] = m.reindex(t).to_numpy()
        h[f"low{k}"] = c["low"].reindex(t).to_numpy(); h[f"high{k}"] = c["high"].reindex(t).to_numpy()
    # volatility ratio (Lecture 20 §12): the variance of the hour before the decision, from one-minute log
    # returns, over its median of the previous 672 hours (28 days); known at the decision
    lr2 = np.log(m).diff() ** 2
    hv = lr2.rolling("60min").sum().reindex(dec - pd.Timedelta(minutes=1))
    hv.index = dec
    h["vol_ratio"] = (hv / hv.rolling(672, min_periods=336).median().shift(1)).to_numpy()
    fund = f["interest_1h"].reindex(dec.floor("h"))
    h["funding"] = fund.fillna(0.0).to_numpy()
    return h.dropna(subset=["price", "close0", "close1"])


@dataclass
class Result:
    hourly: pd.DataFrame          # equity, position, trades, costs per hour
    stats: dict


def run(h: pd.DataFrame, p: Params, rival: str = "base", x_bp: float = 0.0, seed: int = 7, tx_override=None,
        vol_switch: str = "off", vol_k: float = 2.0) -> Result:
    """`tx_override` (tests only): a fixed target, as a multiple of equity, instead of the strategy's."""
    sig = targets(h["price"], p) if tx_override is None else pd.DataFrame({"target_x_equity": tx_override}, index=h.index)
    rng = np.random.default_rng(seed)
    jitter_min = (rng.uniform(0, p.jitter_seconds, len(h)) // 60).astype(int).clip(0, 1)   # 0: first minute, 1: second
    price, c0, c1, lo0, hi0 = (h[k].to_numpy() for k in ("price", "close0", "close1", "low0", "high0"))
    fund, tx = h["funding"].to_numpy(), sig["target_x_equity"].to_numpy().copy()
    vr = h["vol_ratio"].to_numpy() if "vol_ratio" in h else np.full(len(h), np.nan)
    violent = vr >= vol_k
    if vol_switch == "flatten":
        tx[violent] = 0.0
    avg_abs = pd.Series(np.abs(tx)).expanding().mean().to_numpy()
    n = len(h)
    eq, pos, last_fill = 1.0, 0.0, np.nan
    rec = np.zeros((n, 7))       # equity, position, traded USD, fee BTC, funding BTC, fill price, maker flag
    for t in range(n):
        # profit and loss of the position held since the last fill, marked at this hour's first-minute close
        mark = c0[t]
        if pos != 0 and not np.isnan(last_fill):
            eq += pos * (1 / last_fill - 1 / mark)
            fcost = pos * fund[t] / mark
            eq -= fcost
        else:
            fcost = 0.0
        last_fill = mark
        traded = fee = 0.0; maker = 0
        if not np.isnan(tx[t]) and not (vol_switch == "pause" and violent[t]):
            target = tx[t] * eq * price[t]
            cap = p.max_position_x_equity * eq * price[t]          # hard limit, a guard against bugs
            target = max(-cap, min(cap, target))
            band = p.buffer * avg_abs[t] * eq * price[t]
            if abs(target - pos) > band:
                new = np.round(target / CONTRACT) * CONTRACT
                trade = new - pos
                if trade != 0:
                    side = np.sign(trade)
                    if rival == "patient":                   # post-only at the decision price; filled only if traded through
                        limit = price[t] - side * TICK / 2
                        if (side > 0 and lo0[t] < limit) or (side < 0 and hi0[t] > limit):
                            fill, rate, maker = limit, MAKER, 1
                        else:
                            fill, rate = c1[t] + side * TICK / 2, TAKER
                    elif rival == "window":                  # trade early if the price moved our way by x bp
                        favour = -side * (c0[t] / price[t] - 1) * 1e4
                        fill = (c0[t] if favour >= x_bp else c1[t]) + side * TICK / 2; rate = TAKER
                        maker = int(favour >= x_bp)          # here: 1 = traded early
                    else:                                    # market order after the random delay
                        fill, rate = (c0[t] if jitter_min[t] == 0 else c1[t]) + side * TICK / 2, TAKER
                    fee = abs(trade) * rate / fill
                    eq -= fee
                    eq += trade * (1 / fill - 1 / mark)       # the new contracts start at the fill, not the mark
                    pos, traded = new, trade
        rec[t] = (eq, pos, traded, fee, fcost, last_fill, maker)
    out = pd.DataFrame(rec, index=h.index, columns=["equity", "position", "traded", "fee", "funding", "mark", "flag"])
    out = out.join(sig[[c for c in sig if c.startswith("tp")]])
    return Result(out, summarise(out, p))


def summarise(o: pd.DataFrame, p: Params) -> dict:
    eq = o["equity"]
    r = eq.pct_change().dropna()
    live = o["position"].abs().cumsum() > 0
    r = r[live.reindex(r.index).fillna(False)]
    m = (1 + r).resample("ME").prod() - 1
    peak = eq.cummax(); dd = eq / peak - 1
    years = max((r.index[-1] - r.index[0]).total_seconds() / (365.25 * 86400), 1 / 365.25) if len(r) > 1 else 1 / 365.25
    if len(r) < 2 or r.std() == 0:
        return dict(sharpe=float('nan'), months=0)
    return dict(sharpe=float(r.mean() / r.std() * np.sqrt(24 * 365)), ann_return=float((eq.iloc[-1] / eq[live].iloc[0]) ** (1 / years) - 1),
                ann_vol=float(r.std() * np.sqrt(24 * 365)), max_drawdown=float(dd.min()), worst_month=float(m.min()),
                month_skew=float(m.skew()), fees_per_year=float(o["fee"].sum() / years), funding_per_year=float(o["funding"].sum() / years),
                hours_at_limit=0, months=int(len(m)))
