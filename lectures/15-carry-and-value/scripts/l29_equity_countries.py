"""Lecture 15: a cross-country equity group (correction of 2026-11-16), monthly, like the bond group (l29_bonds_g10).
Markets: SPY (US) and iShares MSCI country ETFs (l29_fetch_country_etfs). Return over cash, hedged into dollars:
    local return = (1 + dollar total return) / (1 + currency return) - 1, minus local cash (OECD 3-month rate of the month before);
    euro members use the euro and euro cash; Hong Kong (pegged) is taken in dollars against US cash.
Value: the price in local currency (ETF price without distributions / dollars per unit of currency) against its 10-year trend line, z (rule);
AQR's construction (against the average 4.5 to 5.5 years earlier) as the check against AQR's equity-index value factor.
Carry (user): US = S&P 500 earnings yield (Shiller, six months' delay) minus the real bill rate; elsewhere the dividend yield (past 12 months'
distributions / price, a labelled compromise) minus the real local cash rate; real = cash minus the past 12 months' CPI inflation (OECD via FRED,
used two months later). Machinery: l29_bonds_g10.stream (weights / 36-month volatility, 5 bp, yearly at 10%)."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l29 as L, l29_bonds_g10 as G
ETF = L.RAW / "l29_long" / "country_etfs"
FUNDS = {"SPY": "US", "EWJ": "JP", "EWG": "DE", "EWU": "GB", "EWC": "CA", "EWA": "AU", "EWL": "CH", "EWQ": "FR", "EWI": "IT", "EWP": "ES",
         "EWD": "SE", "EWN": "NL", "EWH": "HK", "EWK": "BE", "EWO": "AT"}
EURO = {"DE", "FR", "IT", "ES", "NL", "BE", "AT"}
CCY = {"JP": "JPY", "GB": "GBP", "CA": "CAD", "AU": "AUD", "CH": "CHF", "SE": "SEK"}
CASH = {"US": "US", "JP": "JP", "GB": "GB", "CA": "CA", "AU": "AU", "CH": "CH", "SE": "SE", "HK": "US"}


def monthly(t, kind):
    x = pd.read_csv(ETF / f"{t}_{kind}.csv", index_col=0, parse_dates=True).iloc[:, 0]
    if kind == "div":
        m = x.resample("ME").sum()
    else:
        m = x.resample("ME").last()
    m.index = m.index.to_period("M"); return m


def cpi_inflation(c):
    """Past 12 months' CPI change, used two months later (OECD via FRED; quarterly for Australia, carried forward)."""
    for sid in (f"CPALTT01{c}M659N", f"CPALTT01{c}Q659N"):
        try:
            x = L.FX.fred(sid) / 100
            x = x.resample("ME").last().ffill(limit=3) if "Q659" in sid else x
            x.index = x.index.to_period("M"); return x.shift(2)
        except Exception:
            continue
    raise RuntimeError(c)


def data():
    S, _, _ = L.FX.build(); S = S.resample("ME").last(); S.index = S.index.to_period("M")
    cash3 = {k: L.FX.fred(f"IR3TIB01{v}M156N") / 100 for k, v in {"US": "US", "EZ": "EZ", **{c: c for c in ("JP", "GB", "CA", "AU", "CH", "SE")}}.items()}
    for k in cash3: cash3[k].index = cash3[k].index.to_period("M")
    R, P, DY, CASH_, INF = {}, {}, {}, {}, {}
    for t, c in FUNDS.items():
        adj, close, div = monthly(t, "adj"), monthly(t, "close"), monthly(t, "div").reindex(monthly(t, "close").index).fillna(0)
        fx = S["EUR"] if c in EURO else (S[CCY[c]] if c in CCY else None)
        r_usd = adj.pct_change()
        r_loc = r_usd if fx is None else (1 + r_usd) / (1 + fx.reindex(adj.index).pct_change()) - 1
        cash = cash3["EZ"] if c in EURO else cash3[CASH[c]]
        R[c] = r_loc - cash.reindex(adj.index).shift(1) / 12
        P[c] = close if fx is None else close / fx.reindex(close.index)
        DY[c] = div.rolling(12, min_periods=12).sum() / close
        CASH_[c] = cash.reindex(close.index)
        INF[c] = cpi_inflation("US" if c == "HK" else c).reindex(close.index)
    return pd.DataFrame(R), pd.DataFrame(P), pd.DataFrame(DY), pd.DataFrame(CASH_), pd.DataFrame(INF)


def us_earnings_yield(index):
    sh = L.shiller(); E = sh["E"].copy(); E.index = (E.index + pd.offsets.MonthBegin(6)).to_period("M")
    p = sh["P"].copy(); p.index = p.index.to_period("M")
    return (E.reindex(index) / p.reindex(index))


if __name__ == "__main__":
    R, P, DY, CASH_, INF = data()
    real = CASH_ - INF
    carry = DY - real
    carry["US"] = us_earnings_yield(carry.index) - real["US"]
    print("first month with a return:", {c: str(R[c].first_valid_index()) for c in R})
    print("median carry 2006-2022:", (carry.loc["2006":"2022"].median() * 100).round(1).to_dict())
    A = G.aqr(); S0, E0 = "2006-01", "2022-10"
    vol = R.rolling(36, min_periods=24).std() * np.sqrt(12)
    lp = np.log(P)
    sig = {"value, AQR's construction": G.rank_centred(-(lp - lp.shift(54).rolling(13).mean())),
           "value, our rule (10-year line, z)": G.rank_centred(L.trend_gap(lp, 10)),
           "carry, rank": G.rank_centred(carry),
           "carry, score": (G.zrow(carry) + G.zrow(carry / vol)) / 2}
    out = {}
    for k, w in sig.items():
        s = G.stream(w, R).loc[S0:E0]; out[k] = s
        extra = f", corr with AQR {pd.concat([s, A['VALLS_VME_EQ']], axis=1).dropna().corr().iat[0, 1]:+.2f} (AQR {G.sharpe_m(A['VALLS_VME_EQ'].loc[S0:E0]):+.2f})" if k.startswith("value") else ""
        print(f"{k:36s} Sharpe {G.sharpe_m(s):+.2f}{extra}; 2006-2026: {G.sharpe_m(G.stream(w, R).loc[S0:]):+.2f}")
    pd.DataFrame(out).to_timestamp(how="end").to_parquet(L.RAW / "l29_equity_countries.parquet")
