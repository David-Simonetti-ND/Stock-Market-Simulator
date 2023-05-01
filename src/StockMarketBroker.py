# File: StockMarketBroker.py
# Author: David Simonneti (dsimone2@nd.edu) & John Lee (jlee88@nd.edu) 
# 
# Description: Main Load Balancer/Broker server that redistributes tasks

import socket
import sys
import time
import json
import select
import random
import signal
from collections import deque 
from StockMarketLib import format_message, receive_data, lookup_server, print_debug, VALID_TICKERS

class StockMarketBroker:
    def __init__(self, broker_name, num_chains):
        """Initializes the stock market broker, accepting connections from a randomly selected port.
        
        Also opens a UDP connection to the name server

        Args:
            broker_Name (str): name of the broker
            num_chains (int): how many chain replication servers will be connected
        """
        
        # project name for this broker
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

        # connect to simulator
        self.stockmarketsim_sock = self.connect_to_server("stockmarketsim")

        # used to set up replication servers
        # each 1 of n replication servers will handle about 1/n of client information/requests
        # here we set up our connections to the replication servers
        # num_chains is the total number of replication servers, chain number is the current id of the replication server
        self.num_chains = num_chains
        # maps chain number -> socket object
        self.chain_sockets = {}
        # maps socket object -> chain number
        self.chain_to_index = {}
        # maps chain number -> a deque of pending client requests for that server
        # (pending requests can occur if the replication server crashed or multiple clients are trying to use the same server)
        self.pending_reqs = {}
        for i in range(num_chains):
            self.chain_sockets[i] = self.connect_to_server(f"chain-{i}")
            self.chain_to_index[self.chain_sockets[i]] = i
            self.pending_reqs[i] = deque()

        # set of client connections with a current request - so that we only handle one client conn at a time
        self.pending_conns = set()
        # maps chain socket object -> client connection that is currently being handled on that server
        self.name_to_conn = {}
        # data structure used for measuring the fairness of the broker. maps client number to the number of requests serviced for that client
        self.done = {}

        # ensure we get one round of stock prices before we start 
        while self.latest_stock_info == None:
            status, data = receive_data(self.stockmarketsim_sock)
            ## error reading from stock market sim
            if data is None or status == 2:
                # try to reconnect and go to next loop, since all data was out of date anyways
                self.stockmarketsim_sock = self.connect_to_server("stockmarketsim")
                continue
            self.latest_stock_info = json.loads(data)

        # update the leaderboard & name server every minute 
        signal.signal(signal.SIGALRM, self._update)
        signal.setitimer(signal.ITIMER_REAL, .1, 60) # now and every 60 seconds after
    
    ##################
    # Socket Methods #
    ##################
    
    def connect_to_server(self, server_type, max_attempts=100):
        """ Connect to given server type on socket 
        Args:
            server_type  (str): type of the server to connect to
            max_attempts (int): how many attempts will be made to connect to the server
        """
        attempts = 0
        timeout = 1
        while True:
            # stop trying if we reached max attempts
            if attempts >= max_attempts:
                return None
            # try to lookup the server_type on the same project name
            possible_servers = lookup_server(self.broker_name, server_type) 
            # try and connect to each in order
            for server in possible_servers:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(5)
                    sock.connect((server["name"], server["port"]))
                    sock.sendall(format_message({"type": "broker"}))
                    print_debug(f"Connected to server {server_type}")
                    break
                except Exception:
                    sock = None
            # if we got a connection, we can stop trying!
            if sock != None:
                break
            print(f"Unable to connect to server {server_type}, retrying in {timeout} seconds")
            time.sleep(timeout)
            timeout *= 2 
            attempts += 1
        return sock
    
    def accept_new_connection(self):
        """Accepts a new connection and adds it to the socket table.
        """
        conn, addr = self.socket.accept()
        conn.settimeout(60)
        self.socket_table.add(conn)
    
    ##################
    # Signal Handler #
    ##################
    
    def _update(self, _, __):
        """ Combined update handler
        """
        self._update_ns({"type" : "stockmarketbroker", "owner" : "dsimone2", "port" : self.port_number, "project" : self.broker_name})
        self._update_leaderboard()

    def _update_leaderboard(self):
        ''' updates the leaderboard by polling all connected replicators for their user info.
        '''
        # snapshot of each ticker's price
        prices = {}
        for t in VALID_TICKERS:
            prices[t] = self.latest_stock_info[t]
        
        # keep a dictionary mapping users to their net worth
        users = {}
        request = {"action": "broker_leaderboard", "latest_stock_info": self.latest_stock_info, "username": "broker", "password": "broker"}
        for i in range(self.num_chains):
            # get the socket conn
            chain_socket = self.chain_sockets[i]
            # if the replicator is busy, skip it for this update
            if i in self.name_to_conn.keys():
                continue
            # try to get the user information from the replicator
            try:
                chain_socket.sendall(format_message(request))
                status, data = receive_data(chain_socket)
            except Exception as e:
                print(f"Unable to send request to database server to get leaderboard info")
                continue
            # and try to update our user information with the info from that replicator
            try:
                users = {**users, **data["Value"]}      
            except:
                pass
        # sort the users by their net worth
        self.leaderboard = sorted(list([ (username, users[username]) for username in users.keys()]), key = lambda x: x[1], reverse=True)
        print_debug("Leaderboard Updated.")
    
    def _update_ns(self, message):
        """Updates the name server with the current state
        """
        # send info to name server
        self.ns_socket.sendall(json.dumps(message).encode("utf-8"))
        print_debug("Name Server Updated.")
        # keep track of last name server update
        self.last_ns_update = time.time_ns()
        
    ######################
    # Replicator Methods #
    ######################

    def _get_leaderboard(self):
        """reports the top 10 users
        """
        if self.leaderboard == []:
            self._update_leaderboard(None, None)
        # Top 10
        lstring = "TOP 10\n" + "---------------\n"
        try:
            for i in range(10):
                lstring += self.leaderboard[i][0] + ' | ' + str(round(self.leaderboard[i][1], 2)) + "\n"
        except:
            pass
        print_debug("\n" + lstring)
        return self.json_resp(True, lstring)
        
    def hash(self, string):
        """returns an integer hash from an input string
        """
        if not isinstance(string, str):
            raise TypeError("Key must be a string")
        hash = 0
        # loop over each character in the string
        for character in string:
            # add the ascii value of that character
            hash += ord(character)
        # return the integer hash of the string
        return hash % 41
    
    def json_resp(self, success, value):
        """Basic message fmt
        """
        return {"Success": success, "Value": value}   
    
    def start_request(self, request, conn):
        """Forwards job request to hashed replicator
        """
        # if there is no username, we don't know which server to hash to
        if request.get("username", None) == None:
            return self.json_resp(False, "Username required to perform an action")
        # if its a leaderboard request, then the broker handles it
        if request.get("action", None) == "leaderboard":
            request["latest_stock_info"] = self.latest_stock_info
            return self._get_leaderboard()
        # peform the request the client submitted
        # add current stock info to request
        request["latest_stock_info"] = self.latest_stock_info
        # see which replicator the client maps to
        username_hash = self.hash(request["username"])
        chain_num = (username_hash % self.num_chains)
        chain_socket = self.chain_sockets[chain_num]
        # if the replicator is busy, and the client isn't already in the request queue, we add it
        if chain_num in self.name_to_conn.keys():
            if (request, conn) not in self.pending_reqs[chain_num]:
                self.pending_reqs[chain_num].append((request, conn))
            return None
        try:
            chain_socket.sendall(format_message(request))
        except Exception as e:
            print(f"Unable to send request to database server, adding to job queue")
            chain_socket.close()
            # if the replicator is down, try one time to reconnect, otherwise we add the request to the queue
            chain_socket = self.connect_to_server(f"chain-{username_hash % self.num_chains}", max_attempts=1)
            if chain_socket != None:
                self.chain_sockets[chain_num] = chain_socket
                self.chain_to_index[chain_socket] = (chain_num)
            if (request, conn) not in self.pending_reqs[chain_num]:
                self.pending_reqs[chain_num].append((request, conn))
            return None
        # return the replicator number that is servicing the request
        return username_hash % self.num_chains
        
    def finalize_request(self, index):
        """Asynchronously called when a replicator is done handling a client request
        """
        status, data = receive_data(self.chain_sockets[index])
        if status == 0 and data:
            response = data
        else:
            # if we get an incomplete response, something really bad has happened
            response = self.json_resp(False, "The database server has crashed")
        # try to send response to client
        try:
            self.name_to_conn[index].sendall(format_message(response))
        except Exception as e:
            pass
            # client crashed here, so nothing we can do
        # used for debugging fairness of system
        #self.done[self.name_to_conn[index]] = self.done.get(self.name_to_conn[index], 0) + 1
        #print(len(self.done.keys()), [self.done[x] for x in self.done.keys()])


