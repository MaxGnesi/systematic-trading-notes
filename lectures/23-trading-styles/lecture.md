# Lecture 23: Who Else Trades: Reading Trading Styles from Public Data

*Systematic Trading: Lecture Notes (MSc) · draft, Nov 9, 2026 · Max Gnesi*

Lecture 22 showed that a market's reaction to our order is made by other traders with their own rules. This short lecture asks which of them are at work on Bybit's BTCUSDT perpetual, when and in what conditions, and how much public data can tell, as the bridge to the market-making strategy of Lecture 24: a quoter has to know whom its quotes will meet. The public feed never says who traded, but trading styles leave footprints. Each footprint is first tested in Lecture 22's laboratory market, where the answer is known, then measured on 20 September to 3 November 2025. The hypotheses were fixed before any result was computed, and every change is dated ([results/hypotheses.md](results/hypotheses.md)).

## 1. What we see, and who did it

The idea of the lecture fits in one chart: the same minutes once as the traders sent them, once as the public feed shows them.

![Who else trades: what we see, and who did it](figures/23_key.png)
<sub><b>How to read the figure.</b> <b>Axes.</b> All panels: minutes (x), size of each taker order in BTC, log scale (y). Top: four minutes of Lecture 22's laboratory market, each order coloured by the trader who sent it (invented). Middle: the same orders as the public feed shows them, grey, with our footprint measures: runs of equal orders at regular gaps (orange line), and orders sent within 100 ms after the outside price moved 2 ticks or more their way (crosses); the laboratory's hidden value stands in for the outside price. Bottom: four real minutes of Bybit BTCUSDT on 1 October 2025, in sample, with the same measures; Binance's last trade is the outside price, and a move of 2 bp marks an order. Blue bands: the first 3 s after each whole minute.</sub>

In the laboratory several slicers work at once. The run rule finds one of them, and every order it marks is a slicer's, but it misses the others. Of the orders sent just after the outside price moved, a third are the sniper's. A footprint is a partial and noisy view of a style, and its quality can only be judged where the answer is known. On Bybit the same measures find two runs of 0.01 BTC orders arriving every few seconds for minutes on end, and a burst of large orders, up to 20 BTC, sent within 100 ms of a move on Binance.

The lecture runs as follows:

| § | Step | Question |
|---|---|---|
| 1 | What we see, and who did it | Can trading styles be read from public data at all? |
| 2 | Four footprints | How is each style recognised, and how well, where the answer is known? |
| 3 | What is at work on Bybit | Do snipers, clock traders and slicers leave their footprints here? (H10, H11, H12) |
| 4 | When, and in what conditions | Do the styles come at regular times, and do volatile hours change the mix? (H13, H14) |
| 5 | Runs as they start | Can a slicer be recognised by its third slice, and does the market expect the next? (H16, H17) |
| 6 | What it means for our strategy | What a quoter should watch, and a checklist for reading a market |

## 2. Four footprints

Each style gets the same short card: the footprint, the rule that measures it, what the laboratory showed with the answer known, what the rule misses, and what it means for a quoter. The laboratory and its traders are those of Lecture 22, §2; its results here are on invented data.

| § | Style | Its footprint in public data | Tested in |
|---|---|---|---|
| 2.1 | Slicer (TWAP) | Equal orders at regular gaps | Lecture 22's laboratory, step 4; H12 |
| 2.2 | Clock trader | A burst of flow with the trend just after whole minutes | Step 5; H11 |
| 2.3 | Sniper | Orders sent just after a move elsewhere, in its direction | Step 3; H10 |
| 2.4 | Maker pulling | Quotes cancelled near the best, in bursts | Lectures 18 and 22; Lecture 22, H20a |
| 2.5 | Scalper | An echo at its exit distance; not recognisable | Step 6 |

### 2.1 The slicer

**Key message.** A large order cut into equal slices at a fixed interval leaves a run of identical orders; a run of eight or more is rarely chance, but most slicing goes unseen.

**The rule.** Taker orders of one exact size on one side, eight or more in a row, whose gaps vary by less than a fifth of their mean, at least 1 s apart (H12). Bybit's own TWAP tool slices every 30 s by default.

**With the answer known.** In the laboratory, 93 to 96% of what the rule finds is the slicer's, for gaps exactly regular or randomised by up to a fifth; with no slicer, it finds almost nothing (0.01% of taker size). It finds only about 40% of the slicer's size: slices too small to stand out, and sizes that other traders also use, are missed. A first version with five slices found as much in shuffled data as in real slicing, and was changed before any real data were used ([Lecture 22, step 4](../22-a-market-that-reacts/figures/22_sim_step4.png)).

