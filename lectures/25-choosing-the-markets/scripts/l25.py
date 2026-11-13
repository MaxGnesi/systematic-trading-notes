"""Settings and helpers shared by the Lecture 25 scripts. PORTFOLIO_DATA: folder with etf_daily.csv (written by l25_fetch.py; default data/portfolio
in the repository, which is not committed); L25_RESULTS: where results are written (default results/ next to this folder)."""
import os
from pathlib import Path
import numpy as np, pandas as pd

LECTURE = Path(__file__).resolve().parents[1]; REPO = LECTURE.parents[1]
DATA = Path(os.environ.get("PORTFOLIO_DATA", REPO / "data" / "portfolio")); RAW = DATA / "etf_daily.csv"
RESULTS = Path(os.environ.get("L25_RESULTS", LECTURE / "results")); FIG = LECTURE / "figures"; RESULTS.mkdir(parents=True, exist_ok=True)

UNIVERSE = {
    "US equity": ["SPY", "QQQ", "MDY", "IWM"],
    "US sectors": ["XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY", "XLRE", "XLC"],
    "Developed countries": ["EWA", "EWC", "EWD", "EWG", "EWH", "EWI", "EWJ", "EWK", "EWL", "EWN", "EWO", "EWP", "EWQ", "EWS", "EWU", "EIS", "ENZL"],
    "Emerging countries": ["EWT", "EWY", "EWZ", "EWW", "EZA", "EWM", "FXI", "ECH", "TUR", "THD", "EPU", "EIDO", "EPHE", "INDA", "EPOL", "RSX"],
    "Regions": ["EFA", "EEM", "VGK", "AAXJ"],
    "Themes": ["SMH", "SOXX", "IBB", "XBI", "ARKG", "ICLN", "TAN", "FAN", "LIT", "URA", "NLR", "GDX", "XME", "OIH", "ITB", "ITA", "PAVE", "PHO", "WOOD",
               "KWEB", "HACK", "CIBR", "SKYY", "CLOU", "FINX", "ARKK", "BOTZ", "ROBO", "AIQ", "IRBO", "DRIV", "BLOK", "ESPO", "UFO", "MJ"],
    "Government bonds": ["SHY", "IEI", "IEF", "TLT", "TIP", "BWX", "BNDX"],
    "Credit": ["LQD", "HYG", "EMB", "MBB", "BKLN"],
    "FX": ["UUP", "UDN", "FXE", "FXY", "FXB", "FXA", "FXC", "FXF"],
    "Commodities": ["GLD", "SLV", "PPLT", "DBC", "DBA", "DBB", "USO", "UNG", "CPER"],
    "Real estate": ["VNQ", "RWX"]}
GROUP = {t: g for g, ts in UNIVERSE.items() for t in ts}
SUPER = {"US equity": "Equity", "US sectors": "Equity", "Developed countries": "Equity", "Emerging countries": "Equity", "Regions": "Equity",
         "Themes": "Equity", "Real estate": "Equity", "Government bonds": "Rates", "Credit": "Credit", "Commodities": "Commodities", "FX": "FX"}
CLASS = {t: SUPER[g] for t, g in GROUP.items()}; CLASSES = ("Equity", "Rates", "Credit", "Commodities", "FX")
FUTURES = {"DBC", "DBA", "DBB", "USO", "UNG", "CPER", "UUP", "UDN"}; DEPOSITS = {"FXE", "FXY", "FXB", "FXA", "FXC", "FXF"}   # what the ETF holds

FLOOR = 10e6          # median daily dollar volume over the past year, USD
WIN, MINW = 156, 104  # estimation window and minimum common weeks
PHASE = 26            # trend phase: sign of the trailing 26-week return (about 126 days, as in Lecture 3, section 8.4)
DUP_R, DUP_C = 0.9, 0.85
CEIL = 30             # at most WIN / 5 markets
MIN_PER_CLASS = 2     # added 2026-11-13 after results: below it a class rests on one ETF; filled from below the floor if need be (flagged)
REVIEWS = [pd.Timestamp(f"{y}-12-31") for y in range(2009, 2026)]
SEED = 20261113


def load():
    """Daily adjusted closes and dollar volume; weekly (Friday) log prices, returns, trend phases and trend-positioned returns."""
    raw = pd.read_csv(RAW, header=[0, 1], index_col=0, parse_dates=True)
    close = raw["Close"]; close = close[[t for t in close.columns if close[t].notna().any()]]
    dv = close * raw["Volume"][close.columns]
    L = np.log(close.resample("W-FRI").last()); R = L.diff(); PH = np.sign(L.diff(PHASE)); POS = PH.shift(1) * R
    return close, dv, R, PH, POS


