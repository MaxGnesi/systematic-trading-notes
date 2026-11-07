"""Lecture 22 §2, teaching simulation, step 4: a TWAP, and H12's run rule tested where the answer is known. The TWAP slices parent orders every 30 s; its rate is raised fivefold halfway through,
a change of mix made on purpose. The rule sees only public trades. Scored: how much of the TWAP's size it finds, how much of what it finds is TWAP, whether it sees the change, and what it finds with no TWAP.
Invented data, several seeds."""
import json, sys
from pathlib import Path
import numpy as np, polars as pl
from plotly.subplots import make_subplots
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l22 as L, l22_sim as Sim, l22_styles as St
from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure
apply_theme(); BLUE, ORANGE, GREEN = SERIES[0], SERIES[1], SERIES[2]; OUT = L.RESULTS / "sim_step4.json"; SEEDS = range(8); T_END, HALF, BLOCK = 1_800_000, 900_000, 300_000; A, Z = 1_200_000, 1_560_000


def world(seed, twap=True, jitter=0.0):
    m = Sim.Market(seed=seed); m.band = -1; tw = Sim.Twap(rate=((0, 0.2), (HALF, 1.0)), jitter=jitter)
    m.players += [Sim.Noise(limit=12.0, depth=8.0), Sim.FairValue(), Sim.Value(), Sim.MarketMaker()] + ([tw] if twap else []); m.run(T_END)
    return m


