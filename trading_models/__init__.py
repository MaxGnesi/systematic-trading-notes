"""Research toolkit: data -> risk -> allocation -> backtest.

Data flows one way. Every stage exchanges plain pandas objects:

    data       prices / returns   DataFrame (index: dates, columns: assets)
    risk       covariance         DataFrame (assets x assets)
    allocation weights            Series    (index: assets, sums to 1)
    backtest   portfolio returns  Series    (index: dates)
"""