def psd(C):
    """Nearest positive semi-definite correlation matrix by lifting negative eigenvalues (pairwise estimates need not be PSD)."""
    v, E = np.linalg.eigh(C.fillna(0).values); v = np.maximum(v, 1e-8); A = E @ np.diag(v) @ E.T; d = np.sqrt(np.diag(A))
    return pd.DataFrame(A / np.outer(d, d), C.index, C.columns)


def corr(X, mp):
    """Pairwise correlation with mp common weeks; markets lacking overlap are dropped one at a time (most missing pairs first)."""
    C = X.corr(min_periods=mp); C = C.loc[C.notna().any(), C.notna().any()]
    while C.isna().any().any():
        b = C.isna().sum().idxmax(); C = C.drop(index=b, columns=b)
    return psd(C)


def mp_edge(N, T, lmax):
    """Marchenko-Pastur upper edge, variance scaled by 1 - lambda_max / N (Laloux et al., 1999)."""
    return (1 - lmax / N) * (1 + np.sqrt(N / T)) ** 2


def mp_count(C, T):
    v = np.linalg.eigvalsh(C.values); N = len(v)
    return 1 if N == 1 else max(int((v > mp_edge(N, T, v.max())).sum()), 1)


def rmt_clean(C, T):
    v, E = np.linalg.eigh(C.values); edge = mp_edge(len(v), T, v.max()); noise = v < edge; v2 = v.copy(); v2[noise] = v[noise].mean()
    A = E @ np.diag(v2) @ E.T; d = np.sqrt(np.diag(A)); return pd.DataFrame(A / np.outer(d, d), C.index, C.columns), int((~noise).sum()), float(edge)


def enb(C, names=None, w=None):
    """Effective number of bets (Meucci, 2009): exp of the entropy of the principal components' risk shares. w on the correlation matrix =
    inverse-volatility weights; default equal; 'class' = equal risk per class, equal within."""
    names = list(C.index) if names is None else names
    if isinstance(w, str):
        cls = pd.Series({n: CLASS[n] for n in names}); k = cls.nunique(); w = np.array([1 / k / (cls == cls[n]).sum() for n in names])
    w = np.ones(len(names)) / len(names) if w is None else np.asarray(w)
    v, E = np.linalg.eigh(C.loc[names, names].values); p = (E.T @ w) ** 2 * v; p = p[p > 1e-12] / p.sum(); return float(np.exp(-(p * np.log(p)).sum()))


def pdi(C):
    """Portfolio diversification index (Rudin and Morgan, 2006)."""
    v = np.sort(np.linalg.eigvalsh(C.values))[::-1]; r = v / v.sum(); return float(2 * (np.arange(1, len(v) + 1) * r).sum() - 1)


def mean_abs(C, names):
    a = np.abs(C.loc[names, names].values); n = len(a); return float((a.sum() - n) / (n * (n - 1))) if n > 1 else 0.0


def dr_abs(C, names):
    """Diversification ratio with inverse-volatility weights, sign ignored: N / sqrt(sum |rho|)."""
    return len(names) / np.sqrt(np.abs(C.loc[names, names].values).sum())


def concordance(P, a, b):
    """Share of weeks two markets are in the same trend phase, sign ignored (a mirror image is the same bet for a long/short trader)."""
    ok = P[a].notna() & P[b].notna() & (P[a] != 0) & (P[b] != 0); c = (P.loc[ok, a] == P.loc[ok, b]).mean(); return max(c, 1 - c)


def explained(C, sel, targets):
    """Average R-squared of the target markets regressed on the selected ones (from the correlation matrix)."""
    S = [x for x in sel if x in C.index]; T = [x for x in targets if x in C.index]
    if not S or not T: return np.nan
    cts = C.loc[T, S].values; B = np.linalg.solve(C.loc[S, S].values + 1e-8 * np.eye(len(S)), cts.T)
    return float(np.mean(np.minimum(np.sum(cts * B.T, axis=1), 1.0)))   # a selected market explains itself: R-squared 1 up to rounding


def window(R, end):
    X = R[R.index <= end].iloc[-WIN:]; return X.loc[:, X.notna().sum() >= MINW]


def liquidity(dv, end):
    return dv[dv.index <= end].iloc[-252:].median().dropna().to_dict()
