# File: StockMarketEndpoint.py
# Author: John Lee (jlee88@nd.edu) & David Simonneti (dsimone2@nd.edu) 

# Description: Class/Endpoint that clients utilize to connect to the broker server

import socket, json, time
import random
import threading
from StockMarketLib import format_message, receive_data, lookup_server, SUBSCRIBE_TIMEOUT, print_debug

class StockMarketEndpoint:
    """API Endpoint for a user to connect to the broker/simulator with
    """

    def __init__(self, name, username, password):
        self.name = name
        self.username = username
        self.password = password
        
        # connect to broker & simulator
        self.connect_to_broker()
        self.subscribe_to_simulator(resub=False)
        
        # asyncronously recieve updates.
        self.recent_price = {"time": 0}
        simulator_thread = threading.Thread(target=self.async_get_stock_update, daemon=True)
        simulator_thread.start()
    
    ##################
    # Socket Methods #
    ##################
    
    def connect_to_broker(self):
        """Connect to the broker by searching the name server.
        """
        # keep track of timeouts - exponentially increase by a factor of 2 each failed attempt
        timeout = 1
        while True:
            # lookup all brokers with the right name and type
            possible_brokers = lookup_server(self.name, "stockmarketbroker")
            # try to connect to each server
            for broker in possible_brokers:
                try:
                    # print_debug(f"Trying to connect to {broker}")
                    # create new socket and attempt connection
                    self.broker_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.broker_socket.connect((broker["name"], broker["port"]))
                    print_debug("Connected to Broker.")
                    # if we are successful, we can return with a complete connection
                    return
                except Exception as e:
                    # unable to connect, try another
                    pass
            # print error, wait a little, and try again
            print(f"Unable to connect to any potential brokers, retrying in {timeout} seconds")
            time.sleep(timeout)
            timeout *= 2

    def subscribe_to_simulator(self, resub = True):
        """Subscribes to the simulator using a TCP
        """
        # keep track of timeouts - exponentially increase by a factor of 2 each failed attempt
        self.info_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.info_sock.bind((socket.gethostname(), 0))
        self.info_sock.settimeout(5)
        sock_info = self.info_sock.getsockname()
        timeout = 1
        while True:
            # lookup all brokers with the right name and type
            possible_sims = lookup_server(self.name, "stockmarketsim")
            # try to connect to each server
            for sim in possible_sims:
                try:
                    # create new socket and attempt connection
                    # print_debug(f"Trying to subscribe to {sim}")
                    self.sim_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.sim_socket.connect((sim["name"], sim["port"]))
                    self.sim_socket.sendall(format_message({"hostname": sock_info[0], "port": sock_info[1], "resub": resub}))
                    self.sim_socket.close()
                    self.last_sub_time = time.time_ns()
                    print_debug("Resubscribed to StockMarketSim.")
                    # if we are successful, we can return with a complete connection
                    return
                except Exception as e:
                    # unable to connect, try another
                    pass
            # print error, wait a little, and try again
            print(f"Unable to connect to the stock market simulator , retrying in {timeout} seconds")
            time.sleep(timeout)
            timeout *= 2
        
    
    def send_request_to_broker(self, request):
        """Takes in a request, formats it to protocol, sends it off, and tries to read a response
        """
        timeout = 1
        encoded_request = format_message(request)
        if encoded_request == None:
            print(f"Error: Unable to convert request {request} to json")
            return None
        while True:
            # try to send request
            try:
                self.broker_socket.sendall(encoded_request)
            # if server doesn't accept request, print error, close connection to server, reconnect, and try again
            except Exception:
                print(f"Unable to send request to broker, retrying in {timeout} seconds")
                time.sleep(timeout)
                timeout *= 2
                self.close_connection()
                self.connect_to_broker(timeout)
                continue
            # wait up to 5 seconds for a response
            #self.broker_socket.settimeout(5)
            status, response = receive_data(self.broker_socket)
            # Error case where we timeout before getting all the data
            if response == None or status != 0:
                print(f"Unable receive response from broker, retrying in {timeout} seconds")
                time.sleep(timeout)
                timeout *= 2
                self.close_connection()
                self.connect_to_broker()
            else:
                return response

    def close_connection(self):
        """Closes connection
        """
        self.broker_socket.close()
        
    ################
    # Data Methods #
    ################
    
    def get_stock_update(self):
        """ Returns local storage of stock update which is updated asynchronously
        """
        return self.recent_price

    def async_get_stock_update(self):
        """Recieve the last stock update asyncronously, and if data is missed, ignore.
        Recv is blocking, so other threads can run while blocking.
        """
        while True:
            if (time.time_ns() - self.last_sub_time) > SUBSCRIBE_TIMEOUT * random.uniform(.8, .9):
                self.subscribe_to_simulator()
            try:
                self.recent_price = json.loads(self.info_sock.recv(1024))
            except Exception as e:
                
                print_debug("Could not get data", e)
                pass

    #############
    # API Calls #
    #############

    def register(self, registered_ok = False):
        """Registers user with broker
        
        registered_ok (bool): flag that avoids exception if user is already registered.
        """
        request = {"action": "register", "username": self.username, "password": self.password}
        resp = self.send_request_to_broker(request)
        if resp['Success'] == False and not registered_ok:
            raise Exception(resp['Value'])
        return resp['Value']

    def buy(self, ticker, amount):
        """Sends a buy request to broker
        
        ticker (str): ticker to buy
        amount (int): amount to purchase. must be an int
        """
        request = {"action": "buy", "ticker": ticker, "amount": amount, "username": self.username, "password": self.password}
        resp = self.send_request_to_broker(request)
        return resp

    def sell(self, ticker, amount):
        """Sends a sell request to broker
        
        ticker (str): ticker to sell
        amount (int): amount to sell. must be an int
        """
        request = {"action": "sell", "ticker": ticker, "amount": amount, "username": self.username, "password": self.password}
        resp = self.send_request_to_broker(request)
        return resp
    
    def get_leaderboard(self):
        """Retrieves leaderboard of players
        """
        request = {"action": "leaderboard", "username": self.username, "password": self.password}
        resp = self.send_request_to_broker(request)
        if resp['Success'] == False:
            raise Exception(resp['Value'])
        return resp['Value']

    def get_balance(self):
        """Retrieves user's balance
        """
        request = {"action": "balance", "username": self.username, "password": self.password}
        resp = self.send_request_to_broker(request)
        if resp['Success'] == False:
            raise Exception(resp['Value'])
        return resp['Value']

        

