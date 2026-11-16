"""Lecture 30: the final portfolio tested on 1990-2005 (plan: results/hypotheses.md), with 2006-2022 for reference.
Rule: trend + carry at equal risk. Rival: trend + carry + value from fundamentals at equal thirds. Yardsticks: trend alone, US equities, 60/40.
The investor's frame: 60/40 with 0/20/30/50% of its risk budget in the rule, at 60/40's volatility. Luck: 1,000 random carry strategies.
Costs: 5 bp (rule), 10 and 20 bp (sensitivity). Output: results/test.json, figures/30_key.png."""
import json, os, sys
from pathlib import Path
import numpy as np, pandas as pd
import plotly.graph_objects as go
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); import l30_data as D
import l29_combined as M, l29_bonds_g10 as G, l29_grids as Gr, l29_value_fund as VF, l29 as L
from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure
RES = Path(os.environ.get("L30_RESULTS", HERE.parent / "results")); RES.mkdir(parents=True, exist_ok=True); FIG = HERE.parent / "figures"
N = int(sys.argv[1]) if len(sys.argv) > 1 else 1000


def total(Gs, W):
    S = pd.DataFrame({g: G.stream(W[g], Gs[g]["R"]) for g in Gs}); return M.scale_total(S.mean(axis=1, skipna=True)), S


def combine(streams, ref):
    """Equal-risk average of streams (each already at 10%), scaled on its past to ref's volatility (expanding, from 12 months)."""
    X = pd.concat(streams, axis=1).dropna(); c = X.mean(axis=1)
    return (c * ref.reindex(c.index).std() / c.expanding(12).std().shift(1)).dropna()


def stats(r):
    s = Gr.stats(r); w = (1 + r).cumprod()
    return {k: float(v) for k, v in s.items()} | dict(ret=float(w.iloc[-1] ** (12 / len(r)) - 1), vol=float(r.std() * np.sqrt(12)),
                                                     skew=float(r.skew()), worst_month=float(r.min()))


def blend(base, add, w):
    a = add * base.std() / add.std(); b = (1 - w) * base + w * a; return b * base.std() / b.std()