**What it misses.** Slicers that vary their size, follow volume instead of the clock, or post resting orders. The share it reports is a floor.

**For a quoter.** A slicer is the most benign counterparty there is: steady flow on one side that knows nothing about the next minute. It also pushes the price its way, slice after slice, so a quote against it should lean.

### 2.2 The clock trader

**Key message.** Traders who decide at the close of a bar act together just after whole minutes; their footprint is in the clock, not in their rule.

**The rule.** At each whole minute, taker flow in the direction of the recent trend over the next 3 s, against the same measure at fake minutes 10 to 50 s away (H11a); and the share of quotes wider than one tick in the 2 s before the minute, which rises if market makers expect the burst (H11b).

**With the answer known.** In the laboratory, crowds of trend followers acting at bar closes are found from about 1% of taker size, and a maker that widens before the minute is found clearly. The first version of H11, flow after the mid crosses its average, found nothing even where trend followers were known to trade: others took their flow back at once. That measure was replaced before any real data were used ([Lecture 22, step 5](../22-a-market-that-reacts/figures/22_sim_step5.png)).

**What it misses.** Rules that do not wait for a bar close, and any rule whose direction does not match the simple trend we measure.

**For a quoter.** The seconds after a whole minute bring a burst of one-sided flow. A quote that stands then is filled by traders who move together; a maker may step back or widen before the mark, as H11b asks.

### 2.3 The sniper

**Key message.** A fast trader that sees a move elsewhere first takes the quotes that have not yet caught up; its footprint is timing.

**The rule.** Orders sent within 100 ms after Binance's price moved 2 bp or more in their direction (H10). If they are informed about a price that has already moved, their move afterwards should be larger than other orders' of the same size.

**With the answer known.** In the laboratory a sniper that sees the hidden value first earns from stale quotes, and the maker's margin per BTC falls from 1.15 to 0.36 ticks as its quotes refresh more slowly, from every 0.1 s to every 5 s ([Lecture 22, step 3](../22-a-market-that-reacts/figures/22_sim_step3.png)). The timing rule is a blunt tool: in the key chart, only a third of the orders it marks are the sniper's, because other traders also trade after moves.

**What it misses.** The races themselves: the losers' orders fail and leave no trace in the book (Aquilina, Budish and O'Neill, 2022). And moves elsewhere that come from other venues than Binance.

**For a quoter.** The sniper decides the cost of a stale quote. Every move on Binance is a moment when a resting order on Bybit is wrong and can be taken; refreshing faster than the sniper is the only defence, and it is not cheap.

### 2.4 The maker pulling

**Key message.** Market makers withdraw their quotes when the price moves fast; the withdrawal is visible in the book, and it makes the tail of everyone's cost fatter.

**The rule.** A pull is a book update in which five or more of the best twenty levels on one side lose size that trades do not explain (Lecture 18). On Bybit pulls are in 7% of updates after a quiet second and 79% after a move of more than 5 bp (Lecture 18).

**With the answer known.** In the laboratory a maker with a kill switch steps out after fast moves, and orders arriving while it is out pay twice as much at the median and more than twice in the tail. On Bybit, out of sample, orders of 1 to 5 BTC arriving after the most pulls had a 90th percentile of cost of 1.62 bp against 0.72 after the fewest (Lecture 22, H20a).

**What it misses.** Who pulled: one large maker or many small ones look the same.

**For a quoter.** A maker that pulls is a competitor stepping aside, which is both a risk and a chance: the queue empties, but the fills that come are the ones the others refused.

### 2.5 The scalper: a footprint that cannot be told apart

A scalper joins the best price and exits a few ticks better. In the laboratory its round trips leave an echo, the same size added on the far side at its exit distance, and with one scalper the echo peaks at exactly its gain. But a market maker that leans its quotes and posts a fixed size leaves the same echo at one and two ticks, with no scalper at all. The scalper is a one-level market maker (Silber, 1984), and public data cannot separate the two. It is not tested on Bybit.

## 3. What is at work on Bybit

Three footprints were tested on the 24 out-of-sample days, 11 October to 3 November 2025, with the rules of §2 fixed in sample. Two are clearly there; the third shows a clock, but not the trend crowd it was meant to find.

