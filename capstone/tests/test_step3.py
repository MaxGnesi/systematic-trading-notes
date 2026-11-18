"""Step 3 tests, no network: settings checks, the take profit, and the backtest's inverse accounting.
Run: python -m capstone.tests.test_step3"""
from pathlib import Path

import numpy as np
import pandas as pd

from capstone.backtest import engine
from capstone.strategies.trend import params as P
from capstone.strategies.trend.signal import take_profit


def test_params_load_and_reject(tmp=Path(__file__).resolve().parents[1] / "data"):
    p = P.load()
    assert p.fast_spans_days == (2.0, 7.0) and p.decision_minute == 23 and p.execution == "taker"
    tmp.mkdir(exist_ok=True)
    bad = tmp / "_bad_params.toml"
    for old, new in [("target_vol = 0.10", "target_vol = 0.9"), ("sigmas = 5.0", "sigmaz = 5.0"), ('mode = "taker"', 'mode = "maker"')]:
        bad.write_text(P.FILE.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")
        try:
            P.load(bad); raise AssertionError(f"accepted: {new}")
        except P.ParamsError:
            pass
    bad.unlink()


def test_take_profit_hand_case():
    f = np.array([1.0] * 12 + [-1.0, -1.0]); r = np.array([np.nan] + [0.01] * 13); v = np.full(14, 0.01)
    out, flat = take_profit(f, r, v, fast_h=4, sigmas=5)     # unit 0.01 x 2 = 0.02; 5 sigma = 10% gain
    assert flat.tolist().index(True) == 10, "flat from the hour the gain reaches 10%"
    assert out[11] == 0 and out[12] == -1, "flat until the sign changes, then trades again"


def test_inverse_accounting():
    idx = pd.date_range("2024-01-01 00:23", periods=3, freq="h", tz="UTC")
    prices = [50000.0, 50000.0, 55000.0]
    h = pd.DataFrame({"price": prices, "close0": prices, "close1": prices, "low0": prices, "high0": prices, "funding": 0.0}, index=idx)
    p = P.load().replace(buffer=0.0, jitter_seconds=0)
    tx = np.array([0.2, 0.2, np.nan])                         # 0.2 x 1 BTC x 50,000 = 10,000 USD long; no trade in the last hour
    res = engine.run(h, p, tx_override=tx)
    fill = 50000 + engine.TICK / 2                            # a buy pays half a tick
    fee = 10000 * engine.TAKER / fill
    spread = 10000 * (1 / fill - 1 / 50000)                   # negative: bought above the mark
    pnl = 10000 * (1 / 50000 - 1 / 55000)                     # inverse: amount x (1/before - 1/after) = 0.0181818 BTC
    assert res.hourly["position"].iloc[0] == 10000
    assert abs(res.hourly["equity"].iloc[2] - (1 - fee + spread + pnl)) < 1e-12

if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn(); print("ok", name)
