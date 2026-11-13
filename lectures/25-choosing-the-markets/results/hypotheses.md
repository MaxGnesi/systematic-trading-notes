# Lecture 25: hypotheses, fixed before the results

The plan below was fixed on 2026-11-13 before any result was computed (SHA-256 of that first version: 87084dc1…). Addenda 1 and 2 were dated before the runs they govern. Everything designed after seeing results is listed in the log at the end and labelled as such; it was tested out of sample in the same way, but on years that had already been seen by earlier runs, so its evidence is weaker.

## The plan (fixed 2026-11-13, approved before any result)

**Question.** Of 116 US-listed ETFs in 11 classes (2 closed ETFs, RSX and IRBO, are missing from the free data), which form a universe that is diverse and tradable, chosen without looking at any strategy's results?

**Data.** Adjusted closes and volume from Yahoo (local only). Weekly returns, Friday to Friday close; all ETFs close at 16:00 New York time, so the closes are synchronous. Each ETF labelled by what it holds: securities directly, futures (rolls), or deposits (FX).

**No look-ahead: a yearly review.** The universe is set at each year end from the past only. The first review, at the end of 2009, uses 2007-2009 (and earlier data where it exists); an ETF needs 2 years of weekly returns to be considered. At each later review, a market already in stays in; a new ETF joins if it is not redundant with a member (rule below) and passes the liquidity floor. The universe used in any year is therefore known at its start.

**Liquidity floor.** Median daily dollar volume over the past year of at least 10 million USD; a market below it is kept only if no member of its cluster passes, and is flagged.

**Methods** (each run at every review, same inputs):
1. Hierarchical clustering on the distance sqrt(2(1-rho)) (Onnela et al., 2003), linkages average, complete and Ward, cut where markets are correlated above rho* in {0.70, 0.75, 0.80, 0.85, 0.90}; one representative per cluster, the most liquid.
2. The same after cleaning the correlation matrix with random-matrix theory (eigenvalues inside the Marchenko-Pastur bound replaced by their average; Laloux et al., 1999; Plerou et al., 2002).
3. Greedy forward selection: start from the most liquid market, add the one that raises the diversification ratio most (Choueifaty and Coignard, 2008), among markets above the floor, until the ratio stops rising by more than 1%.
4. Graphical lasso (Friedman, Hastie and Tibshirani, 2008): partial correlations; a market whose links all vanish at moderate penalty carries information of its own.
5. Minimum spanning tree (Mantegna, 1999; Onnela et al., 2003): which markets are central, which peripheral.
6. Downside correlation: the correlation in weeks when both markets fall by more than their own one-sigma move, against all weeks (Longin and Solnik, 2001).
7. Effective number of bets (Meucci, 2009) and the portfolio diversification index (Rudin and Morgan, 2006), for the full universe and for each selection.

**Consensus.** The main universe: markets chosen by most of the variants of methods 1 to 3 (15 + 15 + 1 variants), at each review. Methods 4 to 7 describe and check it.

**Checks.**
- Robustness: the number of clusters and the effective number of bets across rho* and linkage; how much the selections of different methods overlap.
- Stability: clusters formed on 2007-2016 compared with 2017-2026 (adjusted Rand index; share of pairs that stay together).
- Out of sample: the effective number of bets and the average correlation of the selected universe in the years after each review, against the full universe and against a random selection of the same size and liquidity.
- Stress: the clusters in sell-off weeks against all weeks.

**Expectations, written before the run.**
1. The 116 ETFs carry far fewer independent bets: the effective number of bets is below 20.
2. Countries, sectors and themes collapse into a few equity clusters at rho* = 0.8; government bonds, gold, the dollar and commodities each stay separate.
3. Cleaning with random-matrix theory leaves the equity clusters and merges some of the small ones.
4. In sell-off weeks equity correlations rise and equity clusters merge further.
5. The selected universe keeps its diversification out of sample better than a random one of the same size.

**Stated limits.** Only surviving ETFs (Elton, Gruber and Blake, 1996): themes are most affected. ETF prices of foreign markets trade at a premium or discount to their holdings while the home market is closed. Volume understates capacity (creation and redemption).

## Addendum 1, 2026-11-13, before any result

**Competing expectation 1 (the user).** The effective number of bets is higher, about 25 to 30. Expectation 1 above (below 20) is kept; the run decides between the two.

**Details the plan left open, fixed now.**
- Estimation window at each review: the trailing 3 years of weekly returns (156 weeks; 2007-2009 at the first review); pairwise correlations need 104 common weeks. If the pairwise matrix is not positive semi-definite, negative eigenvalues are set to a small positive value and the diagonal rescaled to 1 (reported).
- Random-matrix cleaning: Marchenko-Pastur upper edge (1 + sqrt(N/T))^2 with the variance scaled by 1 - lambda_max/N (Laloux et al., 1999); eigenvalues below the edge replaced by their average.
- Ward linkage heights are not correlations; the Ward variants are cut at the same distance sqrt(2(1-rho*)) and read as a coarser grouping.
- Diversification ratio with inverse-volatility weights: DR = N / sqrt(1'R1), so it depends on correlations only.
- Effective number of bets and PDI computed for inverse-volatility weights (equal weights on the correlation matrix). Also reported: the number of eigenvalues above the Marchenko-Pastur edge and the number of clusters at rho* = 0.8.
- Consensus additions: a market picked by more than half of the 31 variants joins if its correlation with every member is below 0.8.
- Downside correlation compared with what a bivariate normal with the same overall correlation gives under the same truncation (conditioning alone changes correlation; Longin and Solnik, 2001; Forbes and Rigobon, 2002).
- Extra control: a random member of each cluster instead of the most liquid one (does the liquidity rule cost diversification?).
- Comparison of methods: each family's selection (raw clustering at 0.8 average linkage, cleaned clustering at 0.8 average linkage, greedy) evaluated out of sample like the consensus, to see whether a mix is needed.

## Addendum 2, 2026-11-13, designed after the first runs (labelled as such), before the factor-based run

Selection within each class by principal variables (Jolliffe, 1972; McCabe, 1984; to be checked at source), one market per factor above the Marchenko-Pastur edge, the same caps, floor, duplicate and leaving rules:
- A, one market per factor: for factor j, the liquid market with the largest absolute loading; factor 1 gives the key market of each class.
- B, explained variance step by step: add the market that raises the share of the class's variance explained by the chosen markets most.
New measure, fixed before the run: the share of each class's variance the chosen markets explain in the next year (average R-squared of the class's markets regressed on the chosen ones), averaged over classes; against random selections of the same count per class and against the greedy diversification selection. Expectation: A and B explain more than random and more than greedy; greedy keeps less overlap.

