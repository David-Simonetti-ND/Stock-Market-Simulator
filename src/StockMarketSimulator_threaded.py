import random
from collections import deque
import time
import socket
import json
import select
import numpy as np
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
        self.publish_rate = .25 * 1e9 / GLOBAL_SPEEDUP
        print_debug(f"Publish rate = {self.publish_rate / 1e9} p/sec")
        # actual update every 1/100th a second
        self.update_rate = .05 * 1e9 / GLOBAL_SPEEDUP
        print_debug(f"Update rate = {self.update_rate / 1e9} u/sec")
        # minute (no )
        self.minute_rate = MINUTE_SPEEDUP * 60 * 1e9 / GLOBAL_SPEEDUP # change this for faster volatility
        print_debug(f"Minute rate = {self.minute_rate / 1e9} seconds/minute")
        
        self._simulate_next_minute(first=True)
        
        ## save data to artificially delay it.
        self.delayed_data = deque()
        
        ## Testing features
        if TEST: 
            self.prev_pub_time = 0

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
        prev_pub_time = prev_update_time

        # threads for updateing
        update_thread = threading.Thread(target=self._simulate_tick, daemon=True)
        update_thread.start()
        minute_thread = threading.Thread(target=self._simulate_next_minute, daemon=True)
        minute_thread.start()
        self.tick = 0
        while True:
            
            # check if we have a new subscriber trying to connect
            readable, _, _ = select.select([self.recv_socket], [], [], 0)
            if readable != []:
                self.accept_new_connection()
            
            cur_time = time.time_ns()

            # don't publish every
            if (cur_time - prev_pub_time) > self.publish_rate:
                self.publish_stock_data()
                prev_pub_time = cur_time
    
    ###############
    # Sim Backend #
    ###############
    
    def _simulate_tick(self):
        """Simulates next tick"""
        while True:
            self.tick += 1
            time.sleep(self.update_rate/1e9)
        
    def _simulate_next_minute(self, first = False):
        '''Simulates the next minute's data by using a random walk over a minute bar'''
        self.next_minute = {}
        while True:
            x = np.arange(0, self.minute_rate/self.update_rate , 1)
            for t in self.tickers:
                min = self.stock_prices[t][self.minute]
                # compute random motions
                self.next_minute[t] = (((float(min[5]) - float(min[2])) / (self.minute_rate/self.update_rate)) * x + float(min[2]) + np.random.normal(0, np.random.uniform(.1, 1.9) * np.abs(float(min[3]) - float(min[4])) + .01, len(x))).round(2)
            self.minute += 1
            self.tick = 0
            if first:
                break
            time.sleep(self.minute_rate/1e9)
            

    
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
        # message for each ticker
        update = {"type" : "stockmarketsimupdate", "time": time.time_ns()}
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
        if TEST:
            start = time.time_ns()

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