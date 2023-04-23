import socket
import sys
import time
import os
import json
import select
import random
import http.client
import signal
from StockMarketLib import format_message, receive_data, lookup_server, print_debug, VALID_TICKERS, StockMarketUser

class StockMarketBroker:
    def __init__(self, broker_name, num_chains):
        """Initializes the stock market broker, accepting connections from a randomly selected port.
        
        Also opens a UDP connection to the name server

        Args:
            broker_Name (str): name of the broker
            num_chains (int): how many chain replication servers will be connected
        """
        
        self.broker_name = broker_name
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
        print_debug(f"Listening on port {self.port_number}")
        
        self.socket.listen()
        # use a set to keep track of all open sockets - master socket is the first socket
        self.socket_table = set([self.socket])
        
        # for users and the leaderboard
        self.leaderboard = []
        
        # for stock info
        self.latest_stock_info = None

        # send information to name server
        self.ns_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.ns_socket.connect(("catalog.cse.nd.edu", 9097))
        self.ns_update({"type" : "stockmarketbroker", "owner" : "dsimone2", "port" : self.port_number, "project" : self.broker_name})

        # connect to simulator
        self.stockmarketsim_sock = self.connect_to_server("stockmarketsim")
        
        # update the leaderboard every minute 
        signal.signal(signal.SIGALRM, self._update_leaderboard)
        signal.setitimer(signal.ITIMER_REAL,60, 60) # now and every 60 seconds after

        self.num_chains = num_chains
        self.chain_sockets = {}
        for i in range(num_chains):
            self.chain_sockets[i] = self.connect_to_server(f"chain-{i}")

    def connect_to_server(self, server_type):
        """ Connect to given server type on socket """
        timeout = 1
        while True:
            possible_servers = lookup_server(self.broker_name, server_type) #"stockmarketsim")
            for server in possible_servers:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.connect((server["name"], server["port"]))
                    sock.sendall(format_message({"type": "broker"}))
                    print_debug(f"Connected to server {server_type}")
                    break
                except Exception:
                    sock = None
            if sock != None:
                break
            print(f"Unable to connect to server {server_type}, retrying in {timeout} seconds")
            time.sleep(timeout)
            timeout *= 2 
        return sock
        
    def _update_leaderboard(self, _, __):
        ''' signaled function call to update the leaderboard.'''
        # snapshot of each ticker's price
        prices = {}
        for t in VALID_TICKERS:
            prices[t] = self.latest_stock_info[t]
            
        def net_worth(user):
            nw = user.cash
            for t in VALID_TICKERS:
                nw += user.stocks[t] * prices[t]
            return nw
        
        users = list(self.users.values())
        nw = [net_worth(u) for u in users]
        
        self.leaderboard = sorted(list(zip(users, nw)), key = lambda x: x[1], reverse=True)
        print_debug("Leaderboard Updated.")
        
    
    def accept_new_connection(self):
        """Accepts a new connection and adds it to the socket table.
        """
        conn, addr = self.socket.accept()
        conn.settimeout(60)
        self.socket_table.add(conn)

    def ns_update(self, message):
        """Updates the name server with the current state
        """
        # send info to name server
        self.ns_socket.sendall(json.dumps(message).encode("utf-8"))
        print_debug("Name Server Updated.")
        # keep track of last name server update
        self.last_ns_update = time.time_ns()

    def hash(self, string):
        if not isinstance(string, str):
            raise TypeError("Key must be a string")
        factor_number = 3
        hash = 0
        # loop over each character in the string
        for character in string:
            # multiply the ascii value of that character by a factor
            hash += factor_number * ord(character)
            # pick the next factor based on the previous character
            factor_number = ord(character)
        # return the integer hash of the string
        return hash
    
    def json_resp(self, success, value):
        return {"Success": success, "Value": value}   
    
    def service_request(self, request):
        if request.get("username", None) == None:
            return self.json_resp(False, "Username required to perform an action")
        # peform the request the client submitted
        # add current stock info to request
        request["latest_stock_info"] = self.latest_stock_info
        username_hash = self.hash(request["username"])
        chain_socket = self.chain_sockets[username_hash % self.num_chains]
        timeout = 1 
        while True:
            try:
                print("Request: ", request)
                chain_socket.sendall(format_message(request))
                status, data = receive_data(chain_socket)
            except Exception as e:
                print(e)
                print(f"Unable to send request to database server, retrying in {timeout} seconds")
                time.sleep(timeout)
                timeout *= 2
                chain_socket.close()
                chain_socket = self.connect_to_server("chain-0")
                continue
            if data:
                break
        if status == 0 and data:
            self.chain_sockets[username_hash % self.num_chains] = chain_socket
            return data
        else:
            return self.json_resp(False, "The database server has crashed")


def main():
    # ensure only a port is given
    if len(sys.argv) != 3:
        print("Error: please enter project name and number of chain servers as the arguments")
        exit(1)

    try:
        num_chains = int(sys.argv[2])
    except Exception:
        print("Error: number of chain servers must be an integer")
        exit(1)

    server = StockMarketBroker(sys.argv[1], num_chains)

    while True:
        # if 1 minute has passed, perform a name server update
        if (time.time_ns() - server.last_ns_update) >= (60*1000000000):
            server.ns_update({"type" : "stockmarketbroker", "owner" : "dsimone2", "port" : server.port_number, "project" : server.broker_name})
        # use select to return a list of sockets ready for reading
        # wait up to 5 seconds for an incoming connection
        readable, _, _ = select.select(list(server.socket_table) + [server.stockmarketsim_sock], [], [], 5)
        # if no sockets are readable, try again
        if readable == []:
            continue
        # if the master socket is in the readable list, give it priority and accept the new incomming client
        if server.socket in readable:
            server.accept_new_connection()
            readable.remove(server.socket)
        if server.stockmarketsim_sock in readable:
            status, data = receive_data(server.stockmarketsim_sock)
            ## error reading from stock market sim
            if data is None or status == 2:
                # try to reconnect and go to next loop, since all data was out of date anyways
                server.stockmarketsim_sock = server.connect_to_server("stockmarketsim")
                continue
            server.latest_stock_info = json.loads(data)
            readable.remove(server.stockmarketsim_sock)
        # otherwise we have at least one client connection with data available
        # handle all pendings reads before performing select again
        while len(readable) > 0:
            # check if we should perform a name server update
            if (time.time_ns() - server.last_ns_update) >= (60*1000000000):
                server.ns_update({"type" : "stockmarketbroker", "owner" : "dsimone2", "port" : server.port_number, "project" : server.broker_name})
            # randomly pick a client to service
            conn = random.choice(readable)
            readable.remove(conn)
            # process requests from client until client disconnects
            # read a request, getting status (1 for error on read, 0 for successful reading), and the request
            status, request = receive_data(conn)
            if status == 1:
                # send back error that occured
                error_msg = server.json_resp(False, request)
                try:
                    conn.send(format_message(error_msg))
                except Exception:
                    pass
                continue
            # if connection was broken or closed, go back to waiting for a new connection
            if not request:
                conn.close()
                server.socket_table.remove(conn)
                continue

            response = server.service_request(request)

            # send response 
            try:
                # if the client disconnects before we try to send, get a new connection
                conn.sendall(format_message(response))
            except Exception:
                continue


if __name__ == "__main__":
    main()