"""Lecture 20, Section 2 cards, second part. 20_05: VPIN on invented volume buckets, and how bulk volume classification turns a price move into
one-sided volume. 20_06: a Hawkes process next to a Poisson process with the same average rate, events by generation, and the intensity.
20_07: lead and lag between two invented venues, the Hayashi-Yoshida cross-correlation by lag, with and without an offset between clocks."""
import sys
from math import erf, sqrt
from pathlib import Path
import numpy as np
from plotly.subplots import make_subplots
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l20 as L20
from trading_models.plotting import INK, MUTED, GRID, apply_theme, save_figure

apply_theme()
FIG = L20.FIG; FIG.mkdir(parents=True, exist_ok=True)
BUY, SELL, BLUE, ORANGE = "#2a63b0", "#c0436f", "#2a78d6", "#eb6834"
rng = np.random.default_rng(20)

# 20_05: VPIN. 100 invented buckets of equal volume: 70 balanced (buy share around 50%), then 30 one-sided (buy share around 25%).
NB, WIN = 100, 50
share = np.concatenate([np.clip(rng.normal(0.5, 0.07, 70), 0, 1), np.clip(rng.normal(0.25, 0.07, 30), 0, 1)])
imb = np.abs(2 * share - 1)                                       # |V_buy - V_sell| / V per bucket
vpin = np.array([imb[max(0, k - WIN + 1):k + 1].mean() if k >= WIN - 1 else np.nan for k in range(NB)])
z = np.linspace(-3, 3, 121); phi = np.array([0.5 * (1 + erf(x / sqrt(2))) for x in z])
print("VPIN at 69:", round(vpin[69], 3), "at 99:", round(vpin[99], 3))

fig = make_subplots(rows=1, cols=2, column_widths=[0.62, 0.38], horizontal_spacing=0.09,
                    subplot_titles=("Buckets of equal volume: the imbalance of each, and VPIN over the last 50",
                                    "Bulk classification: a move becomes one-sided"))
k = np.arange(1, NB + 1)
fig.add_bar(x=k, y=imb, marker_color=GRID, name="imbalance of the bucket", row=1, col=1)
fig.add_scatter(x=k, y=vpin, mode="lines", line=dict(color=INK, width=2.5), name="VPIN: average of the last 50 buckets", row=1, col=1)
fig.add_vrect(x0=70.5, x1=100.5, fillcolor="#fbe9f1", line_width=0, layer="below", row=1, col=1)
fig.add_annotation(x=85.5, y=0.92, text="sellers in a hurry:<br>a quarter of the volume bought", showarrow=False, font=dict(size=10.5, color=INK), row=1, col=1)
fig.add_annotation(x=35, y=0.92, text="balanced: about half bought", showarrow=False, font=dict(size=10.5, color=INK), row=1, col=1)
fig.update_xaxes(title_text="bucket number (each bucket = 1/50 of a day's volume)", row=1, col=1)
fig.update_yaxes(title_text="|buy − sell| / volume", range=[0, 1], row=1, col=1)
fig.add_scatter(x=z, y=phi, mode="lines", line=dict(color=BUY, width=2), name="share of the bucket counted as bought", row=1, col=2)
fig.add_scatter(x=z, y=np.abs(2 * phi - 1), mode="lines", line=dict(color=ORANGE, width=2, dash="dash"), name="imbalance it implies", row=1, col=2)
fig.update_xaxes(title_text="price change over the bar, in its standard deviations", row=1, col=2)
fig.update_yaxes(tickformat=".0%", range=[0, 1.02], row=1, col=2)
fig.update_layout(title="VPIN on invented buckets: it rises when the volume turns one-sided, and it is counted in volume, not in time<br>"
                        "<sup>Invented. Left: 100 buckets of equal volume; the window of 50 buckets is about one day's volume. Right: the bulk volume classification of the original, "
                        "share bought = normal distribution function of the bar's standardised price change</sup>",
                  height=470, width=1250, margin=dict(t=110, l=60, r=20, b=50), barmode="overlay", legend=dict(orientation="h", y=-0.22, x=0))
