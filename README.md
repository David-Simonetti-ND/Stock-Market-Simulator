# StockNet, a Stock Market Simulation Game - Distributed Systems SP23 Final Project
by David Simonetti and John Lee

## General Description
We are trying to construct a large scale stock market simulation/game, where clients subscribe to an unreliable/delayed datastream and attempt to make optimal purchasing decisions on a basket of 5 stocks. Each client competes, not in a zero-sum game as in real markets, but for the top position on a global leaderboard.

Although finanicial markets actually move through a means of supply and demand, real market mechanics are beyond the scope of this project. Therefore, we make a series of assumptions for the market to simplify the problem.
    - Every stock is implemented by taking minute data from actual markets from the last month, then using a random walk for that minute to emulate random market movement. General direction and variance are set to update such that the stock stays around a mean value.
    - Each stock has infinite volume/liquidity, meaning that an individual's purchase does not impact the market in any way.
    - Buy orders and sell orders are limited to fill orders, meaning they are priced at the immediate value of the stock, which will likely be different than the price reported through the data stream (the data is delayed).

To add interesting behavior to our system:
    - The market is defined as a basket of 5 stocks
    - The stock data may be delayed/out of order by an arbitrary amount of time or even not sent.


## Goals
We three main goals for our system:
    - Persistence/Consistency
        - A client should be able to disconnect and reconnect using the same account and continiue playing from where they left off
        - The broker should be able to recover, should it go down
    - Throughput
        - We wish to maximize the total operations per second fo all clients
    - Latency
        - In conjunction with maximizing throughput, we wish to minimize the latency of a single client's buy/sell operations
        - We wish to maintain fairness between low-frequency and high-frequency traders.

## Running Code

????????????????????????
No clue bruh


## [Presentation](results/StockNet%20Presentation.pptx)

## [Final Paper](None)