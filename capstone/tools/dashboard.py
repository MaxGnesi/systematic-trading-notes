"""A local dashboard of the live bot (Lecture 24): candles, the moving averages the signal uses, when it fired,
the take-profit levels, sizing by volatility, the position, slippage and profit and loss.

Reads the bot's database read-only and recomputes the signal with the bot's own code from Deribit's public
prices, so the indicators are exactly the bot's. Writes capstone/data/dashboard.html (not committed: it shows
account data). Never sends anything to the exchange with keys.
Usage, from the repository root: python -X utf8 -m capstone.tools.dashboard [--days 30]"""
import argparse
import html
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from capstone.connectors import deribit_rest
from capstone.connectors.history import MinuteCloses
from capstone.strategies.trend import params as P
from capstone.strategies.trend.signal import targets
from trading_models.plotting import INK, MUTED, SERIES, apply_theme

DATA = Path(__file__).resolve().parents[1] / "data"
DB, OUT = DATA / "capstone.db", DATA / "dashboard.html"
UP, DOWN = SERIES[0], SERIES[1]                     # blue and orange: easier to tell apart than green and red


def read_db() -> dict:
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    q = lambda sql: pd.read_sql_query(sql, con)
    out = {"decisions": q("SELECT at, signal, action, target_qty, arrival_price, reason FROM decisions ORDER BY id"),
           "fills": q("SELECT at, client_order_id, side, price, qty, fee, is_maker FROM fills ORDER BY id"),
           "equity": q("SELECT at, equity_btc, price, position_usd FROM equity_snapshots ORDER BY id"),
           "events": q("SELECT at, level, kind, detail FROM bot_events WHERE level IN ('warning', 'critical') ORDER BY id DESC LIMIT 8")}
    con.close()
    for k in ("decisions", "fills", "equity"):
        out[k]["at"] = pd.to_datetime(out[k]["at"], utc=True, format="ISO8601")
    num = {"decisions": ("target_qty", "arrival_price"), "fills": ("price", "qty", "fee"), "equity": ("equity_btc", "price", "position_usd")}
    for k, cols in num.items():
        for c in cols:
            out[k][c] = pd.to_numeric(out[k][c], errors="coerce")
    return out


def inspect_db(rows: int = 25) -> str:
    """Every table of the database: its row count and its latest rows, newest first, as collapsible HTML."""
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True); parts = []
    for (t,) in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"):
        n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        df = pd.read_sql_query(f"SELECT * FROM {t} ORDER BY rowid DESC LIMIT {rows}", con)
        parts.append(f"<details><summary><b>{t}</b>: {n} rows</summary>{df.to_html(index=False) if len(df) else '<p>empty</p>'}</details>")
    con.close()
    return "".join(parts)


def hourly_candles(instrument: str, start: pd.Timestamp) -> pd.DataFrame:
    now = int(time.time() * 1000); t, rows = int(start.timestamp() * 1000), []
    while t < now:
        e = min(t + 1000 * 3_600_000, now)
        rows += deribit_rest.candles("mainnet", instrument, t, e, resolution="60"); t = e
    c = pd.DataFrame(rows).drop_duplicates("start_ms")
    c.index = pd.to_datetime(c.start_ms, unit="ms", utc=True)
    return c[["open", "high", "low", "close"]].astype(float)


def slippage(dec: pd.DataFrame, fills: pd.DataFrame) -> pd.DataFrame:
    """Per order: average fill price against the arrival mid of its decision, in bp; positive = a cost."""
    rows = []
    for label, g in fills.groupby("client_order_id"):
        trade_dec = dec[dec.action.isin(["buy", "sell"]) & (dec["at"] <= g["at"].min())]
        if trade_dec.empty:
            continue
        d = trade_dec.iloc[-1]; side = g.side.iloc[0]
        avg = float((g.price * g.qty).sum() / g.qty.sum())
        rows.append(dict(time=g["at"].min(), label=label, side=side, usd=float(g.qty.sum()), arrival_mid=d.arrival_price, avg_fill=avg,
                         slippage_bp=(avg / d.arrival_price - 1) * (1 if side == "buy" else -1) * 1e4, fee_btc=float(g.fee.sum()),
                         maker=bool(g.is_maker.max())))
    return pd.DataFrame(rows)


