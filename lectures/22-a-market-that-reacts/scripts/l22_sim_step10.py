"""Lecture 22 §2, laboratory market, step 10: the anatomy of a cascade. One fragile world of step 8 (value traders' capital 8 BTC, stops 0.2 BTC a tick, kill switch at 5 ticks)
recorded every 100 ms: the mid and the hidden value, the market maker in or out, the value traders' position against their limit, the stops resting near the price and those fired, and
the depth on each side. The largest 10 s move of the run is shown from 3 minutes before to 2 minutes after, with the stages of the text marked. Invented data.
Output: results/sim_step10.json and figures/22_sim_step10.png. --run recomputes."""
import json, sys
from pathlib import Path
import numpy as np
from plotly.subplots import make_subplots
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l22 as L, l22_sim as Sim
from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure
apply_theme(); OUT = L.RESULTS / "sim_step10.json"; CAP = 8.0; T_END = 3_600_000; STEP = 100


def record(seed):
    m = Sim.Market(seed=seed); m.band = -1; mm = Sim.MarketMaker(kill_move=5, kill_pos=4.0); va = Sim.Value(gap=3.0, max_pos=CAP); st = Sim.Stops(density=0.2)
    m.players += [Sim.Noise(limit=12.0, depth=8.0), Sim.FairValue(), va, mm, st]; rows = []
    for T in range(STEP, T_END + 1, STEP):
        m.run(T); x = m.mid(); b, a = m.book.depth(1), m.book.depth(-1)
        rows.append((T, x, m.fair, float(T < mm.out_until), va.pos, sum(v for p, v in st.stock[-1].items() if p >= x - 15), sum(v for p, v in st.stock[1].items() if p <= x + 15),
                     sum(z for _, s, z in st.fired if s == -1), sum(z for _, s, z in st.fired if s == 1), sum(v for p, v in b.items() if p >= x - 10), sum(v for p, v in a.items() if p <= x + 10)))
    return np.array(rows)


if __name__ == "__main__":
    if "--run" in sys.argv or not OUT.exists():
        best = None
        for seed in (21, 22, 23, 24):
            A = record(seed); mv = A[100:, 1] - A[:-100, 1]; k = int(np.argmax(np.abs(mv[18_000 // STEP:])) + 18_000 // STEP)   # after the first 30 minutes
            print(seed, "largest 10 s move", mv[k], flush=True)
            if best is None or abs(mv[k]) > abs(best[2]): best = (seed, A, mv[k], k)
        seed, A, size, k = best; lo, hi = max(k - 1800, 0), min(k + 1300, len(A))
        cols = ["t", "mid", "value", "maker_out", "value_pos", "stops_below", "stops_above", "fired_sell", "fired_buy", "depth_bid", "depth_ask"]
        OUT.write_text(json.dumps(dict(seed=seed, move=float(size), k=int(k), cap=CAP, **{c: A[lo:hi, i].tolist() for i, c in enumerate(cols)})), encoding="utf-8")
    R = json.loads(OUT.read_text(encoding="utf-8")); t = np.array(R["t"]); i0 = R["k"] - max(R["k"] - 1800, 0)
    t = (t - t[i0]) / 1000                                          # seconds from the start of the largest 10 s move
    sgn = 1 if R["move"] > 0 else -1
    fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.04, row_heights=[0.34, 0.22, 0.22, 0.22],
                        subplot_titles=("Price and value", "The restoring forces: maker in the book, arbitrage capital used", "The amplifier: stops waiting near the price, and stops fired", "Depth near the price"))
    mid, val = np.array(R["mid"]), np.array(R["value"]); base = mid[i0]
    fig.add_scatter(x=t, y=mid - base, mode="lines", line=dict(color=INK, width=1.8), name="mid", row=1, col=1)
    fig.add_scatter(x=t, y=val - base, mode="lines", line=dict(color=MUTED, width=1.5, dash="dot"), name="hidden value", row=1, col=1)
    fig.update_yaxes(title_text="ticks", row=1, col=1)
    fig.add_scatter(x=t, y=1 - np.array(R["maker_out"]), mode="lines", line=dict(color=SERIES[0], width=1.8, shape="hv"), name="maker quoting (1) or out (0)", row=2, col=1)
    used = -sgn * np.array(R["value_pos"]) / CAP                                       # share of their limit used on the side that corrects the move (buying after a fall)
    fig.add_scatter(x=t, y=used, mode="lines", line=dict(color=SERIES[2], width=1.8), name="value traders' capital used on the correcting side (1 = at their limit)", row=2, col=1)
    fig.update_yaxes(title_text="share", row=2, col=1)
    side = "below" if sgn < 0 else "above"; fired = np.array(R["fired_sell" if sgn < 0 else "fired_buy"]); fired = fired - fired[0]
    fig.add_scatter(x=t, y=R[f"stops_{side}"], mode="lines", line=dict(color=SERIES[1], width=1.8), name=f"stops within 15 ticks {side} the price, BTC", row=3, col=1)
    fig.add_scatter(x=t, y=fired, mode="lines", line=dict(color=SERIES[3], width=1.8), name="stops fired since the window began, BTC", row=3, col=1)
    fig.update_yaxes(title_text="BTC", row=3, col=1)
    fig.add_scatter(x=t, y=R["depth_bid"], mode="lines", line=dict(color=SERIES[0], width=1.5), name="bids within 10 ticks, BTC", row=4, col=1)
    fig.add_scatter(x=t, y=R["depth_ask"], mode="lines", line=dict(color=SERIES[1], width=1.5), name="asks within 10 ticks, BTC", row=4, col=1)
    fig.update_yaxes(title_text="BTC", row=4, col=1); fig.update_xaxes(title_text="seconds from the start of the largest 10 s move of the run", row=4, col=1)
    for r in range(1, 5): fig.add_vline(x=0, line=dict(color=INK, width=1, dash="dot"), row=r, col=1)
    fig.update_layout(title=f"The anatomy of a cascade in the laboratory market<br><sup>Invented. One hour of a fragile world (value traders' capital {CAP:g} BTC, stops 0.2 BTC a tick, kill switch at 5 ticks), seed {R['seed']}; "
                      f"its largest 10 s move, {R['move']:.0f} ticks, from 3 minutes before to 2 minutes after</sup>", height=950, width=1300, margin=dict(t=110, l=70, r=30, b=160), legend=dict(orientation="h", y=-0.12, x=0))
    save_figure(fig, L.PREFIX + "22_sim_step10", L.FIG)