## Log of changes designed after results (2026-11-13), in order

1. **First run (the plan).** The majority vote kept almost everything (28 markets at the first review, 80 by 2025): the cleaned-matrix variants put every market in its own group (cleaning lowers very high pairwise correlations, so nothing groups above 0.70-0.75), and thresholds of 0.85-0.90 keep most markets. The graphical lasso gave no stable graph (SPY is a portfolio of the sector ETFs; partial correlations are nearly undefined). The vote is dropped; methods are given roles instead.
2. **Class first** (the user): equity, rates, credit, commodities and FX are fixed first; selection runs within each class. Reason: the equal-weight effective number of bets of all 116 is about 1, because 87 are equity; with equal risk per class it is 2.5-3.4.
3. **Duplicates beyond correlation** (the user, Lecture 3, section 8.4): two markets are duplicates only if |rho| >= 0.9 and their 26-week trend phases agree (sign ignored) at least 85% of the time. Greedy diversification on trend-positioned returns was also run ("pos_nocap"); it did not lower next year's overlap and is not kept.
4. **Size rules** (after the user asked for options): slots per class = factors above the Marchenko-Pastur edge in the class; ceiling 30 (156 weeks / 5); members leave if redundant, below the floor or over the cap at two reviews in a row.
5. **Filling the slots** (addendum 2; the user's proposal of key markets for factor 1): compared "dr", "pc", "ev" and "hy". In the first hybrid run the key market was removed as least diversifying (a factor-1 market always is); it is now protected from the over-cap rule only. Chosen: "hy", key market plus greedy diversification.
6. **At least 2 markets per class** (2026-11-13, the user, after results): with the $10 m floor, FX held only UUP from 2018 to 2024 although its cap was 2-3, because the other FX ETFs trade less. A class must not rest on one ETF; when fewer than 2 pass the floor, the most liquid market below it that is not a duplicate is added and flagged as thin, and a member below the floor does not leave while its class has only 2. The cap per class is at least 2. Effect: FX keeps FXE and FXY (both below the floor, flagged) from 2018 on; UUP stays out as a mirror image of FXE (rho -0.95, same phase 86% of weeks).

## Addendum 3, 2026-11-13, before the run: a roadmap for growing capital (the user's proposal)

At the last review (end of 2025), markets are added in three stages as capital grows:
- **Stage 1, core:** the chosen universe (key market + diversify, at least 2 per class).
- **Stage 2, more bets:** within each class, continue the greedy diversification beyond the cap among markets above the USD 10 m floor (sign ignored, duplicates excluded), until a market raises the class's diversification ratio by less than 1%.
- **Stage 3, capacity:** every other market above the floor, grouped with the stage 1-2 member it is most correlated with; a group shares one risk budget and splits its trading.

**Capacity of a market (placeholder for Lecture 28).** Weights: equal risk per class, inverse volatility within (risk only, as the workflow requires), scaled so the portfolio's volatility is 10% a year on the covariance of 2023-2025. Trading: Lecture 9's slow rule traded partially (lambda = 0.1) turns over 2.4 times a year; its heaviest day, a full reversal, trades 2 x lambda = 20% of the position. Limit: a day's trade at most 1% of the market's median daily dollar volume over the past year. Capacity = 1% x volume / (20% x weight); a stage's capacity is the smallest over its markets or groups.
**Diversification of a stage:** the share of the variance of all 116 ETFs (2023-2025) explained by its markets, and the mean |correlation| among them.
**Expectation, written before the run:** stage 2 adds a few markets and a few points of explained variance; stage 3 adds little diversification but raises capacity; the thin currency ETFs bind the capacity of stage 1.
**Result and reading of addendum 3 (2026-11-13).** The expectation on diversification held (stage 2: 6 markets, 75% to 80% explained; stage 3: 57 near-duplicates, mean |correlation| 0.28 to 0.40). Capacity on the ETFs' own screen volume binds at USD 2-3 m, set by the currency ETFs (FXE, FXY), then short bonds (SHY, TIP: low volatility needs large positions). As the user pointed out, an ETF's screen volume misreads the market's size: it understates FX and Treasuries by orders of magnitude (creation and redemption, and the underlying markets are among the deepest), and can overstate niche themes, whose holdings are small. The roadmap is therefore read as the limit of an account trading ETFs on screen; futures and forwards are mentioned as an example of the next step, as different instruments that would have to be measured again.
