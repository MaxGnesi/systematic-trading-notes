# Daily 10-year government bond yields: sources

Downloaded 2026-11-16. Each output file `<CC>.csv` has the columns `date,yield`. Dates are ISO and yields are in percent. Rows are sorted, with one row per observation the source publishes and no blank values. Raw downloads are in `raw/<CC>/`. Alternative definitions are in `alt/`. The parsing script is `build_daily.py`, run as `python -I build_daily.py <this folder>`.

None of the series is clipped or smoothed. Values that the sources mark as missing (".", "na", "-", empty) are dropped, and nothing is filled in.

| CC | Definition | First | Last | Rows | Frequency |
|---|---|---|---|---|---|
| DE | Zero-coupon (Svensson), 10.0y residual maturity | 1997-08-07 | 2026-11-13 | 7,431 | Daily |
| GB | Nominal zero-coupon, 10y (BoE) | 1982-01-04 | 2026-11-11 | 11,339 | Daily |
| CA | Zero-coupon, 10y (BoC) | 1986-01-02 | 2026-10-28 | 10,023 | Daily |
| AU | Interpolated 10y Australian Government bond yield | 1995-01-03 | 2026-11-11 | 8,034 | Daily |
| NZ | **Not obtained** (see below) | – | – | – | – |
| NO | 10y synthetic yield (to 2018), then 10y generic yield | 1985-01-04 | 2026-11-13 | 9,546 | Weekly to mid-1989, daily from 1990 |
| SE | 10y government bond yield (Riksbank) | 1987-01-02 | 2026-11-13 | 9,991 | Daily |
| CH | Spot (zero-coupon) rate, Confederation bonds, 10y | 1988-01-04 | 2026-10-30 | 7,848 | Weekly 1988–1997, daily from 1998 |
| JP | JGB constant-maturity 10y (MoF par-yield curve) | 1986-07-05 | 2026-10-30 | 9,969 | Daily (Saturdays to Jan 1989) |

## DE: Germany
- **Source:** Deutsche Bundesbank statistics API: `https://api.statistiken.bundesbank.de/rest/download/BBSIS/D.I.ZST.ZI.EUR.S1311.B.A604.R10XX.R.A.A._Z._Z.A?format=csv&lang=en`
- **Series:** BBSIS.D.I.ZST.ZI.EUR.S1311.B.A604.R10XX.R.A.A._Z._Z.A, "Term structure of interest rates on listed Federal securities (method by Svensson) / residual maturity of 10.0 years / daily data". This is a **zero-coupon** yield read from the fitted Svensson curve.
- **Coverage:** 1997-08-07 to 2026-11-13, 7,431 rows, daily. There are no gaps longer than 10 days.
- **Caveats:** The daily curve starts in August 1997, and earlier dates in the file are empty (`.`). The Bundesbank publishes a monthly version of this curve going back further, but it was not downloaded.

## GB: United Kingdom
- **Source:** Bank of England IADB: `https://www.bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp?csv.x=yes&Datefrom=01/Jan/1963&Dateto=now&SeriesCodes=IUDMNZC&CSVF=TN&UsingCodes=Y&VPD=Y&VFD=N`. The same URL with `SeriesCodes=IUDMNPY` gives the par series. The database rejects a From date earlier than 1963.
- **Series used:** **IUDMNZC**, the daily 10-year nominal **zero-coupon** gilt yield from the BoE fitted curve. It was chosen because it starts in 1982, compared with 1993 for the par series.
- **Coverage:** 1982-01-04 to 2026-11-11, 11,339 rows, daily, with no gaps longer than 10 days.
- **Alternative:** `alt/GB_par.csv` holds **IUDMNPY**, the 10-year nominal **par** yield, from 1993-11-01 to 2026-11-11 (8,347 rows). On common dates, zero-coupon minus par averages -0.02 pp, with a mean absolute difference of 0.06 pp.

