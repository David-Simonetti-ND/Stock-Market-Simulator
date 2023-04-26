import random
from collections import deque
import time
import socket
import json
import select
# import numpy as np
import signal
import csv
import sys
import threading
from StockMarketLib import format_message, receive_data, print_debug, VALID_TICKERS, SUBSCRIBE_TIMEOUT, GLOBAL_SPEEDUP, MINUTE_SPEEDUP, CLIENT_DELAY

TEST = True

class StockMarketSimulator:
    """Simulates the Stock Market with the universe of stocks.
    """
    def __init__(self, name):
        ## Project Name
        self.name = name
        
        ## Set Tickers
        self.tickers = VALID_TICKERS
        self.num_tickers = len(self.tickers)
        
        ## Loading Stock Prices
        self.stock_prices = {}
        for t in self.tickers:
            with open(f'data/{t}.csv') as csvfile:
                reader = csv.reader(csvfile)
                self.stock_prices[t] = list(reader)
                print_debug(f"Minute prices loaded for {t}.")
        self.minute = 1
        
        ## Set Rates
        # publish every 1/2 second
        self.publish_rate = .1 * 1e9 / GLOBAL_SPEEDUP
        print_debug(f"Publish rate = {self.publish_rate / 1e9} p/sec")
        # actual update every 1/100th a second
        self.update_rate = .01 * 1e9 / GLOBAL_SPEEDUP
        print_debug(f"Update rate = {self.update_rate / 1e9} u/sec")
        # minute (no )
        self.minute_rate = MINUTE_SPEEDUP * 60 * 1e9 / GLOBAL_SPEEDUP # change this for faster volatility
        print_debug(f"Minute rate = {self.minute_rate / 1e9} seconds/minute")
        
        self.simulate_next_minute()
        
        ## save data to artificially delay it.
        self.delayed_data = deque()
        if TEST: self.prev_pub_time = 0

        ## Open a socket to accept new client subscriptions
        self.recv_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.recv_socket.bind(('', 0))
        # error if port already in use
        except:
            print("Error: port in use")
            exit(1)
        self.host, self.port = self.recv_socket.getsockname()
        print_debug(f"Listening on port {self.port}")
        
        # Publish Socket, bind to a port.
        self._init_pub_socket()
        
        # send information to name server
        self._init_ns_socket()

    ##################
    # Socket Methods #
    ##################
    
    def _init_pub_socket(self):
        """Initializes publish socket
        """
        self.pub_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.pub_port = self.pub_socket.getsockname()[1]
        self.sub_table = deque()
        self.sub_set = set()
        

    def _init_ns_socket(self):
        """Initializes name server socket
        """
        # send information to name server
        self.ns_host, self.ns_port = ("catalog.cse.nd.edu", 9097)
        self.ns_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.ns_socket.connect((self.ns_host, self.ns_port))
        #update the signal
        signal.signal(signal.SIGALRM, self._update_ns)
        signal.setitimer(signal.ITIMER_REAL, 0.1, 60) # now and every 60 seconds after
        
    def _update_ns(self, _, __):
        """Update Name server handler to periodically update name server"""
        # update msg
        update_msg = {
                    "type" : "stockmarketsim",
                    "owner" : "dsimone2",
                    "port" : self.port,
                    "project" : self.name
                    }
        self.ns_socket.sendall(json.dumps(update_msg).encode("utf-8"))
        print_debug("Name Server updated.")
        
    def accept_new_connection(self):
        """ Add a new client to the subscription table
        """
        conn, addr = self.recv_socket.accept()
        error_code, data = receive_data(conn)
        if data.get("type", None) == "broker":
            self.broker_connection = conn
            print_debug(f"New Broker {addr} connected.")
        else:
            self.sub_table.append(((data["hostname"], data["port"]), time.time_ns()))
            self.sub_set.add((data["hostname"], data["port"]))
            conn.close()
            print_debug(f"New Subscriber connected.")
    
    ##########################
    # Main Simulation Method #
    ##########################
    
    def simulate(self):
        """Begin Simulation loop
        """
        # start listening
        self.recv_socket.listen()
        prev_update_time = time.time_ns()
        prev_sub_time = prev_update_time
        prev_min_time = prev_update_time
        self.tick = 0
        while True:
            
            # check if we have a new subscriber trying to connect
            readable, _, _ = select.select([self.recv_socket], [], [], 0)
            if readable != []:
                self.accept_new_connection()
            
            cur_time = time.time_ns()
            
            # update the minute to use for simulation
            if (cur_time - prev_min_time) > self.minute_rate:
                prev_min_time = cur_time
                self.simulate_next_minute()
                self.tick = 0
                
            # try to update
            if (cur_time - prev_update_time) > self.update_rate:
                prev_update_time = cur_time
                self.tick += 1
                #self.simulate_one_tick(tick)

            # don't publish every
            if (cur_time - prev_sub_time) > self.publish_rate:
                self.publish_stock_data()
                prev_sub_time = cur_time
    
    ###############
    # Sim Backend #
    ###############
    
    # def simulate_next_minute(self):
    #     '''Simulates the next minute's data by using a random walk over a minute bar'''
    #     self.next_minute = {}
    #     x = np.arange(0, int(self.minute_rate//self.update_rate + 1) , 1)
    #     for t in self.tickers:
    #         min = self.stock_prices[t][self.minute]
    #         print(min)
    #         # compute random motions
    #         self.next_minute[t] = (((float(min[5]) - float(min[2])) / (self.minute_rate/self.update_rate)) * x + float(min[2]) + np.random.normal(0, np.random.uniform(.1, 1.9) * np.abs(float(min[3]) - float(min[4])) + .01, len(x))).round(2)
    #     self.minute += 1

    def simulate_next_minute(self):
        '''Simulates the next minute's data by using a random walk over a minute bar'''
        self.next_minute = {}
        x = [i for i in range(int(self.minute_rate//self.update_rate + 1))]
        for t in self.tickers:
            min = self.stock_prices[t][self.minute]
            # compute linear step
            tmp = [((float(min[5]) - float(min[2])) / (self.minute_rate/self.update_rate)) * i + float(min[2]) for i in x]
            # add random noise
            self.next_minute[t] = [round(i + random.gauss(0, random.uniform(.1, 1.9) * abs(float(min[3]) - float(min[4])) + .01), 2)  for i in tmp]
        self.minute += 1

    
    ##################
    # Publish Method #
    ##################

    def publish_stock_data(self):
        """Publishes Stock Data to every subscriber
        
        msg = { "type" : "stockmarketsimupdate",
                "time": time.time_ns(),
                "TSLA": ...,
                "MSFT": ...,
                "NVDA": ...,
                "AAPL": ...,
                "AMZN": ...,}
        """
        start = time.time_ns()
        # message for each ticker
        update = {"type" : "stockmarketsimupdate", "time": start}
        for t in self.tickers:
            update[t] = self.next_minute[t][self.tick]

        message = json.dumps(update)
        try:
            self.broker_connection.sendall(format_message(message))
        except Exception as e:
            pass

        # append the current message to the data queue
        self.delayed_data.append(message)
        if len(self.delayed_data) <= CLIENT_DELAY:
            return
        # retrieve the delayed data in the queue. This message will be sent to users
        message = self.delayed_data.popleft()

        
        # remove out of date subscribers
        cur_time = time.time_ns()
        out_of_date_subs = []
        while self.sub_table:
            if (cur_time - self.sub_table[0][1]) > SUBSCRIBE_TIMEOUT:
                out_of_date_subs.append(self.sub_table.popleft())
            else:
                break
        if len(out_of_date_subs) != 0:
            print_debug(f"Removed {len(out_of_date_subs)} subs.")
            
        # send data to subscribed sockets
        print_debug(f"Publishing to {len(self.sub_table)} clients...", update)

        for sub_sock in self.sub_table:
            self.pub_socket.sendto(message.encode("utf-8"), sub_sock[0])
            
        if TEST:
            end = time.time_ns()
            pub_time = end - start
            print(f"Num clients: {len(self.sub_table)}, Publish Time: {pub_time/1e9}, Start Int: {(start - self.prev_pub_time)/1e9}, End Int: {(end - self.prev_pub_time)/1e9}")
            self.prev_pub_time = start
        
            
    
if __name__ == "__main__":
    server = StockMarketSimulator(sys.argv[1])
    server.simulate()