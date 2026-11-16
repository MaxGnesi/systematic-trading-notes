"""Lecture 29 §5.4: value from fundamentals (plan entries of 2026-11-16, fixed before the data were loaded), monthly, signals known at the end of
the month before the position (G.stream shifts by one month on top of the delays below).
Bonds: real yield = 10-year yield - past 12 months' CPI inflation (used two months later), ranked across countries by level.
Currencies: half the PPP gap at its level (ln of local currency per dollar over the World Bank PPP factor, the year's value used from the July
after; the euro uses Germany's), z across the group; half the real exchange rate against its 10-year trend line (as §5).
Equities: yield gap = earnings yield (S&P 500: ten-year average real earnings, six months' delay, over the real price) or dividend yield (others)
minus the real 10-year yield of the same country; z against its own 10-year history.
Commodities: half inventories against the same calendar month's average of the previous five years (EIA crude and gas, month-end, used a month
later; USDA US stocks-to-use, the marketing year's value used from the month after it ends), low = long; half the real price (World Bank / US CPI)
against its own 20-year history; gold and cocoa the real price only.
Caveats: PPP and USDA data are revised history (no point-in-time vintages). Output: results/value_fund.json, printed table."""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); import l29_combined as M, l29_bonds_g10 as G, l29_equity_countries as Q, l29_grids as Gr, l29 as L
FD = L.RAW / "l29_fundamentals"; A, B = "2006-01", "2022-10"
PPP_ISO = {"EUR": "DEU", "JPY": "JPN", "GBP": "GBR", "CHF": "CHE", "CAD": "CAN", "AUD": "AUS", "NZD": "NZL", "NOK": "NOR", "SEK": "SWE"}


def monthly_index(x):
    x.index = pd.PeriodIndex(x.index, freq="M"); return x


def infl(c):
    return Q.cpi_inflation(c)                                                    # already used two months later


def bonds_real(Y):
    I = pd.DataFrame({c: infl(c) for c in Y}).reindex(Y.index)
    return Y - I


def fx_value(Gs):
    S, _, _ = L.FX.build(); S = S.resample("ME").last(); S.index = S.index.to_period("M")     # dollars per unit of currency
    P = pd.read_csv(FD / "ppp.csv", index_col=0)
    ppp = {}
    for c, iso in PPP_ISO.items():
        s = P[iso].dropna(); idx = pd.PeriodIndex([pd.Period(f"{int(y) + 1}-07", "M") for y in s.index])   # year y used from July of y+1
        ppp[c] = pd.Series(s.to_numpy(), idx).reindex(S.index, method="ffill")
    ppp = pd.DataFrame(ppp)
    gap = np.log((1 / S[list(PPP_ISO)]) / ppp)                                   # > 0: weaker than PPP = cheap
    return (G.zrow(gap) + G.zrow(Gs["fx"]["V"].reindex(gap.index))) / 2


def equity_value(Gs):
    Re, Pp, DY, CASH_, INF = Q.data()
    sh = L.shiller(); cpi = sh["P"] * 0 + L.shiller()["P"]                        # placeholder to keep index
    raw = pd.read_excel(L.RAW / "l29_shiller_ie_data.xls", sheet_name="Data", header=None, skiprows=8).iloc[:, [0, 7, 10]]
    raw.columns = ["date", "real_p", "real_e"]; raw = raw[pd.to_numeric(raw["date"], errors="coerce").notna()]
    d = raw["date"].astype(float); yr = d.astype(int); mo = ((d - yr) * 100).round().astype(int)
    raw.index = pd.PeriodIndex(pd.to_datetime(dict(year=yr, month=mo, day=1)), freq="M"); raw = raw[["real_p", "real_e"]].apply(pd.to_numeric, errors="coerce")
    e10 = raw["real_e"].shift(6).rolling(120, min_periods=110).mean()            # ten years of real earnings, six months' delay
    ey_us = (e10 / raw["real_p"]).reindex(DY.index)
    LT = {"US": "US", "JP": "JP", "DE": "DE", "GB": "GB", "CA": "CA", "AU": "AU", "CH": "CH", "FR": "FR", "IT": "IT", "ES": "ES", "SE": "SE", "NL": "NL", "BE": "BE", "AT": "AT", "HK": "US"}
    y10 = pd.DataFrame({c: G.fred(f"IRLTLT01{k}M156N") for c, k in LT.items()}) / 100; y10.index = y10.index.to_period("M")
    real10 = y10.reindex(DY.index) - INF
    gap = DY.copy(); gap["US"] = ey_us; gap = gap - real10
    z = (gap - gap.rolling(120, min_periods=96).mean()) / gap.rolling(120, min_periods=96).std()
    return z


