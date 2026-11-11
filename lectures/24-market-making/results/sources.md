# Sources checked for Lecture 24 (2026-11-11)

## Bybit's fees, USDT perpetual contracts

From Bybit's help centre, read on 2026-11-11.

**Trading Fee Structure** (https://www.bybit.com/en/help-center/article/Trading-Fee-Structure, "last updated on 2026-11-05"). Perpetual and futures contracts, taker / maker:

| VIP level | Taker | Maker |
|---|---|---|
| VIP 0 | 0.0550% | 0.0200% |
| VIP 1 | 0.0400% | 0.0180% |
| VIP 2 | 0.0375% | 0.0160% |
| VIP 3 | 0.0350% | 0.0140% |
| VIP 4 | 0.0320% | 0.0120% |
| VIP 5 | 0.0320% | 0.0100% |
| Supreme VIP | 0.0300% | 0.0000% |

The page adds that rates may vary by region, and that the account's own fee-rate page is authoritative.

**Market Maker Incentive Program** (https://www.bybit.com/en/help-center/article/Introduction-to-the-Market-Maker-Incentive-Program, "last updated on 2026-10-21"). Maker rebate for perpetual and expiry contracts, Group 1 (BTCUSDT, ETHUSDT, SOLUSDT, XRPUSDT):

| MM level | Weighted maker share | Group 1 maker rebate |
|---|---|---|
| MM 1 | ≥ 0.03% | −0.0010% |
| MM 2 | ≥ 0.50% | −0.0025% |
| MM 3 | ≥ 1.00% | −0.0040% |

The taker fee follows the account's Pro tier. Orders must be at least 10 times the contract's minimum order size; our 0.001 BTC orders, BTCUSDT's minimum, would not qualify.

In bp: standard maker 2 bp, taker 5.5 bp; the best public maker rate is a rebate of 0.4 bp (MM 3, 1% of all makers' volume on the contracts).

## Literature

- Avellaneda, M. and Stoikov, S. (2008). High-frequency trading in a limit order book. *Quantitative Finance* 8(3), 217-224. doi:10.1080/14697680701381228. (The publisher's page refused automated access; volume, issue, pages and DOI as listed by the journal's citation records.)
- Guéant, O., Lehalle, C.-A. and Fernandez-Tapia, J. (2013). Dealing with the inventory risk: a solution to the market making problem. *Mathematics and Financial Economics* 7(4), 477-507. doi:10.1007/s11579-012-0087-0. arXiv:1105.3115 (HAL: hal-01393110). Checked at source (arXiv abstract): a stochastic control problem "similar to the one introduced by Ho and Stoll and formalized mathematically by Avellaneda and Stoikov", solved "under inventory constraints", with "closed-form approximations based on a spectral characterization of the optimal quotes".