if __name__ == "__main__":
    apply_theme(); Gs = D.groups_long(); Y, C = G.data()
    Wc = {g: Gr.sig(Gs[g]["C"], Gs[g]["R"]) for g in Gs}
    carry, Sc = total(Gs, Wc)
    F = {"bonds": VF.bonds_real(Y), "fx": VF.fx_value(Gs), "equity": VF.equity_value(Gs), "commod": VF.commodity_value()}
    value, Sv = total(Gs, {g: G.rank_centred(F[g].reindex(Gs[g]["R"].index)) for g in Gs})
    LO = D.sixty_forty()
    periods = {"1990-2005": (D.trend_1990(), "1990-01", "2005-12"),
               "2006-2022": (M.compound(pd.read_parquet(L.RAW / "l29_trend_futures_fixed.parquet")["ret"]), "2006-01", "2022-10")}
    out = {}
    for pn, (trend, a, b) in periods.items():
        tr = trend.loc[a:b]; cy = carry.loc[a:b]; vl = value.loc[a:b]
        rule = combine([tr, cy], tr); rival = combine([tr, cy, vl], tr); idx = rule.index
        lo = LO.reindex(idx)
        o = {"groups_active": {g: str(Sc[g].loc[a:b].first_valid_index()) for g in Sc},
             "carry_groups": {g: float(G.sharpe_m(Sc[g].loc[a:b])) for g in Sc}, "value_groups": {g: float(G.sharpe_m(Sv[g].loc[a:b])) for g in Sv},
             "corr_carry_trend": float(cy.reindex(idx).corr(tr.reindex(idx))), "corr_rule_6040": float(rule.corr(lo["60/40"])),
             "corr_trend_6040": float(tr.reindex(idx).corr(lo["60/40"])), "corr_rule_equity": float(rule.corr(lo["equity"]))}
        for k, r in (("trend", tr.reindex(idx)), ("carry", cy.reindex(idx)), ("value", vl.reindex(idx)), ("rule: trend + carry", rule),
                     ("rival: + value", rival.reindex(idx)), ("US equities", lo["equity"]), ("60/40", lo["60/40"])):
            o[k] = stats(r.dropna())
        o["investor"] = {f"{int(w * 100)}%": stats(blend(lo["60/40"], rule, w)) for w in (0, 0.2, 0.3, 0.5)}
        out[pn] = o
        print(f"\n{pn}: carry groups {({g: round(v, 2) for g, v in o['carry_groups'].items()})}, corr carry-trend {o['corr_carry_trend']:+.2f}, rule-60/40 {o['corr_rule_6040']:+.2f}")
        for k in ("trend", "carry", "value", "rule: trend + carry", "rival: + value", "US equities", "60/40"):
            x = o[k]; print(f"   {k:20s} Sharpe {x['sharpe']:+.2f} ret {x['ret']:+.1%} maxDD {x['maxdd']:.1%} Calmar {x['calmar']:.2f} Omega {x['omega']:.2f} skew {x['skew']:+.2f}")
        for w, x in o["investor"].items(): print(f"   60/40 with {w:>3s} in the rule: Sharpe {x['sharpe']:.2f} maxDD {x['maxdd']:.1%}")
    # luck baseline on 1990-2005
    tr, a, b = periods["1990-2005"]; rng = np.random.default_rng(30); hold = {g: M.holding(Wc[g]) for g in Wc}; al, co = [], []
    for i in range(N):
        rt, _ = total(Gs, {g: M.markov_signs(Wc[g], hold[g], rng) for g in Wc}); rt = rt.loc[a:b]
        al.append(G.sharpe_m(rt)); co.append(G.sharpe_m(combine([tr.loc[a:b], rt], tr.loc[a:b])))
    ra, rc = out["1990-2005"]["carry"]["sharpe"], out["1990-2005"]["rule: trend + carry"]["sharpe"]
    out["luck_1990_2005"] = dict(carry_beaten=float(np.mean(np.array(al) < ra)), carry_median=float(np.median(al)), carry_p95=float(np.percentile(al, 95)),
                                rule_beaten=float(np.mean(np.array(co) < rc)), rule_median=float(np.median(co)), rule_p95=float(np.percentile(co, 95)))
    print("\nluck, 1990-2005:", {k: round(v, 2) for k, v in out["luck_1990_2005"].items()})
    # costs
    cost = {}
    for bp in (10, 20):
        G.COST = bp / 1e4; c2, _ = total(Gs, Wc); G.COST = 0.0005
        cost[f"{bp} bp"] = {pn: float(G.sharpe_m(combine([tr_.loc[a_:b_], c2.loc[a_:b_]], tr_.loc[a_:b_]))) for pn, (tr_, a_, b_) in periods.items()}
    out["costs"] = cost; print("rule's Sharpe with higher costs on carry:", cost)
    (RES / "test.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    # key chart: 1990-2005, money over time
    o = out["1990-2005"]; tr, a, b = periods["1990-2005"]; rule = combine([tr.loc[a:b], carry.loc[a:b]], tr.loc[a:b]); lo = LO.reindex(rule.index)
    lines = (("60/40 with 30% of its risk in the rule", blend(lo["60/40"], rule, 0.3), SERIES[0], "solid"), ("60/40", lo["60/40"], INK, "solid"),
             ("The rule: trend + carry", rule, SERIES[1], "dot"))
    fig = go.Figure()
    for (name, r, col, dash), dy in zip(lines, (12, -12, 0)):
        w = 100 * (1 + r).cumprod(); x = w.index.to_timestamp(how="end"); st = stats(r)
        fig.add_scatter(x=x, y=w, name=name, line=dict(color=col, width=2.6 if dash == "solid" else 2, dash=dash))
        fig.add_annotation(x=x[-1], y=w.iloc[-1], text=f"<b>{name.split(':')[0]}</b><br>Sharpe {st['sharpe']:.2f} · worst {st['maxdd']:.0%}", showarrow=False,
                           xanchor="left", xshift=8, yshift=dy, align="left", font=dict(size=12, color=col))
    fig.update_yaxes(title_text="value of 100 invested (excess return over cash)")
    fig.update_layout(title="The final portfolio on years it was not built on<br><sup>1990-2005, monthly, after costs; 60/40 = S&P 500 and US 10-year bonds; "
                            "the rule = trend and carry at equal risk; the blend keeps 60/40's volatility</sup>",
                      height=560, width=1250, margin=dict(t=90, l=80, r=230, b=110), legend=dict(orientation="h", y=-0.12, x=0))
    save_figure(fig, os.environ.get("L30_PREFIX", "") + "30_key", FIG)
