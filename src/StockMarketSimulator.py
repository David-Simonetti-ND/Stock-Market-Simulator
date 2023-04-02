import random
import time
import socket
import json
import select
import numpy as np
import signal
import sys
from StockMarketLib import format_message, receive_data, VALID_TICKERS, SUBSCRIBE_TIMEOUT, GLOBAL_SPEEDUP

class StockMarketSimulator:
    """Simulates the Stock Market with the universe of stocks.
    """
    def __init__(self, name):
        # name of market simulator
        self.name = name
        
        # tickers
        self.tickers = VALID_TICKERS
        self.num_tickers = len(self.tickers)

        # track stock prices
        self.stock_prices = np.ones(self.num_tickers) * 100
        random.seed(time.time())
        
        # publish every 1/20 second
        self.publish_rate = .05 * 10e9 / GLOBAL_SPEEDUP
        # actual update every 1/100th a second
        self.update_rate = .01 * 10e9 / GLOBAL_SPEEDUP
            
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
        conn.close()
        self.sub_table.add(((data["hostname"], data["port"]), time.time_ns()))
    
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
                    "type" : "stockmartketsim",
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
        while True:
            
            # check if we have a new subscriber trying to connect
            readable, _, _ = select.select([self.recv_socket], [], [], 0)
            if readable != []:
                self.accept_new_connection()
            
            cur_time = time.time_ns()
            # try to update
            #if (cur_time - prev_update_time) > self.update_rate:
            #    prev_update_time = cur_time
            self.simulate_one_tick()
                
            # don't publish every
            if (cur_time - prev_sub_time) > self.publish_rate:
                self.publish_stock_data()
                prev_sub_time = cur_time
    
    def sinusoid_main(self):
        
    
    def simulate_one_tick(self):
        #! Temporarily simulates 1 tick
        self.stock_prices += np.random.normal(0, .1)

    def publish_stock_data(self):
        """Publishes Stock Data to every subscriber
        """
        # message for each ticker
        update = {"type" : "stockmarketsimupdate", "time": time.time_ns()}
        for i in range(self.num_tickers):
            update[self.tickers[i]] = self.stock_prices[i]
        message = json.dumps(update)
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