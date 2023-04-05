# Stock Market Simulation Game - Distributed Systems SP23 Final Project
by David Simonetti and John Lee

## General Description
We are trying to construct a large scale stock market simulation/game, where clients subscribe to a (unreliable) datastream and attempt to make optimal purchasing decisions on a basket of N stocks. Each client competes, not in a zero-sum game as in real markets, but for the top position on a shared leaderboard.

Although finanicial markets actually move through a means of supply and demand, real market mechanics are beyond the scope of this project. Therefore, we make a series of assumptions for the market to simplify the problem.
    - Every stock is implemented by taking minute data from actual markets from the last month, then using random walk for that minute to emulate random market movement. General direction and variance are set to update such that the stock stays around a mean value.
    - Each stock has infinite volume/liquidity, meaning that an individual's purchase does not impact the market in any way.
    - Buy orders are limited to limit orders and fill orders. Limit orders have a defined price and last until they are fulfilled or canceled. If the stock price is less than the order, the limit order will be automatically completed. Limit orders also lock the desired funding from the client's balance. Fill orders are immediately filled at the current price of the stock. The client's entire balance is blocked off untill the fill order returns to.
    - Sell orders are similarly limited to limit orders and liquidation orders. Limit orders sit until the stock is sold. The to-be-sold stock is blocked from other sell operations or liquidation. If the price is above the desired price, then the order is automatically completed. Liquidation orders sell the entire stock, and blocks operations on all of that stock.

To add interesting behavior to our system:
    - the market is defined as a basket of N=5 stocks
    - the stock data may be delayed/out of order by an arbitrary amount of time or even not sent.


## Goals
We have a couple of semantic goals to hit.
    - [] Assuming a maximum xput of operations per client, we would ideally like to scale up the number of clients of handles to thousands
    - [] Basic Reliability of client reconnection. If a client reconnects, it should be able to continue on from the same position
    - [] Client centric consistency -> a client can only buy/sell with resources it has and is not being used elsewhere. 


## To Dos (o is for Progress Report)
    - [] Stock Market Simulator
        - [o] Saves previous values for clients who crash to poll.
        - [o] Stochastic function for modeling basket of 5 stocks
            - [o] Stock 1
            - [o] Stock 2
            - [o] Stock 3
            - [o] Stock 4
            - [o] Stock 5           
        - [o] Publishes data every n seconds using UDP
            - [o] Randomly mask/delay data
        - [o] Stream high quality data through TCP to brokers
    - [o] Stock Brokers
        - [o] Single Stock Broker
            - [o] TCP connection with Simulator
            - [o] Handle buy/sell orders from clients
            - [o] Track a clients resources/allow client to poll its resources
            - [o] Async update/poll client leaderboards
        - [] Multiple Stock Brokers
            - [] Unknown, but for scaling
    - [o] Clients
        - [o] Buy/Sell of different kinds
        - [o] Poll Leaderboard
        - [o] Poll Resources
