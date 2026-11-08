"""Lecture 22 §2, teaching simulation, step 9: ignition, by itself and on purpose, on the dials of step 8. By itself: in the world as it runs, with no order of ours, how many 10 s windows
see the mid move 15 ticks or more. On purpose: a pusher sells z BTC at the market at a copied moment and buys z back at the market after a wait; its profit per BTC in ticks (average sale price less average purchase price; any part
the book cannot fill on the way back is reported as unfilled), and how often it is positive. Momentum ignition is treated in many jurisdictions as manipulation: it is shown here as a risk to recognise, not a strategy. Invented data: 3 seeds x 20 moments per world."""
import copy, json, sys
from pathlib import Path
import numpy as np, polars as pl
from plotly.subplots import make_subplots
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l22 as L, l22_sim as Sim, l22_sim_step8 as S8
from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure
apply_theme(); OUT = L.RESULTS / "sim_step9.json"; SIZES = (5.0, 10.0); WAITS = (10_000, 60_000); BIG = 15


def one_world(cap, dens, kill):
    pnl = {f"{z:g}|{w}": [] for z in SIZES for w in WAITS}; short = {k: [] for k in pnl}; big = 0; windows = 0
    for seed in S8.SEEDS:
        m = Sim.Market(seed=seed); m.band = -1; mm = Sim.MarketMaker(kill_move=kill, kill_pos=4.0 if kill else 0.0)
        m.players += [Sim.Noise(limit=12.0, depth=8.0), Sim.FairValue(), Sim.Value(gap=3.0, max_pos=cap), mm] + ([Sim.Stops(density=dens)] if dens else [])
        for T0 in S8.MOMENTS:
            m.run(T0)
            for z in SIZES:
                for w in WAITS:
                    c = S8.fork(m); f, _ = c.market_order(-1, z, "us", T0 + 1); sold = sum(q for _, q, _, _ in f); got = sum(p * q for p, q, _, _ in f)
                    c.run(T0 + w); g, _ = c.market_order(1, sold, "us", T0 + w + 1); bought = sum(q for _, q, _, _ in g); paid = sum(p * q for p, q, _, _ in g)
                    if sold > 1e-9 and bought > 1e-9: pnl[f"{z:g}|{w}"].append(got / sold - paid / bought); short[f"{z:g}|{w}"].append(1 - bought / sold)
        m.run(S8.MOMENTS[-1] + 60_000)
        Q = pl.DataFrame(m.quotes, schema=["t", "bid", "ask"], orient="row").drop_nulls().filter(pl.col("t") >= S8.MOMENTS[0])
        x = ((Q["bid"] + Q["ask"]) / 2).to_numpy()[::100]                     # the mid every 10 s
        d = np.abs(np.diff(x)); big += int((d >= BIG).sum()); windows += len(d); del m
    return dict(big_per_hour=big / windows * 360, pnl={k: dict(mean=float(np.mean(v)), se=float(np.std(v, ddof=1) / np.sqrt(len(v))), win=float(np.mean(np.array(v) > 0)), unfilled=float(np.mean(short[k])), n=len(v)) for k, v in pnl.items()})


R = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
if "--run" in sys.argv:
    for w in S8.WORLDS:
        if S8.key(*w) in R: continue
        R[S8.key(*w)] = one_world(*w); OUT.write_text(json.dumps(R), encoding="utf-8"); v = R[S8.key(*w)]
        print(S8.key(*w), round(v["big_per_hour"], 2), {k: (round(x["mean"], 2), round(x["win"], 2)) for k, x in v["pnl"].items()}, flush=True)
fig = make_subplots(rows=1, cols=3, horizontal_spacing=0.08, subplot_titles=("By itself: how often does the mid jump?", "On purpose: does selling 10 BTC and buying back after 60 s pay?", "How often does it pay?"))
for (dens, kill), c, d, nm in (((0.0, 0), MUTED, "solid", "no stops, no kill switch"), ((0.0, 5), SERIES[0], "dot", "kill switch only"), ((0.2, 0), SERIES[2], "dot", "stops only"), ((0.2, 5), SERIES[1], "solid", "stops and kill switch")):
    ws = [R[S8.key(cap, dens, kill)] for cap in S8.CAPS]
    fig.add_scatter(x=S8.cap_lab, y=[w["big_per_hour"] for w in ws], mode="lines+markers", line=dict(color=c, width=2, dash=d), marker=dict(color=c, size=8), name=nm, row=1, col=1)
    fig.add_scatter(x=S8.cap_lab, y=[w["pnl"]["10|60000"]["mean"] for w in ws], error_y=dict(type="data", array=[w["pnl"]["10|60000"]["se"] for w in ws], color=c, thickness=1), mode="lines+markers",
                    line=dict(color=c, width=2, dash=d), marker=dict(color=c, size=8), showlegend=False, row=1, col=2)
    fig.add_scatter(x=S8.cap_lab, y=[w["pnl"]["10|60000"]["win"] for w in ws], mode="lines+markers", line=dict(color=c, width=2, dash=d), marker=dict(color=c, size=8), showlegend=False, row=1, col=3)
for c in (1, 2, 3): fig.update_xaxes(title_text="value traders' capital", row=1, col=c)
fig.add_hline(y=0, line=dict(color=INK, width=1, dash="dot"), row=1, col=2)
fig.update_yaxes(title_text=f"10 s windows moving {BIG}+ ticks, per hour", rangemode="tozero", row=1, col=1); fig.update_yaxes(title_text="profit per BTC, ticks", row=1, col=2)
fig.update_yaxes(title_text="share of round trips with a profit", tickformat=".0%", range=[0, 1], row=1, col=3)
fig.update_layout(title="Step 9: ignition, by itself and on purpose<br><sup>Invented; 3 seeds x 20 moments per world, dials as in step 8. On purpose: a market sell of 10 BTC, bought back at the market 60 s later. Bars: ± one standard error</sup>",
                  height=520, width=1500, margin=dict(t=110, l=70, r=30, b=140), legend=dict(orientation="h", y=-0.25, x=0))
save_figure(fig, L.PREFIX + "22_sim_step9", L.FIG)