def commodity_value():
    def stocks(f, col="value"):
        x = pd.read_csv(FD / f, index_col=0, parse_dates=True).iloc[:, 0].astype(float); m = x.resample("ME").last(); m.index = m.index.to_period("M"); return m
    inv = {}
    for t, f in (("nymex-cl", "crude_stocks.csv"), ("nymex-ng", "gas_storage.csv")):
        m = stocks(f); avg = sum(m.shift(12 * k) for k in range(1, 6)) / 5     # same calendar month, previous five years
        inv[t] = (m / avg - 1).shift(1)                                           # month-end value used a month later
    gr = pd.read_csv(FD / "grains_stocks_to_use.csv"); gr = gr[gr["region"].str.lower().str.contains("united states")]
    endm = {"corn": 8, "soybeans": 8, "wheat": 5}                                  # marketing years end in August (corn, soybeans) or May (wheat)
    for t, name in (("cbot-corn", "corn"), ("cbot-soybeans", "soybeans"), ("cbot-wheat", "wheat")):
        g = gr[gr["commodity"].str.lower().str.contains(name)].set_index("market_year")["stocks_to_use"].sort_index()
        dev = g / g.shift(1).rolling(5).mean() - 1
        idx = pd.PeriodIndex([pd.Period(f"{int(y) + 1}-{endm[name]:02d}", "M") + 1 for y in dev.index])   # used from the month after the year ends
        inv[t] = pd.Series(dev.to_numpy(), idx)
    days = pd.period_range("1990-01", "2026-10", freq="M")
    inv = pd.DataFrame({k: v[~v.index.duplicated()].reindex(days, method="ffill") for k, v in inv.items()})
    W = pd.read_csv(L.RAW / "l29_long" / "wb_commodities_monthly.csv", index_col=0, parse_dates=True); W.index = W.index.to_period("M")
    cpi = L.fred_local("CPIAUCSL"); cpi.index = cpi.index.to_period("M")
    real = np.log(W[L.COMMOD].div(cpi.reindex(W.index), axis=0)).shift(1)        # monthly average, used the month after
    rv = -(real - real.rolling(240, min_periods=200).mean()) / real.rolling(240, min_periods=200).std()
    a = G.zrow(-inv.reindex(rv.index)); b = G.zrow(rv)
    return pd.concat([a, b]).groupby(level=0).mean() if False else (a.add(b, fill_value=np.nan) / 2).fillna(b)


if __name__ == "__main__":
    Gs = M.groups()
    Y, C = G.data()
    F = {"bonds": bonds_real(Y), "fx": fx_value(Gs), "equity": equity_value(Gs), "commod": commodity_value()}
    tf = M.compound(pd.read_parquet(L.RAW / "l29_trend_futures_fixed.parquet")["ret"]); te = M.compound(pd.read_parquet(L.L28.OUT / "l28_base.parquet")[("etf", "ret")].dropna())
    out = {}
    for name, V in (("price (rule)", {g: Gs[g]["V"] for g in Gs}), ("fundamental", F)):
        S = pd.DataFrame({g: G.stream(G.rank_centred(V[g].reindex(Gs[g]["R"].index)), Gs[g]["R"]) for g in Gs}); tot = M.scale_total(S.mean(axis=1, skipna=True))
        row = {g: G.sharpe_m(S[g].loc[A:B]) for g in S}
        for pn, (tr, a, b) in {"2006-2022": (tf, A, B), "2013-2026": (te, "2013-01", "2026-10")}.items():
            s = tot.loc[a:b]; c = M.with_trend(s, tr.loc[a:b])
            row[pn] = dict(value=G.sharpe_m(s), corr_trend=float(pd.concat([s, tr], axis=1).dropna().corr().iat[0, 1]), trend=G.sharpe_m(tr.loc[c.index]), with_trend=G.sharpe_m(c))
        out[name] = row
        print(name, {g: round(row[g], 2) for g in S}, "|", {pn: {k: round(v, 2) for k, v in row[pn].items()} for pn in ("2006-2022", "2013-2026")})
    print("coverage, first month with a signal:", {g: str(F[g].dropna(how="all").index[0]) for g in F})
    (HERE.parent / "results" / "value_fund.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
