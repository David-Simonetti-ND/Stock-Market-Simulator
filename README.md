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
1. Persistence/Consistency
    - A client should be able to disconnect and reconnect using the same account and continiue playing from where they left off
    - The broker should be able to recover, should it go down
2. Throughput
    - We wish to maximize the total operations per second fo all clients
3. Latency
    - In conjunction with maximizing throughput, we wish to minimize the latency of a single client's buy/sell operations
    - We wish to maintain fairness between low-frequency and high-frequency traders.


## Architecture

David can you fill this in

#### Overview

![Overview](results/img/Overview.png)

#### Simulator
![Simulator](results/img/Simulator.png)

#### Broker/Load Balancer
![Broker](results/img/Broker.png)

#### Replicator/Replication Manager
![Replication](results/img/Replication.png)



## Evaluation
We evaluted our system according to our 3 goals above:

#### Consistency
While we do not test the client-side (since our logging system should ensure that), we test what happens when our replication system crashes. In this plot, we observe that initially, our servers are servicing clients. At 10 seconds in, we crash all replicators and observe that no clients are being serviced. During this time, our replication manager goes through and restarts our replicators so that at ~23 seconds in all our clients can be serviced again.

![consistency](results/img/Consistency.png)

#### Throughput
We test the total throughput of our system on 50, 100, 200, and 500 clients using a different number of replication servers. Initially, from 1-15 replication servers, the total throughput increases drastically for all clients. Then it starts leveling off. In an ideal system, we would only see this leveling off when the number of clients reaches the number of servers, since each server would begin handling more than 1 client. However, since we only have 1 load balancer, it is a source of bottleneck for our system.

![throughput](results/img/Throughput.png)

#### Latency
We test the latency of both a high-frequency and low-frequency client. Overall, we observe that the latency goes up as the number of high-frequency clients increase, which is to be expected. We see a significant jump around 50-60 clients, which we suspect to be the point our load balancer becomes a bottleneck. For both HFT and LFT, the latency stays around the same, so our goal of fairness is met.

![latency](results/img/Latency.png)

#### Simulator Publish Times
We wished to ensure that our simulator was not another source of bottleneck, we tested how long it would take in each publish interval to publish to an increasing number of clients. We observe that even with 1000 clients, the publish time is only 6ms, which is below our update rate of 10ms and the actual publish interval of 100ms. Thus, we could have more clients subscribe than our architecture can currently handle.

![sim_clients](results/img/PubOverClients.png)

Furthermore, since we implement a pub/sub scheme that might result in temporarily duplicated clients, we observe the publish times over time. The data shows that the publish times do near the update rate, particularly with the two spikes (which we cannot explain besides performance hiccups). However, this is not a problem if we simply updated the data asynchronously.

![sim_time](results/img/PubOverTime.png)


## Running Code

(Advanced)
Running using condor:

To run StockNet on condor, there are a couple of initialization steps to get it working.
First, clone this github repository somewhere in your /scratch365/$USER/ directory.
Once there, navigate into the Stock-Market-Simulator directory and run the following command:
`conda env create --prefix /scratch365/$USER/stock_conda --file environment.yml `
This will create the prerequisite conda environment needed for the condor jobs to run.
The command might take some time to run (creating a conda environment can be pretty slow).

Once this is complete, you are ready to run StockNet with condor jobs!
In order to run the system, please open four different terminal windows.
Connect the first two to different CRC machines (for example, disc01 and disc02)
Connect the second two to condorfe
On the first terminal window, navigate to the Stock-Market-Simulator directory (where you cloned the github repo)
Then cd into src, and run
`python3 StockMarketSimulator.py stock`
To run this, you can use the conda environment created by conda up above, or any equivalent python3 (no dependencies required)
This will start the simulator on project name "stock"

On the second terminal, navigate to the Stock-Market-Simulator/src/condor directory.
Once there, 


## Presentation
The powerpoint presentation summarizing our system and evaluation can be downloaded [here](results/StockNet%20Presentation.pptx).

## Final Paper
The final paper is located [here](None).