def measure(m, seed):
    """Taker orders from the public trades; tq is the part of each order that was the TWAP's, known only here."""
    O = m.public_trades().group_by("t", "side").agg(pl.col("size").sum().round(3).alias("q"), pl.col("size").filter(pl.col("taker") == "twap").sum().alias("tq")).sort("t")
    _, lab = St.runs(O); _, lab0 = St.runs(St.shuffled(O, BLOCK, seed)); q, tq, b = O["q"].to_numpy(), O["tq"].to_numpy(), O["t"].to_numpy() // BLOCK; r, r0 = lab >= 0, lab0 >= 0
    blocks = [dict(true=float(tq[b == k].sum() / q[b == k].sum()), found=float(q[(b == k) & r].sum() / q[b == k].sum()), shuffled=float(q[(b == k) & r0].sum() / q[b == k].sum())) for k in range(T_END // BLOCK)]
    by = {f"{z:g}": [float(tq[(q == z) & r].sum()), float(tq[q == z].sum())] for z in np.unique(q[tq > 0])}
    return O, lab, dict(blocks=blocks, by=by,recall=float(tq[r].sum() / tq.sum()) if tq.sum() else None, precision=float(tq[r].sum() / q[r].sum()) if r.any() else None, found=float(q[r].sum() / q.sum()), shuffled=float(q[r0].sum() / q.sum()), runs=int(lab.max() + 1))


def compute():
    R = {}; keep = {}
    for nm, tw, jit in (("exact", True, 0.0), ("jitter", True, 0.2), ("none", False, 0.0)):
        R[nm] = []; keep[nm] = []
        for s in SEEDS:
            m = world(s, tw, jit); O, lab, x = measure(m, s); R[nm].append(x); keep[nm].append((O, St.shuffled(O, BLOCK, s)))
            if nm == "exact" and s == 0:
                W = O.with_columns(pl.Series("run", lab)).filter(pl.col("t").is_between(A, Z)); R["window"] = dict(t=W["t"].to_list(), q=W["q"].to_list(), twap=(W["tq"] > 0).to_list(), run=W["run"].to_list())
        print(nm, {k: round(float(np.mean([x[k] for x in R[nm] if x[k] is not None])), 3) for k in ("recall", "precision", "found", "shuffled", "runs") if any(x[k] is not None for x in R[nm])}, flush=True)
    R["grid"] = []
    for n in (5, 8, 10):
        for cv in (0.1, 0.15, 0.2, 0.3):
            g = dict(n=n, cv=cv)
            for nm in ("exact", "jitter", "none"):
                tf = ta = qf = qs = qa = 0.0
                for O, O0 in keep[nm]:
                    _, lab = St.runs(O, cv, n); _, lab0 = St.runs(O0, cv, n); q, tq = O["q"].to_numpy(), O["tq"].to_numpy(); r = lab >= 0
                    tf += tq[r].sum(); ta += tq.sum(); qf += q[r].sum(); qs += q[lab0 >= 0].sum(); qa += q.sum()
                g[nm] = dict(recall=float(tf / ta) if ta else None, precision=float(tf / qf) if qf else None, found=float(qf / qa), shuffled=float(qs / qa))
            R["grid"].append(g)
    OUT.write_text(json.dumps(R), encoding="utf-8")
    return R


R = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() and "--run" not in sys.argv else compute()
mean = lambda nm, k: float(np.mean([x[k] for x in R[nm]])); bl = lambda nm, k: [float(np.mean([x["blocks"][i][k] for x in R[nm]])) for i in range(T_END // BLOCK)]
g8 = [g for g in R["grid"] if g["n"] == 8 and g["cv"] == 0.2][0]
for nm in ("exact", "jitter", "none"): print(nm, "pooled over seeds:", {k: round(v, 4) for k, v in g8[nm].items() if v is not None})
for nm in ("exact", "jitter"):
    agg = {}
    for x in R[nm]:
        for z, (f, a) in x["by"].items(): agg.setdefault(z, [0.0, 0.0]); agg[z][0] += f; agg[z][1] += a
    print(nm, "TWAP size found, by slice size:", {z: round(f / a, 2) for z, (f, a) in sorted(agg.items(), key=lambda v: -v[1][1])[:12]})
print("by 5 min, exact: true", np.round(bl("exact", "true"), 3), "found", np.round(bl("exact", "found"), 3), "shuffled", np.round(bl("exact", "shuffled"), 3))
fig = make_subplots(rows=1, cols=4, column_widths=[0.28, 0.28, 0.24, 0.2], horizontal_spacing=0.06, subplot_titles=("With the owners known: TWAP slices in orange", "The public trades, with the runs the rule found", "Does it see the mix change?", "Five slices are too few"))
w = R["window"]; t = (np.array(w["t"]) - A) / 60_000; q = np.array(w["q"]); tw = np.array(w["twap"]); run = np.array(w["run"])
fig.add_scatter(x=t[~tw], y=q[~tw], mode="markers", marker=dict(color=MUTED, size=4, opacity=0.5), name="other taker orders", row=1, col=1); fig.add_scatter(x=t[tw], y=q[tw], mode="markers", marker=dict(color=ORANGE, size=8), name="TWAP slices (hidden in the feed)", row=1, col=1)
fig.add_scatter(x=t, y=q, mode="markers", marker=dict(color=MUTED, size=4, opacity=0.5), showlegend=False, row=1, col=2)
for k, i in enumerate(sorted(set(run[run >= 0].tolist()))):
    s = run == i; fig.add_scatter(x=t[s], y=q[s], mode="lines+markers", line=dict(color=BLUE, width=1.5), marker=dict(color=BLUE, size=8), name="runs the rule found", showlegend=k == 0, row=1, col=2)
for c in (1, 2): fig.update_xaxes(title_text="minutes", row=1, col=c); fig.update_yaxes(type="log", title_text="order size, BTC", row=1, col=c)
x = [2.5 + 5 * i for i in range(T_END // BLOCK)]
for nm, k, c, d in (("true TWAP share", ("exact", "true"), ORANGE, "solid"), ("found, slices exactly 30 s apart", ("exact", "found"), BLUE, "solid"), ("found, gaps randomised by up to 20%", ("jitter", "found"), BLUE, "dot"), ("found, sizes shuffled", ("exact", "shuffled"), MUTED, "solid")):
    fig.add_scatter(x=x, y=bl(*k), mode="lines+markers", line=dict(color=c, width=2, dash=d), marker=dict(color=c, size=7), name=nm, row=1, col=3)
fig.add_vline(x=15, line=dict(color=INK, width=1, dash="dot"), row=1, col=3); fig.add_annotation(x=15, y=1, yref="y3 domain", text="TWAP rate ×5", xanchor="left", showarrow=False, row=1, col=3)
fig.update_xaxes(title_text="minutes", row=1, col=3); fig.update_yaxes(title_text="share of taker size", tickformat=".0%", rangemode="tozero", row=1, col=3)
for n, c in ((5, MUTED), (8, BLUE), (10, GREEN)):
    g = [x for x in R["grid"] if x["n"] == n]
    for k, d in (("exact", "solid"), ("jitter", "dot")):
        fig.add_scatter(x=[x["cv"] for x in g], y=[x[k]["precision"] for x in g], mode="lines+markers", line=dict(color=c, width=2, dash=d), marker=dict(color=c, size=7), name=f"{n} slices or more" + (", gaps randomised" if k == "jitter" else ""), row=1, col=4)
fig.add_vline(x=0.2, line=dict(color=INK, width=1, dash="dot"), row=1, col=4)
fig.update_xaxes(title_text="largest coefficient of variation of the gaps", row=1, col=4); fig.update_yaxes(title_text="share of what was found that is TWAP", tickformat=".0%", range=[0, 1.05], row=1, col=4)
fig.update_layout(barmode="group", title="Step 4: a TWAP, and the run rule of H12 tested with the answer known<br><sup>Invented; 8 seeds of 30 minutes. Parents of 1 to 5 BTC over 5 to 30 minutes, sliced every 30 s; 0.2 parents a minute, then 1 a minute from minute 15. The rule sees only public trades; left, eight slices or more, gaps' variation below 0.2</sup>", height=520, width=1600, margin=dict(t=110, l=70, r=30, b=140), legend=dict(orientation="h", y=-0.28, x=0))
save_figure(fig, L.PREFIX + "22_sim_step4", L.FIG)