def tp_levels(price: pd.Series, sig: pd.DataFrame, days: float, p, hourly_vol: pd.Series) -> pd.DataFrame:
    """For one speed, each run of the same sign: entry time and price, and the price at which its open gain would
    reach the take-profit threshold (entry x (1 + sign x sigmas x unit), unit = hourly volatility at entry x sqrt(hours));
    an approximation, since the rule sums hourly returns."""
    f = sig[f"f{days:g}d"]; flat = sig[f"tp{days:g}d"].astype(bool)
    sign = np.sign(f.where(~flat, np.nan).ffill()).fillna(0)
    # the sign of the underlying forecast is what starts a new run; recompute it before the take profit
    raw_sign = np.sign(f.mask(flat)).ffill()
    runs, cur = [], None
    for t, s in raw_sign.items():
        if np.isnan(s) or s == 0:
            continue
        if cur is None or s != cur["sign"]:
            if cur is not None:
                cur["end"] = t; runs.append(cur)
            unit = hourly_vol.get(t, np.nan) * np.sqrt(days * 24)
            cur = dict(start=t, sign=s, entry=float(price.get(t, np.nan)), level=float(price.get(t, np.nan)) * (1 + s * p.tp_sigmas * unit))
    if cur is not None:
        cur["end"] = price.index[-1]; runs.append(cur)
    return pd.DataFrame(runs)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--days", type=int, default=30); a = ap.parse_args()
    p = P.load(); apply_theme()
    db = read_db()
    hourly = MinuteCloses(p.instrument, "mainnet", int(p.vol_window_days * 2) + 60).hourly(p.decision_minute)
    sig = targets(hourly, p)
    hourly_vol = hourly.pct_change().rolling(int(p.vol_window_days * 24), min_periods=int(p.vol_window_days * 12)).std()
    start = hourly.index[-1] - pd.Timedelta(days=a.days)
    px, sg = hourly[hourly.index >= start], sig[sig.index >= start]
    candles = hourly_candles(p.instrument, start)
    eq = db["equity"].set_index("at")
    eq_h = eq.equity_btc.resample("h").last().reindex(sg.index, method="ffill")
    target_usd = sg.target_x_equity * eq_h * px
    slip = slippage(db["decisions"], db["fills"])

    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.55, 0.27, 0.18],
                        subplot_titles=("Hourly candles (mainnet), the moving averages of each speed, the bot's decisions and fills, and the current take-profit levels",
                                        "The signal: each speed's forecast after the take profit, and the blend the position follows",
                                        "Sizing: annual volatility of hourly returns over the past six months (the position is scaled by 10% / this)"))
    fig.add_trace(go.Candlestick(x=candles.index, open=candles.open, high=candles.high, low=candles.low, close=candles.close, name="hourly candles",
                                 increasing=dict(line=dict(color=UP, width=1), fillcolor=UP), decreasing=dict(line=dict(color=DOWN, width=1), fillcolor=DOWN)), row=1, col=1)
    full = hourly[hourly.index >= start - pd.Timedelta(days=60)]; levels = []
    for j, days in enumerate(p.fast_spans_days):
        fast_h = days * 24; dash = "solid" if j == 0 else "dot"
        for span, nm, w in ((fast_h, "fast", 1.3), (fast_h * p.slow_over_fast, "slow", 1.3)):
            ma = full.ewm(span=span).mean(); ma = ma[ma.index >= start]
            fig.add_scatter(x=ma.index, y=ma, mode="lines", name=f"{days:g}-day speed: {nm} average ({span / 24:g} days)",
                            line=dict(color=INK if nm == "fast" else MUTED, width=w, dash=dash), row=1, col=1)
        lv = tp_levels(px, sg, days, p, hourly_vol).tail(1)              # the current trade of this speed only
        taken = bool(sg[f"tp{days:g}d"].iloc[-1])
        for _, r in lv.iterrows():
            label = (f"{days:g}-day speed: take profit already taken (flat)" if taken else
                     f"{days:g}-day speed: take-profit level, {'long' if r.sign > 0 else 'short'} from {r.entry:,.0f}: about {r.level:,.0f}")
            fig.add_scatter(x=[r.start, r.end], y=[r.level, r.level], mode="lines", name=label, hoverinfo="name",
                            line=dict(color=SERIES[2 + j], width=1.6, dash="dot" if taken else "dash"), row=1, col=1)
            levels.append(r.level)
    d = db["decisions"]; d = d[d["at"] >= start]
    for act, sym, col, nm in (("hold", "circle", MUTED, "decision: hold"), ("sell", "triangle-down", DOWN, "signal fired: sell"),
                              ("buy", "triangle-up", UP, "signal fired: buy")):
        x = d[d.action == act]
        if len(x):
            fig.add_scatter(x=x["at"], y=x.arrival_price, mode="markers", name=nm, marker=dict(symbol=sym, size=14 if act != "hold" else 7, color=col,
                            line=dict(width=1.5, color=INK if act != "hold" else "white")), customdata=np.c_[x.target_qty, x.reason],
                            hovertemplate="%{x}<br>arrival mid %{y:,.1f}<br>target %{customdata[0]:,.0f} USD<br>%{customdata[1]}<extra></extra>", row=1, col=1)
    if len(slip):
        fig.add_scatter(x=slip.time, y=slip.avg_fill, mode="markers", name="fill (average price)", marker=dict(symbol="x", size=11, color=INK),
                        customdata=np.c_[slip.slippage_bp, slip.usd], hovertemplate="%{x}<br>fill %{y:,.2f}<br>%{customdata[1]:,.0f} USD"
                        "<br>slippage %{customdata[0]:+.2f} bp<extra></extra>", row=1, col=1)
    fig.add_hline(y=0, line=dict(color=MUTED, width=1), row=2, col=1, exclude_empty_subplots=False)
    for j, days in enumerate(p.fast_spans_days):
        c, col = f"f{days:g}d", SERIES[2 + j]
        tp = sg[f"tp{days:g}d"].astype(bool)
        if tp.any():
            runs = (tp != tp.shift()).cumsum()[tp]                                     # each period in which this speed is flat
            for _, g in tp[tp].groupby(runs):
                fig.add_vrect(x0=g.index[0], x1=g.index[-1], fillcolor=col, opacity=0.12, line_width=0, row=2, col=1, exclude_empty_subplots=False,
                              annotation_text=f"{days:g}-day speed: take profit taken, flat", annotation_position="top right",
                              annotation_font=dict(size=11, color=INK))
        fig.add_scatter(x=sg.index, y=sg[c], name=f"forecast, {days:g}-day speed", mode="lines",
                        line=dict(color=col, width=1.6), row=2, col=1)
    fig.add_scatter(x=sg.index, y=sg.blend, name="blend (the position follows it)", mode="lines",
                    line=dict(color=INK, width=2.4), row=2, col=1)
    fig.add_scatter(x=sg.index, y=100 * sg.ann_vol, name="annual volatility", mode="lines", line=dict(color=INK, width=1.6), showlegend=False, row=3, col=1)
    fig.update_layout(height=1150, hovermode="x unified", margin=dict(t=70, l=80, r=30, b=60), legend=dict(orientation="h", y=-0.06, x=0))
    fig.update_xaxes(rangeslider_visible=False, range=[start, hourly.index[-1]])
    lo, hi = min([candles.low.min()] + levels), max([candles.high.max()] + levels)
    fig.update_yaxes(range=[lo - 0.03 * (hi - lo), hi + 0.03 * (hi - lo)], row=1, col=1)
    for r, t in ((1, "USD"), (2, "forecast (below 0 = short)"), (3, "% a year")):
        fig.update_yaxes(title_text=t, row=r, col=1)

    # since the bot started: its own time axis, so a young account is not squeezed into the edge of a month
    e = eq.copy()
    tg = target_usd[target_usd.index >= (e.index.min() if len(e) else start)]
    fig2 = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08,
                         subplot_titles=("Position in USD: the target from the signal and the position held",
                                         "Profit and loss of the account in BTC since the bot started"))
    fig2.add_scatter(x=tg.index, y=tg, name="target position", mode="lines+markers", line=dict(color=SERIES[0], width=1.6, dash="dot"), row=1, col=1)
    fig2.add_scatter(x=e.index, y=e.position_usd, name="position held", mode="lines", line=dict(color=INK, width=2, shape="hv"), row=1, col=1)
    if len(e):
        fig2.add_scatter(x=e.index, y=e.equity_btc - e.equity_btc.iloc[0], name="P&L", mode="lines", line=dict(color=INK, width=1.6), fill="tozeroy",
                         fillcolor="rgba(120,120,120,0.15)", showlegend=False, hovertemplate="%{x}<br>%{y:+.6f} BTC<extra></extra>", row=2, col=1)
    fig2.update_layout(height=560, hovermode="x unified", margin=dict(t=60, l=80, r=30, b=40), legend=dict(orientation="h", y=-0.12, x=0))
    fig2.update_yaxes(title_text="USD", row=1, col=1); fig2.update_yaxes(title_text="BTC", row=2, col=1)

    now = datetime.now(timezone.utc)
    last = db["decisions"].iloc[-1] if len(db["decisions"]) else None
    if last is not None:
        mins = (now - last["at"]).total_seconds() / 60
        fired = last.action != "hold" and mins < 120
        banner = (f'<div class="banner {"fired" if fired else "calm"}"><b>{"Signal fired: " + last.action.upper() if fired else "Last decision: " + last.action}</b>'
                  f" at {last['at']:%Y-%m-%d %H:%M} UTC, {mins:.0f} minutes ago; target {last.target_qty:,.0f} USD; {html.escape(str(last.reason))}</div>")
    else:
        banner = '<div class="banner calm">No decision yet</div>'
    now_row = sg.iloc[-1]
    tiles = "".join(f'<div class="tile"><div class="k">{k}</div><div class="v">{v}</div></div>' for k, v in (
        ("Blend now", f"{now_row.blend:+.2f}"), ("Annual volatility", f"{100 * now_row.ann_vol:.0f}%"),
        ("Target", f"{target_usd.iloc[-1]:,.0f} USD"), ("Held", f"{eq.position_usd.iloc[-1]:,.0f} USD" if len(eq) else "n/a"),
        ("P&L since start", f"{(eq.equity_btc.iloc[-1] - eq.equity_btc.iloc[0]):+.6f} BTC" if len(eq) else "n/a"),
        ("Average slippage", f"{slip.slippage_bp.mean():+.2f} bp" if len(slip) else "no fills")))
    tbl = slip.assign(time=slip.time.dt.strftime("%Y-%m-%d %H:%M")).round({"arrival_mid": 2, "avg_fill": 2, "slippage_bp": 2, "fee_btc": 8}).to_html(index=False) if len(slip) else "<p>No fills yet.</p>"
    ev = db["events"].to_html(index=False) if len(db["events"]) else "<p>None.</p>"
    dbview = inspect_db()
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta http-equiv="refresh" content="60">
<title>Trend bot dashboard</title><style>
body{{font-family:system-ui,Segoe UI,sans-serif;margin:16px;background:#fff;color:#1f2328}} h1{{font-size:20px;margin:0 0 8px}} h2{{font-size:16px}}
.banner{{padding:10px 14px;border-radius:6px;margin:8px 0 12px}} .calm{{background:#eef2f6}}
.fired{{background:#fff4e5;border:2px solid #d97706;animation:flash 1s ease-in-out 6}} @keyframes flash{{50%{{background:#fde68a}}}}
.tiles{{display:flex;flex-wrap:wrap;gap:10px;margin:0 0 10px}} .tile{{border:1px solid #d8dee4;border-radius:6px;padding:8px 12px;min-width:140px}}
.k{{color:#57606a;font-size:12px}} .v{{font-size:18px;font-weight:600}}
table{{border-collapse:collapse;font-size:13px}} td,th{{border-bottom:1px solid #d8dee4;padding:4px 10px;text-align:right}} th{{color:#57606a}}
.note{{color:#57606a;font-size:13px;max-width:950px}}</style></head><body>
<h1>Trend bot: market, signal, sizing, position, P&amp;L</h1><div class="note">Written {now:%Y-%m-%d %H:%M} UTC from the bot's database and Deribit's public prices; the last {a.days} days. Testnet account: the signal uses mainnet prices, the trades fill on the testnet. The page reloads every minute; a scheduled task rewrites it every five minutes (README), or rerun <code>python -X utf8 -m capstone.tools.dashboard</code>.</div>
{banner}<div class="tiles">{tiles}</div>{fig.to_html(full_html=False, include_plotlyjs="cdn")}<h2>Since the bot started</h2>{fig2.to_html(full_html=False, include_plotlyjs=False)}
<h2>Trades and slippage</h2><div class="note">Slippage: the average fill against the order book's mid when the decision was taken, in basis points; positive is a cost. Fees are separate.</div>{tbl}
<h2>Recent warnings</h2>{ev}
<h2>The database</h2><div class="note">The latest rows of each table of <code>capstone/data/capstone.db</code>, newest first, read-only. Click a table to open it.</div>{dbview}</body></html>"""
    OUT.write_text(page, encoding="utf-8")
    print("written", OUT, "| decisions", len(db["decisions"]), "| fills", len(db["fills"]), "| candles", len(candles),
          "| last slippage", f"{slip.slippage_bp.iloc[-1]:+.2f} bp" if len(slip) else "none")


if __name__ == "__main__":
    main()
