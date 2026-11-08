"""Lecture 22 §2, teaching simulation, step 7: our order in worlds that differ by one player type. At each moment the market is copied, random numbers included: one copy goes on without our
order, the others with a market buy of 1 or 5 BTC. The response is the mid with our order less the mid without, at 1, 10, 60 and 120 s; the plain replay of Lecture 21 assumes it is zero.
Our cost: the average fill less the mid before, in ticks. Invented data: 3 seeds, 40 moments each (every 90 s from minute 60), per world. Each world is saved as it finishes; rerun resumes."""
import copy, json, sys
from pathlib import Path
import numpy as np
from plotly.subplots import make_subplots
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l22 as L, l22_sim as Sim
from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure
apply_theme(); OUT = L.RESULTS / "sim_step7.json"; SEEDS = (11, 12, 13); MOMENTS = range(3_600_000, 7_200_000, 90_000); TAUS = (1_000, 10_000, 60_000, 120_000); SIZES = (1.0, 5.0)


def crowd(k):
    return [Sim.TrendFollower(fast=f, slow=s, size=0.2, clock=c, lag=2000) for _ in range(k) for f, s in ((1, 50), (20, 50), (5, 20), (1, 20)) for c in (60_000, 300_000)]


def base(jump):
    return [Sim.Noise(limit=12.0, depth=8.0), Sim.FairValue(jump=5.0 if jump else 0.0, jump_rate=0.1 if jump else 0.0), Sim.Value(gap=3.0), Sim.MarketMaker()]


WORLDS = {"base": lambda: base(False), "+ value jumps": lambda: base(True), "+ sniper (with jumps)": lambda: base(True) + [Sim.Sniper(theta=3.0, size=0.5)],
          "+ TWAP": lambda: base(False) + [Sim.Twap(rate=((0, 0.5),))], "+ trend followers": lambda: base(False) + crowd(5), "+ scalper": lambda: base(False) + [Sim.Scalper()],
          "full mix (with jumps)": lambda: base(True) + [Sim.Sniper(theta=3.0, size=0.5), Sim.Twap(rate=((0, 0.5),)), Sim.Scalper()] + crowd(5)}


def fork(m):
    """A copy of the market as it stands, without its records."""
    keep = (m.trades, m.quotes, m.snaps); m.trades, m.quotes, m.snaps = [], [], []; c = copy.deepcopy(m); m.trades, m.quotes, m.snaps = keep
    return c


def one_world(make):
    cost = {z: [] for z in SIZES}; resp = {z: [] for z in SIZES}
    for seed in SEEDS:
        m = Sim.Market(seed=seed); m.band = -1; m.players += make()
        for T0 in MOMENTS:
            m.run(T0); copies = {0.0: fork(m)} | {z: fork(m) for z in SIZES}
            for z in SIZES:
                c = copies[z]; mid0 = c.mid(); f, left = c.market_order(1, z, "us", T0 + 1); cost[z].append(sum(p * q for p, q, _, _ in f) / max(z - left, 1e-9) - mid0)
            path = {z: [] for z in copies}
            for tau in TAUS:
                for z, c in copies.items(): c.run(T0 + tau); path[z].append(c.mid())
            for z in SIZES: resp[z].append([a - b for a, b in zip(path[z], path[0.0])])
        del m
    se = lambda x: (np.std(x, axis=0, ddof=1) / np.sqrt(len(x))).tolist()
    return {f"{z:g}": dict(cost=float(np.mean(cost[z])), cost_se=float(se(cost[z])), resp=np.mean(resp[z], axis=0).tolist(), resp_se=se(resp[z]), n=len(resp[z])) for z in SIZES}


R = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
if "--run" in sys.argv:
    for nm, make in WORLDS.items():
        if nm in R: continue
        R[nm] = one_world(make); OUT.write_text(json.dumps(R), encoding="utf-8")
        print(nm, {z: (round(v["cost"], 2), [round(x, 2) for x in v["resp"]], [round(x, 2) for x in v["resp_se"]]) for z, v in R[nm].items()}, flush=True)
names = list(WORLDS); short = [n.replace(" (with jumps)", "*") for n in names]
fig = make_subplots(rows=1, cols=3, column_widths=[0.36, 0.36, 0.28], horizontal_spacing=0.09, subplot_titles=("How does the mid answer a 5 BTC buy?", "How much is left after 10 s?", "What does our order cost?"))
x = [0] + [t / 1000 for t in TAUS]
for nm, c in zip(("base", "+ sniper (with jumps)", "+ TWAP", "+ trend followers", "full mix (with jumps)"), SERIES):
    v = R[nm]["5"]; fig.add_scatter(x=x, y=[0] + v["resp"], error_y=dict(type="data", array=[0] + v["resp_se"], color=c, thickness=1), mode="lines+markers",
                                    line=dict(color=c, width=2), marker=dict(color=c, size=7), name=nm, row=1, col=1)
fig.add_scatter(x=x, y=[0] * len(x), mode="lines", line=dict(color=INK, width=1.5, dash="dot"), name="plain replay: the price ignores our order", row=1, col=1)
fig.update_xaxes(title_text="seconds after our order", type="category", row=1, col=1); fig.update_yaxes(title_text="mid with our order less without, ticks", row=1, col=1)
for z, c, sym in (("1", MUTED, "circle"), ("5", SERIES[0], "diamond")):
    fig.add_scatter(x=[R[n][z]["resp"][1] for n in names], y=short, error_x=dict(type="data", array=[R[n][z]["resp_se"][1] for n in names], color=c, thickness=1), mode="markers",
                    marker=dict(color=c, size=10, symbol=sym), name=f"our buy of {z} BTC", row=1, col=2)
    fig.add_scatter(x=[R[n][z]["cost"] for n in names], y=short, error_x=dict(type="data", array=[R[n][z]["cost_se"] for n in names], color=c, thickness=1), mode="markers",
                    marker=dict(color=c, size=10, symbol=sym), showlegend=False, row=1, col=3)
fig.add_vline(x=0, line=dict(color=INK, width=1, dash="dot"), row=1, col=2)
fig.update_xaxes(title_text="response at 10 s, ticks", row=1, col=2); fig.update_xaxes(title_text="average fill less mid before, ticks", rangemode="tozero", row=1, col=3)
for c in (2, 3): fig.update_yaxes(categoryorder="array", categoryarray=short[::-1], row=1, col=c)
fig.update_yaxes(showticklabels=False, row=1, col=3)
fig.update_layout(title="Step 7: our order in worlds that differ by one player type<br><sup>Invented; 3 seeds x 40 moments per world. The same market copied at each moment, run on with and without our market buy. "
                  "Bars: ± one standard error. * with jumps of the value</sup>", height=540, width=1600, margin=dict(t=110, l=70, r=30, b=140), legend=dict(orientation="h", y=-0.25, x=0))
save_figure(fig, L.PREFIX + "22_sim_step7", L.FIG)
