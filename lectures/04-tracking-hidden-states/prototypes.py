"""Lecture 4 prototypes (draft, for review): reproduces charts C.5 and C.6 and the signal-agreement table.

Run from anywhere inside the repository:  python lectures/04-tracking-hidden-states/prototypes.py
Prices come from trading_models.data.ohlc (cached under data/raw/, fetched on first run).
These are prototypes; the final versions will live in the Lecture 4 notebook.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from trading_models.data.ohlc import load_ohlc
from trading_models.plotting import MUTED, SERIES, apply_theme, save_figure

apply_theme()
ROOT = next(p for p in [Path.cwd(), *Path(__file__).resolve().parents] if (p / "pyproject.toml").exists())
FIG = ROOT / "lectures" / "04-tracking-hidden-states" / "figures"
ohlc = load_ohlc(["QQQ"], start="1999-01-01", cache=ROOT / "data" / "raw" / "nb11_qqq_ohlc_long.csv")
close = ohlc["close"]["QQQ"].dropna()
log_price, dates = np.log(close.to_numpy()), close.index


def model(n_states: int):
    """Transition matrix, observation vector and relative noise settings (diagonal of Q)."""
    if n_states == 1:   # level only
        return np.array([[1.0]]), np.array([1.0]), np.array([1.0])
    if n_states == 2:   # level + slope
        return np.array([[1, 1], [0, 1.0]]), np.array([1.0, 0]), np.array([1.0, 1e-2])
    # level + slope + acceleration: over one bar the level moves by slope + 0.5 * acceleration
    return np.array([[1, 1, 0.5], [0, 1, 1], [0, 0, 1.0]]), np.array([1.0, 0, 0]), np.array([1.0, 1e-2, 1e-4])


def kalman(y, transition, observe, q_diag, r_price):
    """Linear Kalman filter. Returns the filtered states, one row per bar."""
    n = transition.shape[0]
    state = np.zeros(n); state[0] = y[0]
    uncertainty = np.eye(n)
    Q = np.diag(q_diag)
    out = np.empty((len(y), n))
    for t, price in enumerate(y):
        state = transition @ state                                    # predict
        uncertainty = transition @ uncertainty @ transition.T + Q
        surprise_var = observe @ uncertainty @ observe + r_price
        gain = uncertainty @ observe / surprise_var                   # how much to trust the new price
        state = state + gain * (price - observe @ state)              # correct by gain x surprise
        uncertainty = uncertainty - np.outer(gain, observe @ uncertainty)
        out[t] = state
    return out


def run(y, n_states, r_price, q_scale=1e-4):
    F, H, q_rel = model(n_states)
    return kalman(y, F, H, q_rel * q_scale, r_price)


def variance_reduction(n_states, r_price):
    """Sum of squared steady-state weights of the level, from its impulse response."""
    z = np.zeros(4000)
    base = run(z, n_states, r_price)[:, 0]
    z[3000] = 1.0
    w = (run(z, n_states, r_price)[:, 0] - base)[3000:]
    return (w ** 2).sum() / w.sum() ** 2


# ---- C.5: three models matched on memory (variance reduction 1/20, as EMA(20)) ----
r_matched = {}
for k in (1, 2, 3):
    lo, hi = 1e-6, 1e3
    for _ in range(60):
        mid = np.sqrt(lo * hi)
        lo, hi = (mid, hi) if variance_reduction(k, mid) > 1 / 20 else (lo, mid)
    r_matched[k] = mid
    print(f"model with {k} state(s): price noise R matched to variance reduction 1/20 -> {mid:.4g}")

states = {k: run(log_price, k, r_matched[k]) for k in (1, 2, 3)}
names = {1: "Level only (= EMA-like)", 2: "Level + slope", 3: "Level + slope + acceleration"}
m = (dates >= "2021-06-01") & (dates <= "2023-06-30")
fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.34, 0.22, 0.22, 0.22],
                    subplot_titles=("Position: price and each model's level", "Slope (annualised trend, %)",
                                    "Acceleration (change in annualised trend per day, %)",
                                    "Signals: +1 long / -1 short (offset for readability)"))
fig.add_scatter(x=dates[m], y=close.to_numpy()[m], name="QQQ close", mode="lines", line=dict(width=1, color=MUTED), row=1, col=1)
for j, k in enumerate((1, 2, 3)):
    fig.add_scatter(x=dates[m], y=np.exp(states[k][m, 0]), name=names[k], mode="lines", line=dict(width=1.7, color=SERIES[j]), row=1, col=1)
for j, k in ((1, 2), (2, 3)):
    fig.add_scatter(x=dates[m], y=100 * 252 * states[k][m, 1], name=names[k], showlegend=False, mode="lines",
                    line=dict(width=1.7, color=SERIES[j]), row=2, col=1)
fig.add_scatter(x=dates[m], y=100 * 252 * states[3][m, 2], name=names[3], showlegend=False, mode="lines",
                line=dict(width=1.7, color=SERIES[2]), row=3, col=1)
signals = {
    "Position, level only": np.sign(log_price - states[1][:, 0]),
    "Position, level + slope": np.sign(log_price - states[2][:, 0]),
    "Position, + acceleration": np.sign(log_price - states[3][:, 0]),
    "Slope, level + slope": np.sign(states[2][:, 1]),
    "Slope, + acceleration": np.sign(states[3][:, 1]),
    "Acceleration": np.sign(states[3][:, 2]),
}
colours = [SERIES[0], SERIES[1], SERIES[2], SERIES[1], SERIES[2], SERIES[2]]
dashes = ["solid", "solid", "solid", "dot", "dot", "dash"]
for j, (name, s) in enumerate(signals.items()):
    fig.add_scatter(x=dates[m], y=s[m] * 0.4 + (len(signals) - 1 - j) * 1.2, name=name, mode="lines",
                    line=dict(width=1.3, color=colours[j], dash=dashes[j], shape="hv"), row=4, col=1)
fig.update_yaxes(showticklabels=False, row=4, col=1)
for r_ in (2, 3):
    fig.add_hline(y=0, line=dict(width=1, color=MUTED, dash="dot"), row=r_, col=1)
fig.update_layout(title="Three Kalman models matched on memory (variance reduction of EMA(20)): states and signals, QQQ 2021-2023",
                  height=1100, width=1150, margin=dict(t=90, b=80), legend=dict(orientation="h", y=-0.05, x=0))
save_figure(fig, "c5_three_models_states_signals", FIG)

agree = pd.DataFrame(signals, index=dates).iloc[300:]
print("\nShare of days each pair of signals agrees (QQQ, 1999 onward):")
print((agree.T.dot(agree) / len(agree) * 0.5 + 0.5).round(2).to_string())

# ---- C.6: the dials, four noise settings on the three-state model (QQQ 2020) ----
F3, H3, _ = model(3)
settings = {"Balanced": (1e-6, 1e-8, 1e-11), "Level emphasised": (1e-4, 1e-8, 1e-11),
            "Slope emphasised": (1e-6, 1e-6, 1e-11), "Acceleration emphasised": (1e-6, 1e-8, 1e-9)}
r_price = 1e-4
m = (dates >= "2020-01-01") & (dates <= "2020-07-31")
fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.06,
                    subplot_titles=("Level (price scale)", "Slope (annualised trend, %)",
                                    "Acceleration (change in annualised trend per day, %)"))
fig.add_scatter(x=dates[m], y=close.to_numpy()[m], name="QQQ close", mode="lines", line=dict(width=1, color=MUTED), row=1, col=1)
for j, (name, q) in enumerate(settings.items()):
    X = kalman(log_price, F3, H3, np.array(q), r_price)
    fig.add_scatter(x=dates[m], y=np.exp(X[m, 0]), name=name, mode="lines", line=dict(width=1.6, color=SERIES[j]), row=1, col=1)
    fig.add_scatter(x=dates[m], y=100 * 252 * X[m, 1], name=name, showlegend=False, mode="lines", line=dict(width=1.6, color=SERIES[j]), row=2, col=1)
    fig.add_scatter(x=dates[m], y=100 * 252 * X[m, 2], name=name, showlegend=False, mode="lines", line=dict(width=1.6, color=SERIES[j]), row=3, col=1)
for r_ in (2, 3):
    fig.add_hline(y=0, line=dict(width=1, color=MUTED, dash="dot"), row=r_, col=1)
fig.update_layout(title="One filter, three hidden states: how the noise settings shift emphasis (QQQ, 2020)",
                  height=900, width=1100, margin=dict(t=90, b=70), legend=dict(orientation="h", y=-0.06, x=0))
save_figure(fig, "c6_noise_settings_emphasis", FIG)
print("\nCharts written to", FIG)
