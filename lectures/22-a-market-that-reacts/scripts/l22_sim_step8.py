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
    M = [dict(mo, w=k) for k, v in R.items() for mo in v["moments"]]; gap = np.array([m["gap"] for m in M]); r5 = np.array([m["r5"] for m in M]); r10 = np.array([m["r10"] for m in M])
    c10 = np.array([m["c10"] for m in M], float); out = np.array([m["maker_out"] for m in M]); dep = np.array([m["depth"] for m in M]); kill = np.array([k.endswith("|5") for k in (m["w"] for m in M)])
    se = lambda x: x.std(ddof=1) / np.sqrt(len(x))
    fig = make_subplots(rows=1, cols=4, horizontal_spacing=0.075, subplot_titles=("The two ends: a 5 BTC sell", "Does the push fade? By the gap to the value", "What does 10 BTC cost? Maker in or out",
                                                                               "What does 10 BTC cost? By depth"))
    for sel, nm, c in ((np.abs(gap) <= 1, "price within 1 tick of the value", SERIES[0]), (np.abs(gap) > 3, "price more than 3 ticks from the value", SERIES[1])):
        x = r5[sel]; fig.add_scatter(x=[0, 1, 10, 60], y=[0] + x.mean(0).tolist(), error_y=dict(type="data", array=[0] + (x.std(0, ddof=1) / np.sqrt(len(x))).tolist(), color=c, thickness=1),
                                     mode="lines+markers", line=dict(color=c, width=2), marker=dict(color=c, size=7), name=f"{nm} ({sel.sum()} moments)", row=1, col=1)
    fig.add_scatter(x=[0, 1, 10, 60], y=[0] * 4, mode="lines", line=dict(color=INK, width=1.5, dash="dot"), name="plain replay: the price ignores our order", row=1, col=1)
    fig.update_xaxes(title_text="seconds after our sell", type="category", row=1, col=1); fig.update_yaxes(title_text="mid with our sell less without, ticks", row=1, col=1)
    bins = [(-99, -3, "below by >3"), (-3, -1, "below 1-3"), (-1, 1, "within 1"), (1, 3, "above 1-3"), (3, 99, "above by >3")]
    for z, arr, c in (("5 BTC", r5, MUTED), ("10 BTC", r10, SERIES[1])):
        ys = [arr[(gap > a) & (gap <= b), 2] for a, b, _ in bins]
        fig.add_scatter(x=[b[2] for b in bins], y=[y.mean() for y in ys], error_y=dict(type="data", array=[se(y) for y in ys], color=c, thickness=1), mode="lines+markers", line=dict(color=c, width=2),
                        marker=dict(color=c, size=8), name=f"our sell of {z}, left after 60 s", row=1, col=2)
    fig.add_hline(y=0, line=dict(color=INK, width=1, dash="dot"), row=1, col=2)
    fig.update_xaxes(title_text="price against the value when we sell (ticks)", row=1, col=2); fig.update_yaxes(title_text="mid with our sell less without, ticks", row=1, col=2)
    for q, sym, nm in ((50, "circle", "median cost"), (90, "diamond", "90th percentile of cost")):
        sel = [kill & ~out, kill & out]
        fig.add_scatter(x=["maker in", "maker out"], y=[np.nanpercentile(c10[s], q) for s in sel], mode="markers", marker=dict(color=SERIES[0], size=12, symbol=sym), name=nm, row=1, col=3)
        qs = np.quantile(dep, [0.2, 0.4, 0.6, 0.8]); f = np.digitize(dep, qs)
        fig.add_scatter(x=[f"{i + 1}" for i in range(5)], y=[np.nanpercentile(c10[f == i], q) for i in range(5)], mode="lines+markers", line=dict(color=SERIES[0], width=2, dash="solid" if q == 50 else "dot"),
                        marker=dict(color=SERIES[0], size=10, symbol=sym), showlegend=False, row=1, col=4)
    fig.update_xaxes(title_text=f"when we sell (kill-switch worlds; out: {int((kill & out).sum())} moments)", row=1, col=3)
    fig.update_xaxes(title_text="fifth of depth within 10 ticks (1 = thinnest)", row=1, col=4)
    for c in (3, 4): fig.update_yaxes(title_text="average fill below the mid before, ticks", rangemode="tozero", row=1, col=c)
    fig.update_layout(title="Step 8: the tipping side of the map, read by the state when we sell<br><sup>Invented; 16 worlds (value traders' capital, stops, kill switch) x 3 seeds x 20 moments, our market sell at copied moments, "
                      "pooled. Bars: ± one standard error</sup>", height=540, width=1600, margin=dict(t=110, l=70, r=30, b=150), legend=dict(orientation="h", y=-0.27, x=0))
    save_figure(fig, L.PREFIX + "22_sim_step8", L.FIG)
