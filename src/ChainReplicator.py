import socket
import sys
import time
import os
import json
import select
import random
import http.client
import signal
from StockMarketLib import format_message, receive_data, lookup_server, VALID_TICKERS, StockMarketUser

class ChainReplicator:
    def __init__(self, chain_name):
        """Initializes the chain replication server.
        
        Also opens a UDP connection to the name server

        Args:
            chain_name (str): name of the chain server
        """
        
        
        self.chain_name = chain_name
        # create socket
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # set 60 seconds timeout waiting for a connection, so we can update the name server
        self.socket.settimeout(60)
        # try to bind to port
        try:
            self.socket.bind((socket.gethostname(), 0))
        # error if port already in use
        except:
            print("Error: port in use")
            exit(1)

        self.port_number = self.socket.getsockname()[1]
        print(f"Listening on port {self.port_number}")
        
        self.socket.listen()
        # use a set to keep track of all open sockets - master socket is the first socket
        self.socket_table = set([self.socket])
        
        # for users and the leaderboard
        self.num_users = 0
        self.users = {}
        self.leaderboard = []

        # see if we need to perform a rebuild after a crash
        # if there is a checkpoint file or a transaction log, we will reload in stock market data from those files
        # set the txn_log to none to indicate that we are rebuilding from crash
        self.txn_log = None
        self.rebuild_server()
        # once the server is rebuilt, there is two cases
        # start new transaction log
        self.txn_log = open("table.txn", "w")
        self.txn_count = 0

        # send information to name server
        self.ns_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.ns_socket.connect(("catalog.cse.nd.edu", 9097))
        self.ns_update()

        timeout = 1
        while True:
            possible_simulators = lookup_server(self.broker_name, "stockmarketsim")
            for simulator in possible_simulators:
                try:
                    self.stockmarketsim_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.stockmarketsim_sock.connect((simulator["name"], simulator["port"]))
                    self.stockmarketsim_sock.sendall(format_message({"type": "broker"}))
                    print("DEBUG: Connected to StockMarketSim")
                    break
                except Exception:
                    self.stockmarketsim_sock = None
            if self.stockmarketsim_sock != None:
                break
            print(f"Unable to connect to simulator, retrying in {timeout} seconds")
            time.sleep(timeout)
            timeout *= 2
        
        # update the leaderboard every minute 
        signal.signal(signal.SIGALRM, self._update_leaderboard)
        signal.setitimer(signal.ITIMER_REAL,60, 60) # now and every 60 seconds after