save_figure(fig, L20.PREFIX + "20_05_vpin_card", FIG)

# 20_06: Hawkes. Branching simulation over 120 s: outside events at MU per second; each event has a Poisson(N_BR) number of offspring after
# exponential delays of mean TAU. Next to it, a Poisson process with the same average rate MU / (1 - N_BR).
MU, N_BR, TAU, T_END = 0.4, 0.75, 1.0, 120.0
imm = np.sort(rng.uniform(0, T_END, rng.poisson(MU * T_END)))
ev = [(t, 0) for t in imm]; front = list(ev)
while front:
    nxt = []
    for t, g in front:
        for d in rng.exponential(TAU, rng.poisson(N_BR)):
            if t + d < T_END: nxt.append((t + d, g + 1))
    ev += nxt; front = nxt
ev.sort(); th = np.array([e[0] for e in ev]); gen = np.array([e[1] for e in ev])
rate = MU / (1 - N_BR)
pois = np.sort(rng.uniform(0, T_END, rng.poisson(rate * T_END)))
grid = np.linspace(0, T_END, 4000)
lam = MU + np.array([(N_BR / TAU * np.exp(-(g - th[th < g]) / TAU)).sum() for g in grid])
print("Hawkes events", len(th), "outside", int((gen == 0).sum()), "share triggered", round((gen > 0).mean(), 2), "Poisson events", len(pois))

fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.09, row_heights=[0.2, 0.3, 0.5],
                    subplot_titles=("Without excitation: events at random times (Poisson), same average rate",
                                    "With excitation (Hawkes): events from outside and the events they trigger",
                                    "The intensity of the Hawkes process: the expected rate of events at each moment"))
fig.add_scatter(x=pois, y=np.zeros(len(pois)), mode="markers", marker=dict(symbol="line-ns", size=14, line=dict(width=1.5, color=MUTED)),
                showlegend=False, row=1, col=1)
fig.add_scatter(x=th[gen == 0], y=np.zeros((gen == 0).sum()), mode="markers", marker=dict(symbol="line-ns", size=14, line=dict(width=2, color=INK)),
                name="from outside", row=2, col=1)
fig.add_scatter(x=th[gen > 0], y=np.zeros((gen > 0).sum()), mode="markers", marker=dict(symbol="line-ns", size=14, line=dict(width=1.5, color=ORANGE)),
                name="triggered by an earlier event", row=2, col=1)
fig.add_scatter(x=grid, y=lam, mode="lines", line=dict(color=BLUE, width=1.5), name="intensity", showlegend=False, row=3, col=1)
fig.add_hline(y=MU, line=dict(color=MUTED, width=1, dash="dot"), row=3, col=1)
fig.add_annotation(x=1, y=MU, text="the outside rate μ", xanchor="left", yshift=8, showarrow=False, font=dict(size=10, color=MUTED), row=3, col=1)
for r in (1, 2):
    fig.update_yaxes(visible=False, range=[-1, 1], row=r, col=1)
fig.update_yaxes(title_text="events per second", rangemode="tozero", row=3, col=1)
fig.update_xaxes(title_text="seconds", row=3, col=1)
fig.update_layout(title=f"A Hawkes process on invented events: each event raises the chance of more, so events come in clusters<br>"
                        f"<sup>Invented. Outside events at {MU} per second; each event triggers on average {N_BR} more, after delays of about {TAU:.0f} s "
                        f"(branching ratio n = {N_BR}); the Poisson process above has the same average rate, {rate:.1f} per second</sup>",
                  height=560, width=1250, margin=dict(t=110, l=60, r=20, b=50), legend=dict(orientation="h", y=-0.13, x=0))
save_figure(fig, L20.PREFIX + "20_06_hawkes_card", FIG)

# 20_07: lead and lag. A common price moves in steps; venue A follows it at once, venue B after LAG ms; each venue trades at its own random
# times and its trades show its own price with a little noise. The Hayashi-Yoshida correlation of the two price series by lag.
LAG, T_MS = 20, 60_000
steps_t = np.sort(rng.uniform(0, T_MS, 3000)); steps_x = np.cumsum(rng.choice([-1.0, 1.0], 3000))