## CA: Canada
- **Source used:** the Bank of Canada zero-coupon yield curves. The CSV comes from the form on `https://www.bankofcanada.ca/rates/interest-rates/bond-yield-curves/`, which submits to `https://www.bankofcanada.ca/stats/results/csv?lookupPage=lookup_yield_curve.php&startRange=1986-01-01&searchRange=all`. The download holds every maturity from 0.25 to 30 years.
- **Series:** column **ZC1000YR**, the 10-year **zero-coupon** yield. The source gives it in decimal form, and it was multiplied by 100.
- **Coverage:** 1986-01-02 to 2026-10-28, 10,023 rows, daily.
- **Caveats:**
  - The BoC updates this file weekly, with about a two-week lag.
  - Days without bond-pricing data are marked "na", mostly in 1986–1990 (about 210–245 observations per year then). The largest gap runs from 1989-02-23 to 1989-03-31.
  - **1993-11-26 = 6.31%** is a one-day outlier: neighbouring days are about 7.07% and 6.93%. It is left as published and should be checked before use.
- **Alternative:** `alt/CA_benchmark.csv` holds the BoC Valet series **BD.CDN.10YR.DQ.YLD**, "Benchmark bond yield, 10-year" (Government of Canada 10-year **benchmark** bond). It comes from `https://www.bankofcanada.ca/valet/observations/BD.CDN.10YR.DQ.YLD/csv` and runs from 2001-01-02 to 2026-11-12 (6,467 rows). On common dates, zero-coupon minus benchmark averages +0.065 pp, and the daily changes correlate at 0.987. Valet has no longer daily 10-year series.

## AU: Australia
- **Source:** Reserve Bank of Australia, table F2:
  - `https://www.rba.gov.au/statistics/tables/csv/f2-data.csv` covers 2013-05-20 onwards.
  - `https://www.rba.gov.au/statistics/tables/xls-hist/f02dhist.xls` covers 1995-01-03 to 2013-05.
- **Series:** **FCMYGBAG10D**, "Australian Government 10 year bond". It is an interpolated yield on Australian Government bonds at 10 years: the midpoint of bid and offer quotations at close of business.
- **Coverage:** 1995-01-03 to 2026-11-11, 8,034 rows, daily, with no gaps longer than 10 days. The historical file supplies dates before the first date of the current file. The two files do not overlap on any date with values, so the join was not cross-checked.
- **Caveats:**
  - The RBA site returns HTTP 403 to plain curl, so both files were retrieved with Claude Code's web-fetch tool.
  - RBA table F2 starts in 1995. Earlier daily data were not found on this table.

## NZ: New Zealand (NOT OBTAINED)
- The RBNZ website blocks automated access. Every request, including the B2 file URLs under `https://www.rbnz.govt.nz/-/media/project/sites/rbnz/files/statistics/series/b/b2/` (`hb2-daily.xlsx`, `hb2-daily-close.xlsx`), returns HTTP 403 with "Your access to the Reserve Bank website has been restricted". The web-fetch tool also gets 403. No workaround was attempted.
- **Suggested fix (free):** open the RBNZ "Wholesale interest rates (B2)" page in a normal browser and save the daily files, "B2 Daily (1985–2017)" and "B2 Daily (2018–current)", into `raw/NZ/`. The 10-year government bond column can then be parsed in the same way as the other countries. According to the RBNZ, selected B2 series start in 1985. In August 2025 the RBNZ changed the B2 data source to the NZ Financial Markets Association.
- **Fallback:** the existing monthly FRED/OECD file `IRLTLT01NZM156N` in `..\` holds monthly values, not daily data. It has not been substituted here.

## NO: Norway
- **Sources:** Norges Bank.
  - (1) Synthetic yields, no longer updated, from `https://www.norges-bank.no/contentassets/f851e16643634e72a63b13967e0e463e/government-bonds-synthetic-business-day.xlsx?v=18112022125538`, sheet "10 years". These ran from 1985 to 2021-06-30 and were interpolated or extrapolated from few bonds.
  - (2) Open data API, `https://data.norges-bank.no/api/data/GOVT_GENERIC_RATES/B.10Y.GBON?format=csv&startPeriod=1980-01-01&locale=en`, giving **generic** 10-year yields from 2019-01-02. These are based on the on-the-run bond with a residual maturity near 10 years.
