import random
import time
import socket
import json
import select
import numpy as np
import signal
import csv
import sys
from StockMarketLib import format_message, receive_data, VALID_TICKERS, SUBSCRIBE_TIMEOUT, GLOBAL_SPEEDUP, MINUTE_SPEEDUP, CLIENT_DELAY

class StockMarketSimulator:
    """Simulates the Stock Market with the universe of stocks.
    """
    def __init__(self, name):
        # name of market simulator
        self.name = name
        
        # tickers
        self.tickers = VALID_TICKERS
        self.num_tickers = len(self.tickers)
        
        # load true stock prices
        self.stock_prices = {}
        for t in self.tickers:
            with open(f'data/{t}.csv') as csvfile:
                reader = csv.reader(csvfile)
                self.stock_prices[t] = list(reader)
        self.minute = 1

        
        # publish every 1/2 second
        self.publish_rate = .1 * 10e9 / GLOBAL_SPEEDUP
        # actual update every 1/100th a second
        self.update_rate = .01 * 10e9 / GLOBAL_SPEEDUP
        # minute (no )
        self.minute_rate = MINUTE_SPEEDUP * 60 * 10e9 / GLOBAL_SPEEDUP # change this for faster volatility

        self.delayed_data = []
        
        # simulate the next minute
        self.simulate_next_minute()
            
        # Open a socket to accept new client subscriptions
        self.recv_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.recv_socket.bind(('', 0))
        # error if port already in use
        except:
            print("Error: port in use")
            exit(1)
        self.host, self.port = self.recv_socket.getsockname()
        print(f"Listening on port {self.port}")
        
        # Publish Socket, bind to a port.
        self._init_pub_socket()
        
        # send information to name server
        self._init_ns_socket()
    
    def accept_new_connection(self):
        """ add a new client to the subscription table
        """
        conn, addr = self.recv_socket.accept()
        error_code, data = receive_data(conn)
        if data.get("type", None) == "broker":
            self.broker_connection = conn
        else:
            self.sub_table.add(((data["hostname"], data["port"]), time.time_ns()))
            conn.close()
    
    def _init_pub_socket(self):
        """Initializes publish socket
        """
        self.pub_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.pub_port = self.pub_socket.getsockname()[1]
        self.sub_table = set()

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
        """Update Name server handler"""
        # update msg
        update_msg = {
                    "type" : "stockmarketsim",
                    "owner" : "dsimone2",
                    "port" : self.port,
                    "project" : self.name
                    }
        self.ns_socket.sendall(json.dumps(update_msg).encode("utf-8"))
    
    
    def simulate(self):
        """Begin Simulation loop
        """
        # start listening
        self.recv_socket.listen()
        prev_update_time = time.time_ns()
        prev_sub_time = prev_update_time
        prev_min_time = prev_update_time
        tick = 0
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
                tick = 0
                
            # try to update
            if (cur_time - prev_update_time) > self.update_rate:
                prev_update_time = cur_time
                tick += 1
                #self.simulate_one_tick(tick)

                
            # don't publish every
            if (cur_time - prev_sub_time) > self.publish_rate:
                self.publish_stock_data(tick)
                prev_sub_time = cur_time
    
    def simulate_next_minute(self):
        self.next_minute = {}
        x = np.arange(0, self.minute_rate/self.update_rate , 1)
        for t in self.tickers:
            min = self.stock_prices[t][self.minute]
            # compute random motions
            self.next_minute[t] = (((float(min[5]) - float(min[2])) / (self.minute_rate/self.update_rate)) * x + float(min[2]) + np.random.normal(0, np.random.uniform(.1, 1.9) * np.abs(float(min[3]) - float(min[4])) + .01, len(x))).round(2)
            
        self.minute += 1
    
    def simulate_one_tick(self, tick):
        """"""
        return 

    def publish_stock_data(self, tick):
        """Publishes Stock Data to every subscriber
        """
        # message for each ticker
        update = {"type" : "stockmarketsimupdate", "time": time.time_ns()}
        for t in self.tickers:
            update[t] = self.next_minute[t][tick]

        message = json.dumps(update)
        try:
            self.broker_connection.sendall(format_message(message))
        except Exception as e:
            pass

        self.delayed_data.append(message)
        if len(self.delayed_data) <= CLIENT_DELAY:
            return
        message = self.delayed_data.pop(0)

        
        # remove out of date subscribers
        out_of_date_subs = [sub for sub in self.sub_table if (time.time_ns() - sub[1] > (SUBSCRIBE_TIMEOUT)) ]
        for sub in out_of_date_subs:
            self.sub_table.remove(sub)
            
        # send data to subscribed sockets
        print(f"Publishing to {len(self.sub_table)} clients...", update)
        for sub_sock in self.sub_table:
            #! can add randomized delay here
            self.pub_socket.sendto(message.encode("utf-8"), sub_sock[0])

    

    
if __name__ == "__main__":
    server = StockMarketSimulator(sys.argv[1])
    server.simulate()