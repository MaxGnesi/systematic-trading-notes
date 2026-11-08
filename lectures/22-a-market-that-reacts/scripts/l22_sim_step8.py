"""Lecture 22 §2, teaching simulation, step 8: the tipping side of the map. Three dials: the value traders' capital (the position at which they stop trading), stop orders and liquidations
resting around the price, and the market maker's kill switch. Our market sell of 1, 5 or 10 BTC at moments copied as in step 7; the response is the mid with our order less without, at 1, 10
and 60 s, and our cost is a distribution, not an average. Invented data: 3 seeds x 20 moments (every 60 s from minute 20) per world. Each world is saved as it finishes; rerun resumes."""
import copy, json, sys
from pathlib import Path
import numpy as np
from plotly.subplots import make_subplots
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l22 as L, l22_sim as Sim
from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure
apply_theme(); OUT = L.RESULTS / "sim_step8.json"; SEEDS = (21, 22, 23); MOMENTS = range(1_200_000, 2_400_000, 60_000); TAUS = (1_000, 10_000, 60_000); SIZES = (1.0, 5.0, 10.0)
CAPS = (0.0, 15.0, 8.0, 4.0); CASCADE = -15
WORLDS = [(cap, dens, kill) for cap in CAPS for dens in (0.0, 0.2) for kill in (0, 5)]
key = lambda cap, dens, kill: f"{cap:g}|{dens:g}|{kill}"


def fork(m):
    keep = (m.trades, m.quotes, m.snaps); m.trades, m.quotes, m.snaps = [], [], []; c = copy.deepcopy(m); m.trades, m.quotes, m.snaps = keep
    return c


def one_world(cap, dens, kill):
    resp = {z: [] for z in SIZES}; cost = {z: [] for z in SIZES}; out = 0; n = 0; state = []
    for seed in SEEDS:
        m = Sim.Market(seed=seed); m.band = -1; mm = Sim.MarketMaker(kill_move=kill, kill_pos=4.0 if kill else 0.0)
        va = Sim.Value(gap=3.0, max_pos=cap); m.players += [Sim.Noise(limit=12.0, depth=8.0), Sim.FairValue(), va, mm] + ([Sim.Stops(density=dens)] if dens else [])
        for T0 in MOMENTS:
            m.run(T0); out += T0 < mm.out_until; n += 1; cs = {0.0: fork(m)} | {z: fork(m) for z in SIZES}
            x = m.mid(); bid = m.book.depth(1); st = [p for p in m.players if p.name == "stops"]
            state.append(dict(room=(cap - va.pos) if cap else None, gap=float(x - m.fair), vpos=float(va.pos), maker_out=bool(T0 < mm.out_until), depth=float(sum(v for p, v in bid.items() if p >= x - 10)),
                              fuel=float(sum(v for p, v in st[0].stock[-1].items() if p >= x - 15)) if st else 0.0))
            for z in SIZES:
                c = cs[z]; mid0 = c.mid(); f, left = c.market_order(-1, z, "us", T0 + 1)
                cost[z].append(mid0 - sum(p * q for p, q, _, _ in f) / max(z - left, 1e-9) if z - left > 1e-9 else np.nan)
            path = {z: [] for z in cs}
            for tau in TAUS:
                for z, c in cs.items(): c.run(T0 + tau); path[z].append(c.mid())
            for z in SIZES: resp[z].append([a - b for a, b in zip(path[z], path[0.0])])
        del m
    r = {}
    for z in SIZES:
        x = np.array(resp[z]); c = np.array(cost[z]); c = c[~np.isnan(c)]
        r[f"{z:g}"] = dict(resp=x.mean(0).tolist(), resp_se=(x.std(0, ddof=1) / np.sqrt(len(x))).tolist(), resp_med=np.median(x, 0).tolist(), cascade=float(np.mean(x[:, 1] < CASCADE)),
                           cost_p=[float(np.percentile(c, q)) for q in (50, 90)], cost_max=float(c.max()), n=len(x))
    per = [dict(s, **{f"r{z:g}": resp[z][i] for z in SIZES}, **{f"c{z:g}": cost[z][i] for z in SIZES}) for i, s in enumerate(state)]
    return dict(sizes=r, maker_out=out / n, moments=per)