- **Splice:** the synthetic series up to 2018-12-31, then the generic series from 2019-01-02. In the 621-day overlap (2019-01-02 to 2021-06-30), synthetic minus generic averages +0.001 pp, with a mean absolute difference of 0.015 pp and a maximum of 0.061 pp.
- **Coverage:** 1985-01-04 to 2026-11-13, 9,546 rows.
- **Caveats:**
  - **Weekly** observations (mostly Fridays) run from 1985 to mid-1989. Data are daily from mid-1989 on, with full years from 1990.
  - The 1985–1989 period has gaps: 1986-10-24 to 1987-01-02 (70 days), plus two gaps of 14 days.
  - Definition change at 2019: synthetic (interpolated) yield, then generic (benchmark-like) yield.

## SE: Sweden
- **Source:** Sveriges Riksbank SWEA API: `https://api.riksbank.se/swea/v1/Observations/SEGVB10YC/1980-01-01` (JSON).
- **Series:** **SEGVB10YC**, the Swedish government bond yield for the 10-year benchmark maturity.
- **Coverage:** 1987-01-02 to 2026-11-13, 9,991 rows, daily.
- **Caveats:**
  - There is a gap from 1990-01-22 to 1990-02-19 (28 days), which leaves 231 observations in 1990.
  - The large moves in 1992 (for example +1.01 pp on 1992-11-19) belong to the ERM crisis and are real.

## CH: Switzerland
- **Source:** Swiss National Bank data portal API, cube **rendeiduebd** ("Bond yields (spot rates)"): `https://data.snb.ch/api/cube/rendeiduebd/data/csv/en?dimSel=D0(CHF),D1(10J)&fromDate=1980-01-01&toDate=2026-12-31`
- **Series:** D0 = CHF (Swiss Confederation bond issues), D1 = 10J (10 years). This is a **spot (zero-coupon)** interest rate.
- **Coverage:** 1988-01-04 to 2026-10-30, 7,848 rows. The cube was published 2026-11-02 and is updated monthly, so the last date lags.
- **Caveats:**
  - Data are **weekly (Mondays plus some month-ends) from 1988 to 1997**, about 61–64 observations per year. They are daily from 1998.
  - The older cube **rendoblid** (raw copy in `raw/CH/rendoblid.csv`) holds the same 10-year series (code 10J0), but it stopped at 2025-07-31 (publication of 2025-09-01). It is not used.

## JP: Japan
- **Source:** Ministry of Finance Japan, JGB interest rate historical data: `https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/historical/jgbcme_all.csv`
- **Series:** column **10Y**, the constant-maturity yield read from the MoF yield curve, which is based on par yields of JGBs.
- **Coverage:** 1986-07-05 to 2026-10-30, 9,969 rows, daily.
- **Caveats:**
  - The file starts in 1974, but the 10-year column is empty until July 1986.
  - **Saturday observations** appear until 1989-01-28 (70 rows), because the market traded on Saturdays then.
  - This file stops at month-end (2026-10-30). The current month is in the MoF's separate file `jgbcme.csv`, which was not downloaded.

## Comparability notes
- **Definitions differ.** DE, GB, CA and CH are zero-coupon (spot) rates from fitted curves. JP is a constant-maturity par-curve yield. AU is an interpolated yield. SE and NO (from 2019) are benchmark or generic bond yields. These differences matter little for daily changes but can shift levels by a few basis points.
- **Last dates differ** because the sources update on different schedules, from 2026-10-28 (CA) to 2026-11-13 (DE, NO, SE).