![What is at work on Bybit: three footprints, out of sample](figures/23_s3_styles.png)
<sub><b>How to read the figure.</b> <b>Axes.</b> Left: order size class in BTC (x), net move of the mid in the order's direction 10 s later, after matched controls, in bp (y); pink: orders sent within 100 ms after Binance's price moved 2 bp or more their way, grey: all other orders. Middle: kind of whole mark (x), the mean over the first 3 s after the mark less the same at fake marks 10 to 50 s after it, in BTC (y); blue: taker flow on the trend's side (H11a), orange: extra taker size on either side. Right: day (x), share of taker size in runs of eight or more equal orders at regular gaps, % on a log scale (y); green: as traded, grey: the same day with sizes shuffled within 5 minutes; shaded: out of sample. Whiskers: 95% bands from 2,000 resamples of the out-of-sample days. Our calculation, Bybit BTCUSDT perpetual.</sub>

**Do orders sent just after a move on Binance move the price more? (H10)** Yes, in every size class. Ten seconds after a sniper-like order the mid has moved 3.0 to 6.5 bp its way, net of matched controls, against 0.4 to 1.8 bp after other orders of the same size; weighted over the classes the difference is 2.7 bp (95% band 2.4 to 3.0). The difference is there already after 1 s (2.7 bp) and still after 60 s (2.2 bp): Bybit catches up with a price that has already moved, and does not give it back. Such orders are 3.4% of taker orders and 9% of taker size. They pay for their speed: 2.3 to 2.5 bp from the mid against 0.2 to 0.8 bp for other orders up to 20 BTC, because they arrive while the book is still moving; the move that follows them is larger still.

**Is there a clock, and does it follow the trend? (H11)** There is a clock, but the trend crowd it was meant to find did not appear. In the first 3 s after a whole minute, taker flow on the side of the trend is no larger than at fake marks (H11a, t = 0.4), and makers do not widen before the minute: quotes wider than one tick are, if anything, slightly rarer in the 2 s before it (H11b, t = −5.5 in the opposite direction). What the clock does bring is volume on both sides: 0.7 BTC more taker size in the first 3 s than at fake marks (t = 6.4), 1.7 BTC at 5-minute marks, 2.7 at quarter-hours and 5.2 at hours, against an average of 2.9 BTC in any 3 s; and the spread widens *after* the mark (t = 4.4), not before. In sample, flow did lean with the trend at 5-minute and 15-minute marks (t = 2.4 and 3.6); out of sample it did not, so it is no finding. The funding minutes (00:00, 08:00, 16:00 UTC) were left out of the tests; with three a day they are too few to say anything on their own.

**Are there more runs of equal orders than chance gives? (H12)** Many more. Out of sample 1.2% of taker size is in runs, against 0.03% with the sizes shuffled within 5 minutes, about forty times as much, and more than five times as much on every one of the 45 days. The share varies from 0.1% to 5.2% a day: a few large slicers make a day. Of the 3,215 runs found out of sample, a third have gaps within 1 s of 30.22 s, and they carry 61% of the size in runs; this fits Bybit's own TWAP tool, which slices every 30 s by default, but cannot prove it. With 40% of a known slicer found in the laboratory (§2.1), the true share is higher.

| Plain question | Measure | Out of sample | p (one-sided) | Verdict |
|---|---|---|---|---|
| Do orders sent just after Binance moved, their way, move the price more? | Net R(10 s), sniper-like less other, same size class | +2.7 bp (2.4 to 3.0) | < 0.001 | Holds |
| Does flow lean with the trend just after a whole minute? | Flow with the trend, first 3 s, real less fake marks | +0.03 BTC, t = 0.4 | 0.34 | Fails |
| Do makers widen before a whole minute? | Share of quotes wider than a tick, 2 s before, real less fake | −0.04 points, t = −5.5 | 1.00 | Fails (opposite sign) |
| Is there more slicing than chance gives? | Share of taker size in runs, real less shuffled | +1.2 points (0.8 to 1.6) | < 0.001 | Holds |

<sub><b>How to read the table.</b> Each row is one hypothesis fixed before the data were used (H10, H11a, H11b, H12). Brackets: 95% bands from 2,000 resamples of days. H10 and H12: bootstrap over days; H11: one-sided t over the 24 days, as fixed. p-values before the correction over all twelve, which comes with §5. Our calculation.</sub>

**For a quoter.** The three footprints say different things about the fills a resting order will get. A fill from a sniper-like order is the worst there is: the price goes on 3 to 6 bp against the quote, and it comes just after Binance moved, which a quoter can see as well. A slicer's fills are the best: small, regular and uninformed about the next minute, but all on one side for as long as the run lasts. The clock does not bring a crowd that knows the trend, it brings volume: a quote standing at the whole minute is filled more often, and the spread opens after the burst, not before it. Lecture 24 starts from these three facts.

## 4. When, and in what conditions

To follow: H13 and H14.

## 5. Runs as they start

To follow: H16 and H17.

## 6. What it means for our strategy

To follow.