def venue(delay, n):
    t = np.sort(rng.uniform(0, T_MS, n)); i = np.searchsorted(steps_t + delay, t, side="right") - 1
    return t, np.where(i >= 0, steps_x[np.maximum(i, 0)], 0.0) + rng.normal(0, 0.3, n)


ta, xa = venue(0, 6000); tb, xb = venue(LAG, 5000)


def hy_corr(t1, x1, t2, x2):
    """Hayashi-Yoshida correlation: products of all pairs of price changes whose time intervals overlap, no resampling."""
    d1, d2 = np.diff(x1), np.diff(x2); s1, e1, s2, e2 = t1[:-1], t1[1:], t2[:-1], t2[1:]
    tot, j = 0.0, 0
    for i in range(len(d1)):
        while j < len(d2) and e2[j] <= s1[i]: j += 1
        k = j
        while k < len(d2) and s2[k] < e1[i]:
            tot += d1[i] * d2[k]; k += 1
    return tot / np.sqrt((d1 ** 2).sum() * (d2 ** 2).sum())


lags = np.arange(-60, 61, 2)
cc = np.array([hy_corr(ta, xa, tb - L, xb) for L in lags])            # B shifted back by L ms: the peak is at L = how much later B moves
OFF = 8
cc_off = np.array([hy_corr(ta, xa, tb + OFF - L, xb) for L in lags])  # B's clock runs OFF ms fast
print("peak lag", lags[cc.argmax()], "with offset", lags[cc_off.argmax()], "LLR", round((cc[lags > 0] ** 2).sum() / (cc[lags < 0] ** 2).sum(), 2))

fig = make_subplots(rows=1, cols=2, column_widths=[0.5, 0.5], horizontal_spacing=0.09,
                    subplot_titles=("Half a second of trades on two venues", "Correlation of their price changes, by how much later B is read"))
w0 = steps_t[np.searchsorted(steps_t, 30_000)] - 100; m = lambda t: (t >= w0) & (t <= w0 + 500)
fig.add_scatter(x=ta[m(ta)] - w0, y=xa[m(ta)], mode="lines+markers", line=dict(color=BLUE, width=1.5, shape="hv"), marker=dict(size=5),
                name="venue A: trades", row=1, col=1)
fig.add_scatter(x=tb[m(tb)] - w0, y=xb[m(tb)], mode="lines+markers", line=dict(color=ORANGE, width=1.5, shape="hv"), marker=dict(size=5),
                name=f"venue B: trades, {LAG} ms behind", row=1, col=1)
fig.update_xaxes(title_text="milliseconds", row=1, col=1); fig.update_yaxes(title_text="price, ticks", row=1, col=1)
fig.add_scatter(x=lags, y=cc, mode="lines", line=dict(color=INK, width=2), name="clocks in step", row=1, col=2)
fig.add_scatter(x=lags, y=cc_off, mode="lines", line=dict(color=MUTED, width=2, dash="dot"), name=f"B's clock {OFF} ms fast", row=1, col=2)
fig.add_vline(x=0, line=dict(color=GRID, width=1), row=1, col=2)
fig.update_xaxes(title_text="lag in ms (positive: A moves first)", row=1, col=2); fig.update_yaxes(title_text="correlation", row=1, col=2)
fig.update_layout(title=f"Lead and lag on two invented venues: the correlation peaks at the delay, and an offset between clocks moves the peak just the same<br>"
                        f"<sup>Invented. One price moves in steps; venue A follows at once, venue B {LAG} ms later; each trades at its own random times "
                        "(about 100 and 80 trades a second) with a little noise. Correlation by the Hayashi-Yoshida estimator</sup>",
                  height=470, width=1250, margin=dict(t=110, l=60, r=20, b=50), legend=dict(orientation="h", y=-0.22, x=0))
save_figure(fig, L20.PREFIX + "20_07_leadlag_card", FIG)