def main():
    # ensure only a port is given
    if len(sys.argv) != 3:
        print("Error: please enter project name and number of replicators as the arguments")
        exit(1)

    try:
        num_chains = int(sys.argv[2])
    except Exception:
        print("Error: number of replicators must be an integer")
        exit(1)

    server = StockMarketBroker(sys.argv[1], num_chains)
    # keep track of how many requests the broker has handled
    total_requests_handled = 0
    while True:
        # use select to return a list of sockets ready for reading
        # wait up to 5 seconds for an incoming connection
        readable, _, _ = select.select(list(server.socket_table) + [server.stockmarketsim_sock] + list([server.chain_sockets[x] for x in server.name_to_conn.keys()]), [], [], 5)
        # if no sockets are readable, try again
        if readable == []:
            continue
        # if the master socket is in the readable list, give it priority and accept the new incomming client
        if server.socket in readable:
            server.accept_new_connection()
            readable.remove(server.socket)
        # new stock information available
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
            # every 1000 requests, print out how many requests have been handled along with the time
            if (total_requests_handled % 1_000) == 0:
                print(f"Time: {time.time_ns()} Requests handled: {total_requests_handled}")
            # randomly pick a client to service
            conn = random.choice(readable)
            readable.remove(conn)
            # if the client already has a request pending, ignore it
            if conn in server.pending_conns:
                continue
            # if a replicator has a response for us
            if conn in [server.chain_sockets[x] for x in server.name_to_conn.keys()]:
                total_requests_handled += 1
                # get the replicator number
                index = server.chain_to_index[conn]
                # finalize the request
                server.finalize_request(index)
                # clean up data structures
                server.pending_conns.remove(server.name_to_conn[index])
                del server.name_to_conn[index]
                # look into the waiting queue for the replicator and see if we can start another request quickly
                to_try = [x for x in server.pending_reqs[index]]
                for request, attempted_conn in to_try:
                    # only try to service requests for the replicator that just freed up
                    chain_sock = server.chain_sockets[server.hash(request["username"]) % server.num_chains]
                    if chain_sock != conn:
                        continue
                    chain_servicer = server.start_request(request, attempted_conn)
                    # if we successfully started it, clean up data structures 
                    if chain_servicer != None:
                        server.name_to_conn[chain_servicer] = attempted_conn
                        server.pending_conns.add(attempted_conn)
                        server.pending_reqs[index].remove((request, attempted_conn))
                continue
            # read a request, getting status (1 for error on read, 0 for successful reading), and the request
            status, request = receive_data(conn)
            if status != 0:
                # send back error that occured
                error_msg = server.json_resp(False, request)
                try:
                    conn.send(format_message(error_msg))
                except Exception:
                    pass
                continue
            # if client connection was broken or closed, go back to waiting for a new connection
            if not request or request == {}:
                conn.close()
                server.socket_table.remove(conn)
                continue
            # if the request is not a leaderboard request, a replicator handles it. Otherwise, the broker handles it
            if request.get("action", None) != "leaderboard":
                # attempt to start the request
                server.pending_conns.add(conn)
                chain_servicer = server.start_request(request, conn)
                if chain_servicer != None:
                    server.name_to_conn[chain_servicer] = conn
            else:
                try:
                    conn.sendall(format_message(server.start_request(request, conn)))
                except Exception:
                    pass
        # at the end of every cycle, try and start any pending request at the front of each queue for each replicator
        for key in server.pending_reqs.keys():
            if server.chain_sockets[key] in server.name_to_conn.keys() or len(server.pending_reqs[key]) == 0:
                continue
            # get the request off the top of the queue
            request, attempted_conn = server.pending_reqs[key][0]
            chain_sock = server.chain_sockets[server.hash(request["username"]) % server.num_chains]
            chain_servicer = server.start_request(request, attempted_conn)
            if chain_servicer != None:
                server.name_to_conn[chain_servicer] = attempted_conn
                server.pending_conns.add(attempted_conn)
                server.pending_reqs[key].remove((request, attempted_conn))


if __name__ == "__main__":
    main()