cap_lab = ["unlimited", "15 BTC", "8 BTC", "4 BTC"]


if __name__ == "__main__":
    R = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    if "--run" in sys.argv:
        for w in WORLDS:
            if key(*w) in R: continue
            R[key(*w)] = one_world(*w); OUT.write_text(json.dumps(R), encoding="utf-8"); v = R[key(*w)]["sizes"]
            print(key(*w), {z: (round(v[z]["resp"][2], 2), round(v[z]["cascade"], 2), [round(c, 1) for c in v[z]["cost_p"]]) for z in v}, flush=True)
    fig = make_subplots(rows=1, cols=4, horizontal_spacing=0.07, subplot_titles=("The two ends: a 5 BTC sell", "Does the push fade? 5 BTC at 60 s", "How often does it cascade? 10 BTC", "What does 10 BTC cost? 90th percentile"))
    for (w, nm, c) in (((0.0, 0.0, 0), "calm: unlimited capital, no stops, no kill switch", SERIES[0]), ((4.0, 0.2, 5), "fragile: 4 BTC of capital, stops, kill switch", SERIES[1])):
        v = R[key(*w)]["sizes"]["5"]; fig.add_scatter(x=[0, 1, 10, 60], y=[0] + v["resp"], error_y=dict(type="data", array=[0] + v["resp_se"], color=c, thickness=1), mode="lines+markers",
                                                      line=dict(color=c, width=2), marker=dict(color=c, size=7), name=nm, row=1, col=1)
    fig.add_scatter(x=[0, 1, 10, 60], y=[0] * 4, mode="lines", line=dict(color=INK, width=1.5, dash="dot"), name="plain replay: the price ignores our order", row=1, col=1)
    fig.update_xaxes(title_text="seconds after our sell", type="category", row=1, col=1); fig.update_yaxes(title_text="mid with our sell less without, ticks", row=1, col=1)
    for (dens, kill), c, d, nm in (((0.0, 0), MUTED, "solid", "no stops, no kill switch"), ((0.0, 5), SERIES[0], "dot", "kill switch only"), ((0.2, 0), SERIES[2], "dot", "stops only"), ((0.2, 5), SERIES[1], "solid", "stops and kill switch")):
        ws = [R[key(cap, dens, kill)]["sizes"] for cap in CAPS]
        fig.add_scatter(x=cap_lab, y=[w["5"]["resp"][2] for w in ws], error_y=dict(type="data", array=[w["5"]["resp_se"][2] for w in ws], color=c, thickness=1), mode="lines+markers",
                        line=dict(color=c, width=2, dash=d), marker=dict(color=c, size=8), name=nm, row=1, col=2)
        fig.add_scatter(x=cap_lab, y=[w["10"]["cascade"] for w in ws], mode="lines+markers", line=dict(color=c, width=2, dash=d), marker=dict(color=c, size=8), showlegend=False, row=1, col=3)
        fig.add_scatter(x=cap_lab, y=[w["10"]["cost_p"][1] for w in ws], mode="lines+markers", line=dict(color=c, width=2, dash=d), marker=dict(color=c, size=8), showlegend=False, row=1, col=4)
    for c in (2, 3, 4): fig.update_xaxes(title_text="value traders' capital", row=1, col=c)
    fig.add_hline(y=0, line=dict(color=INK, width=1, dash="dot"), row=1, col=2)
    fig.update_yaxes(title_text="mid with our sell less without, ticks", row=1, col=2); fig.update_yaxes(title_text=f"share of moments below {CASCADE} ticks at 10 s", tickformat=".0%", rangemode="tozero", row=1, col=3)
    fig.update_yaxes(title_text="average fill below the mid before, ticks", rangemode="tozero", row=1, col=4)
    fig.update_layout(title="Step 8: the tipping side of the map<br><sup>Invented; 3 seeds x 20 moments per world, our market sell at copied moments. Stops: 0.2 BTC a tick from 3 to 30 ticks away; kill switch: out 5 s after a move of 5 ticks within 1 s. "
                      "Bars: ± one standard error</sup>", height=540, width=1600, margin=dict(t=110, l=70, r=30, b=140), legend=dict(orientation="h", y=-0.25, x=0))
    save_figure(fig, L.PREFIX + "22_sim_step8", L.FIG)
