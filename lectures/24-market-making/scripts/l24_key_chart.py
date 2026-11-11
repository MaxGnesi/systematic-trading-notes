"""Lecture 24's key chart, from results/key.json (l24_key.py): where a market maker's money goes, for the five tested designs on the 24 out-of-sample
days, in bp of the value traded. Output: figures/24_key.png."""
import json, sys
from pathlib import Path
from plotly.subplots import make_subplots
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l24 as L
from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure

NAMES = {"baseline": "baseline: at the best", "guard_2": "Binance guard, 2 bp", "as_5_2": "Avellaneda-Stoikov", "behind_1": "1 tick behind the best",
         "pp_e0_c110_n2": "ping-pong, target and stop"}
PARTS = (("fill_1s_bp", "at the fill and in the first second: spread earned less the move against us", SERIES[1]),
         ("move_10s_bp", "move against us from 1 to 10 s", SERIES[4]), ("positions_bp", "positions held beyond 10 s", SERIES[0]),
         ("fees_bp", "fees (2 bp maker, 5.5 bp taker)", MUTED))

apply_theme(); K = json.loads((L.RESULTS / "key.json").read_text(encoding="utf-8"))
for k in K.values(): k["fill_1s_bp"] = k["spread_bp"] + k["move_1s_bp"]                  # the two cannot be told apart at the millisecond of a fill at the best
D = sorted(NAMES, key=lambda d: K[d]["after_fee_bp"]); y = [NAMES[d] for d in D]
fig = make_subplots(rows=1, cols=1)
for key, name, c in PARTS:
    fig.add_bar(y=y, x=[K[d][key] for d in D], orientation="h", marker_color=c, name=name)
fig.add_scatter(y=y, x=[K[d]["after_fee_bp"] for d in D], mode="markers+text", marker=dict(color=INK, size=11, symbol="diamond"), name="result after fees",
                text=[f"{K[d]['after_fee_bp']:.2f}" for d in D], textposition="middle left", textfont=dict(color=INK, size=12))
fig.add_vline(x=0, line=dict(color=INK, width=1))
fig.update_layout(title="Where a market maker's money goes<br><sup>Bybit BTCUSDT perpetual, 24 out-of-sample days (11 October - 3 November 2025); replay with 50 ms latency, "
                        "0.001 BTC orders; bp of the value traded</sup>",
                  barmode="relative", height=560, width=1250, margin=dict(t=100, l=230, r=30, b=150), legend=dict(orientation="h", y=-0.2, x=0))
fig.update_xaxes(title_text="bp of the value traded")
save_figure(fig, L.PREFIX + "24_key", L.FIG)
