"""Lecture 22 §2, teaching simulation, step 3: a trader who sees the value first. Left: its profit against the threshold at which it trades, a very small sniper against the formula of Rabechini Amaral (2026), with the gap's speed and size measured from the run.
Then: where the gap comes from, what the sniper costs the market maker with and without jumps in the value, and who it took its gains from. Invented data, several seeds."""
import json, sys
from pathlib import Path
import numpy as np
from plotly.subplots import make_subplots
from scipy.optimize import brentq
from scipy.special import dawsn, erfi
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l22 as L, l22_sim as Sim
from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure
apply_theme(); BLUE, ORANGE, GREEN = SERIES[0], SERIES[1], SERIES[2]; OUT = L.RESULTS / "sim_step3.json"; SEEDS = range(8); LAG = [1, 2, 5, 10, 20]


class Rec(Sim.Player):
    name = "rec"; next_time = 100

    def __init__(self, mm): self.mm = mm; self.g = []; self.p = []; self.h = []

    def act(self, m, t):
        self.g.append(m.mid() - m.fair); self.p.append(self.mm.pos); b, a = m.book.best(1), m.book.best(-1)
        if b is not None and a is not None: self.h.append((a - b) / 2)
        self.next_time = t + 100


def world(seed, T, sn=None, lean=4.0, jump=0.0, refresh=500):
    m = Sim.Market(seed=seed); m.band = -1; mm = Sim.MarketMaker(lean=lean, refresh=refresh); r = Rec(mm)
    m.players += [Sim.Noise(limit=12.0, depth=8.0), Sim.FairValue(jump=jump, jump_rate=0.1 if jump else 0.0), Sim.Value(), mm, r] + ([sn] if sn else []); m.run(T)
    return m, mm, r


def compute():
    T = 600_000; AC, S2, PH, G, P = [], [], [], [], []
    for s in SEEDS:
        _, _, r = world(s, T); g = np.array(r.g[50:]); p = np.array(r.p[50:]); G.append(g); P.append(p); g0 = g - g.mean(); S2.append(g0.var()); PH.append(np.mean(r.h)); AC.append([np.mean(g0[:-k] * g0[k:]) / g0.var() for k in LAG])
    alpha = -np.polyfit(np.array(LAG) * 0.1, np.log(np.mean(AC, 0)), 1)[0]; sg = float(np.mean(S2) ** 0.5); phi = float(np.mean(PH)); G, P = np.concatenate(G), np.concatenate(P)
    edges = np.arange(-1.5, 1.51, 0.25); mids = (edges[:-1] + edges[1:]) / 2; idx = np.digitize(P, edges) - 1; ok = [i for i in range(len(mids)) if (idx == i).sum() > 200]
    R = dict(alpha=float(alpha), sg=sg, phi=phi, r2=float(np.corrcoef(G, P)[0, 1] ** 2), pos=[float(mids[i]) for i in ok], gap=[float(G[idx == i].mean()) for i in ok], theta=[], rate=[], se=[], orders=[])
    for th in (0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0):
        x, n = [], []
        for s in SEEDS:
            sn = Sim.Sniper(theta=th, size=0.01); m, _, _ = world(s, T, sn); x.append((sn.cash + sn.pos * m.fair) / 0.01 / (T / 1000)); n.append(sn.n / (T / 60000))
        R["theta"].append(th); R["rate"].append(float(np.mean(x))); R["se"].append(float(np.std(x) / len(x) ** 0.5)); R["orders"].append(float(np.mean(n))); print("theta", th, round(np.mean(x), 3), flush=True)
    T = 300_000; R["grid"] = []
    for lean, jump, size, th in [(4.0, 0.0, 0.5, None), (4.0, 0.0, 0.5, 3.0), (4.0, 5.0, 0.5, None), (4.0, 5.0, 0.5, 3.0), (4.0, 5.0, 2.0, 3.0), (1.0, 0.0, 0.5, None), (1.0, 0.0, 0.5, 3.0), (1.0, 5.0, 0.5, None), (1.0, 5.0, 0.5, 3.0), (1.0, 5.0, 2.0, 3.0)]:
        mk, mz, sr, em, en = [], [], [], [], []
        for s in SEEDS:
            sn = Sim.Sniper(theta=th, size=size) if th else None; m, mm, _ = world(s, T, sn, lean, jump); mk.append(mm.cash + mm.pos * m.fair); mz.append(sum(t[2] for t in m.trades if t[5] == "market maker"))
            if sn: sr.append(sn.cash + sn.pos * m.fair); em.append(sn.edge.get("market maker", 0.0)); en.append(sn.edge.get("noise", 0.0))
        R["grid"].append(dict(lean=lean, jump=jump, size=size if th else 0.0, maker=float(np.mean(mk)), maker_se=float(np.std(mk) / len(mk) ** 0.5), per=float(np.sum(mk) / np.sum(mz)), sniper=float(np.mean(sr)) if sr else None, sniper_se=float(np.std(sr) / len(sr) ** 0.5) if sr else None, from_maker=float(np.mean(em)) if em else None, from_noise=float(np.mean(en)) if en else None)); print(R["grid"][-1], flush=True)
    R["refresh"] = []
    for rf in (100, 500, 2000, 5000):
        for size in (0.0, 0.5):
            mk, mz, sr, em, en = [], [], [], [], []
            for s in SEEDS:
                sn = Sim.Sniper(theta=3.0, size=size) if size else None; m, mm, _ = world(s, T, sn, 4.0, 5.0, rf); mk.append(mm.cash + mm.pos * m.fair); mz.append(sum(t[2] for t in m.trades if t[5] == "market maker"))
                if sn: sr.append(sn.cash + sn.pos * m.fair); em.append(sn.edge.get("market maker", 0.0)); en.append(sn.edge.get("noise", 0.0))
            R["refresh"].append(dict(refresh=rf, size=size, maker=float(np.mean(mk)), maker_se=float(np.std(mk) / len(mk) ** 0.5), per=float(np.sum(mk) / np.sum(mz)), sniper=float(np.mean(sr)) if sr else None, from_maker=float(np.mean(em)) if em else None, from_noise=float(np.mean(en)) if en else None)); print(R["refresh"][-1], flush=True)
    OUT.write_text(json.dumps(R, indent=1), encoding="utf-8")
    return R


R = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() and "--run" not in sys.argv else compute()
a, sg, phi = R["alpha"], R["sg"], R["phi"]; uD = brentq(lambda u: u - phi / sg - 2 ** 0.5 * dawsn(u / 2 ** 0.5), phi / sg, 6); thD = uD * sg; print("alpha", round(a, 3), "s_G", round(sg, 3), "phi", round(phi, 3), "gamma", round(phi / sg, 2), "theta_D", round(thD, 2), "R2 gap on position", round(R["r2"], 2))
fig = make_subplots(rows=1, cols=4, horizontal_spacing=0.065, subplot_titles=("How long should it wait?", "Most of the gap is the maker's lean", "A slower maker keeps less", "Who the sniper takes from"))
tt = np.linspace(phi + 1e-3, 4.2, 120); fig.add_scatter(x=tt, y=2 * (tt - phi) / (np.pi / a * erfi(tt / sg / 2 ** 0.5)), mode="lines", line=dict(color=MUTED, width=2), name="the paper's formula", row=1, col=1)
fig.add_scatter(x=R["theta"], y=R["rate"], error_y=dict(type="data", array=R["se"], color=BLUE), mode="markers+lines", line=dict(color=BLUE, width=1.5), marker=dict(color=BLUE, size=8), name="the simulation", row=1, col=1)
fig.add_vline(x=phi, line=dict(color=INK, width=1, dash="dot"), row=1, col=1); fig.add_annotation(x=phi, y=-0.1, text="half-spread", xanchor="left", showarrow=False, row=1, col=1); fig.update_xaxes(title_text="threshold, ticks from the value", row=1, col=1); fig.update_yaxes(title_text="ticks per BTC per second", row=1, col=1)
fig.add_scatter(x=R["pos"], y=R["gap"], mode="lines+markers", line=dict(color=GREEN, width=2), marker=dict(color=GREEN, size=8), showlegend=False, row=1, col=2); fig.update_xaxes(title_text="the maker's position, BTC", row=1, col=2); fig.update_yaxes(title_text="mid minus value, ticks", row=1, col=2)
Rf = R["refresh"]; rl = [f"{g['refresh'] / 1000:g} s" for g in Rf if g["size"] == 0]
for nm, sel, c in (("no sniper", 0.0, MUTED), ("sniper, 0.5 BTC", 0.5, BLUE)):
    fig.add_scatter(x=rl, y=[g["per"] for g in Rf if g["size"] == sel], mode="lines+markers", line=dict(color=c, width=2), marker=dict(color=c, size=8), name=nm, row=1, col=3)
fig.update_xaxes(title_text="how often the maker refreshes", row=1, col=3); fig.update_yaxes(title_text="maker's result, ticks per BTC", rangemode="tozero", row=1, col=3)
J = [g for g in Rf if g["size"] == 0.5]
fig.add_scatter(x=rl, y=[g["from_maker"] for g in J], mode="lines+markers", line=dict(color=GREEN, width=2), marker=dict(color=GREEN, size=8), name="taken from the maker's orders", row=1, col=4); fig.add_scatter(x=rl, y=[g["from_noise"] for g in J], mode="lines+markers", line=dict(color=ORANGE, width=2), marker=dict(color=ORANGE, size=8), name="taken from noise traders' orders", row=1, col=4)
fig.add_hline(y=0, line=dict(color=INK, width=1), row=1, col=4); fig.update_xaxes(title_text="how often the maker refreshes", row=1, col=4); fig.update_yaxes(title_text="edge against the value, ticks × BTC", row=1, col=4)
fig.update_layout(barmode="group", title="Step 3: a trader who sees the value first<br><sup>Invented; 8 seeds. Left, a 0.01 BTC sniper in a world with no jumps; right, a 0.5 BTC sniper with a threshold of 3 ticks over 5 minutes, jumps of 5 ticks about every 10 s</sup>", height=500, width=1500, margin=dict(t=100, l=70, r=30, b=130), legend=dict(orientation="h", y=-0.25, x=0))
save_figure(fig, L.PREFIX + "22_sim_step3", L.FIG)
