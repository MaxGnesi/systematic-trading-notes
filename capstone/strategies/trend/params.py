"""Load and check the strategy's settings (Lecture 24 §8).

Values live in params.toml; the rules live here: the allowed range of every setting, checks between
settings, and rejection of unknown keys (a typo must not pass as a default). An invalid file stops the bot
with a clear message; nothing is ever clamped silently. Changing a value inside its range is a settings
edit; changing a range is a code change, made deliberately.
"""
import tomllib
from dataclasses import dataclass
from pathlib import Path

FILE = Path(__file__).resolve().parent / "params.toml"

RANGES = {  # (section, key): (type, low, high)
    ("signal", "fast_spans_days"): (list, 0.5, 21),
    ("signal", "slow_over_fast"): (float, 2, 8),
    ("signal", "dp_vol_span_days"): (float, 5, 90),
    ("size", "target_vol"): (float, 0.01, 0.40),
    ("size", "vol_window_days"): (float, 90, 366),
    ("size", "buffer"): (float, 0.0, 0.5),
    ("take_profit", "enabled"): (bool, None, None),
    ("take_profit", "sigmas"): (float, 2, 10),
    ("timing", "decision_minute"): (int, 0, 59),
    ("timing", "jitter_seconds"): (int, 0, 600),
    ("execution", "mode"): (str, ("taker", "patient"), None),
    ("kill_switch", "max_drawdown"): (float, 0.02, 0.5),
    ("kill_switch", "max_feed_silence_s"): (float, 5, 600),
}


class ParamsError(ValueError):
    pass


@dataclass(frozen=True)
class Params:
    instrument: str
    fast_spans_days: tuple
    slow_over_fast: float
    dp_vol_span_days: float
    target_vol: float
    vol_window_days: float
    buffer: float
    take_profit: bool
    tp_sigmas: float
    decision_minute: int
    jitter_seconds: int
    execution: str
    max_drawdown: float
    max_feed_silence_s: float

    def replace(self, **kw) -> "Params":
        d = {**self.__dict__, **kw}
        return Params(**d)


def _check(sec: str, key: str, v):
    typ, lo, hi = RANGES[(sec, key)]
    if typ is list:
        if not isinstance(v, list) or not v or not all(isinstance(x, (int, float)) and lo <= x <= hi for x in v):
            raise ParamsError(f"[{sec}] {key} must be a non-empty list of numbers from {lo} to {hi}, got {v!r}")
        return tuple(float(x) for x in v)
    if typ is bool:
        if not isinstance(v, bool):
            raise ParamsError(f"[{sec}] {key} must be true or false, got {v!r}")
        return v
    if typ is str:
        if v not in lo:
            raise ParamsError(f"[{sec}] {key} must be one of {lo}, got {v!r}")
        return v
    if not isinstance(v, (int, float)) or isinstance(v, bool) or not lo <= v <= hi:
        raise ParamsError(f"[{sec}] {key} must be a number from {lo} to {hi}, got {v!r}")
    return int(v) if typ is int else float(v)


def load(path: Path = FILE) -> Params:
    raw = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    known_sections = {s for s, _ in RANGES} | {"instrument"}
    unknown = [k for k in raw if k not in known_sections]
    if unknown:
        raise ParamsError(f"unknown settings: {unknown}")
    vals = {}
    for (sec, key) in RANGES:
        if sec not in raw or key not in raw[sec]:
            raise ParamsError(f"missing setting [{sec}] {key}")
        vals[(sec, key)] = _check(sec, key, raw[sec][key])
    for sec, block in raw.items():
        if isinstance(block, dict):
            extra = [k for k in block if (sec, k) not in RANGES]
            if extra:
                raise ParamsError(f"unknown settings in [{sec}]: {extra}")
    if not isinstance(raw.get("instrument"), str):
        raise ParamsError("instrument must be a name, e.g. \"BTC-PERPETUAL\"")
    return Params(instrument=raw["instrument"], fast_spans_days=vals[("signal", "fast_spans_days")],
                  slow_over_fast=vals[("signal", "slow_over_fast")], dp_vol_span_days=vals[("signal", "dp_vol_span_days")],
                  target_vol=vals[("size", "target_vol")], vol_window_days=vals[("size", "vol_window_days")],
                  buffer=vals[("size", "buffer")], take_profit=vals[("take_profit", "enabled")],
                  tp_sigmas=vals[("take_profit", "sigmas")], decision_minute=vals[("timing", "decision_minute")],
                  jitter_seconds=vals[("timing", "jitter_seconds")], execution=vals[("execution", "mode")],
                  max_drawdown=vals[("kill_switch", "max_drawdown")], max_feed_silence_s=vals[("kill_switch", "max_feed_silence_s")])
