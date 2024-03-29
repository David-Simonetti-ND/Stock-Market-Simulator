# File: Replicator.py
# Author: David Simonneti (dsimone2@nd.edu) and John Lee 
# 
# Description: Replicator class that performs broker operations

import socket
import sys
import time
import os
import json
import select
import signal
from StockMarketLib import format_message, receive_data, print_debug, VALID_TICKERS, StockMarketUser
from StockMarketBroker import StockMarketBroker

class Replicator(StockMarketBroker):
    
    def __init__(self, project_name, chain_num):
        """Initializes the replicator server.
        
        Also opens a UDP connection to the name server

        Args:
            project_name (str): name of the project
            chain_num    (int): replicator number
        """
        
        self.project_name = project_name
        self.chain_num = chain_num
        
        ## Socket Creation
        # create socket on any port from 9123-9223. This is done to play along with firewalls on crc machines.
        for i in range(100):
            # try to bind to port
            try:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                # set 60 seconds timeout waiting for a connection, so we can update the name server
                self.socket.settimeout(60)
                self.socket.bind((socket.gethostname(), 9123 + i))
                break
            # error if port already in use
            except Exception as e:
                self.socket.close()
            
            # if we can't get an open port after 100 attempts, just quit
            if i == 99:
                print("No open ports")
                exit(1)

        self.port_number = self.socket.getsockname()[1]
        print(f"Listening on port {self.port_number}")
        self.socket.listen()
        
        # for users and the leaderboard
        self.num_users = 0
        self.users = {}
        self.leaderboard = []
        # connection to broker 
        self.broker_conn = None

        # see if we need to perform a rebuild after a crash
        # if there is a checkpoint file or a transaction log, we will reload in stock market data from those files
        # set the txn_log to none to indicate that we are rebuilding from crash
        self.txn_log = None
        self.rebuild_server()
        # start new transaction log
        self.txn_log = open(f"table{self.chain_num}.txn", "w")
        self.txn_count = 0

        # send information to name server
        self.ns_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.ns_socket.connect(("catalog.cse.nd.edu", 9097))
        # update the leaderboard & name server every minute 
        signal.signal(signal.SIGALRM, self._update_ns_handler)
        signal.setitimer(signal.ITIMER_REAL, .1, 60) # now and every 60 seconds after
        
        self.select_socks = [self.socket]
        # keep track of latest stock info
        self.latest_stock_info = {}
    
    ##################
    # Socket Methods #
    ##################
    
    def _update_ns_handler(self, _, __):
        """signal-based async update of name server"""
        self._update_ns({"type" : f"chain-{chain_num}", "owner" : "dsimone2", "port" : self.port_number, "project" : self.project_name})

    def accept_new_connection(self):
        """Accepts a new connection and adds it to the socket table.
        """
        conn, addr = self.socket.accept()
        conn.settimeout(60)
        status, data = receive_data(conn)
        # if the connection doesnt tell us who they are, we ignore them
        if data is None or status == 2:
            return
        # if the connection is the broker
        if data["type"] == "broker":
            # update the broker connection to point to the new one
            if self.broker_conn:
                self.select_socks.remove(self.broker_conn)
                self.broker_conn.close()
            self.broker_conn = conn
            self.select_socks.append(conn)
    
    ###############
    # API Backend #
    ###############
    
    def _register_user(self, username, password):
        """Registers Users if they are not registered yet
        """
        # check its not already taken
        if username in self.users: 
            err = f"Username {username} is already in use."
            print_debug(err)
            return self.json_resp(False, err)
        self.write_txn(f"{time.time_ns()} REGISTER {len(username)} {username} {len(password)} {password}\n")
        self.users[username] = StockMarketUser(username, password)
        print_debug(f"User {username} was registered.")
        return self.json_resp(True, None)
    
    def _authenticate(self, username, password):
        """Authenticates and retrieves the associated user
        """
        if username not in self.users:
            err =  "User associated with Username does not exist."
            print_debug(err)
            return self.json_resp(False, err)
        else:
            user = self.users[username]
            # check password
            if user.password == password:
                print_debug(f"User {username} was authenticated.")
                return self.json_resp(True, user)
            else:
                err = f"Password for {username} is incorrect"
                print_debug(err)
                return self.json_resp(False, err)
            
    def _user_buy(self, user: StockMarketUser, request):
        """Purchase a stock
        """
        # check valid ticker to buy
        ticker = request.get("ticker", None)
        if ticker not in VALID_TICKERS or ticker is None:
            err = f"Ticker {ticker} is not valid."
            user.print_debug(err)
            return self.json_resp(False, f"Ticker {ticker} is not valid.")
        
        # check amount to purchase
        amount = request.get("amount", None)
        if amount is None:
            err = "Amount to purchase was not specified"
            user.print_debug(err)
            return self.json_resp(False, "Amount to purchase was not specified")
        else:
            try: 
                amount = int(amount)
            except Exception as e:
                err = f"Amount must be an integer value: {e}"
                user.print_debug(err)
                return self.json_resp(False, err)
            if amount < 0:
                err = f"Amount must be a positive value >0."
                user.print_debug(err)
                return self.json_resp(False, err)
            elif amount == 0:
                # automatic success
                succ = f"Purchased 0 shares of {ticker}."
                user.print_debug(succ)
                return self.json_resp(True, succ )
        
        # snapshot buy price
        buy_price = self.latest_stock_info[ticker]
        
        # can purchase
        if user.can_purchase(amount, buy_price):
            self.write_txn(f"{time.time_ns()} BUY {len(user.username)} {user.username} {ticker} {amount} {buy_price}\n")
            user.purchase(ticker, amount, buy_price)
            succ = f"Purchased {amount} shares of {ticker} at {buy_price}"
            user.print_debug(succ)
            return self.json_resp(True, succ)
        # insufficient funds
        else:
            err = f"Insufficient funds to purchase {amount} shares of {ticker} at {buy_price}"
            user.print_debug(err)
            return self.json_resp(False, err)
        
        
    def _user_sell(self, user: StockMarketUser, request):
        """Sell stocks
        """
        # check valid ticker to buy
        ticker = request.get("ticker", None)
        if ticker not in VALID_TICKERS or ticker is None:
            err =  f"Ticker {ticker} is not valid."
            user.print_debug(err)
            return self.json_resp(False, err)
        
        # check amount to purchase
        amount = request.get("amount", None)
        if amount is None:
            err = "Amount to sell was not specified"
            user.print_debug(err)
            return self.json_resp(False, err)
        else:
            try: 
                amount = int(amount)
            except Exception as e:
                err = f"Amount must be an integer value: {e}"
                user.print_debug(err)
                return self.json_resp(False, err)
            if amount < 0:
                err = f"Amount must be a positive value >0."
                user.print_debug(err)
                return self.json_resp(False, err)
            elif amount == 0:
                # automatic success
                succ = f"Sold 0 shares of {ticker}."
                user.print_debug(succ)
                return self.json_resp(True, succ)
            
        # snapshot sell price
        sell_price = self.latest_stock_info[ticker]
        
        # can sell
        if user.can_sell(amount, ticker):
            self.write_txn(f"{time.time_ns()} SELL {len(user.username)} {user.username} {ticker} {amount} {sell_price}\n")
            user.sell(ticker, amount, sell_price)
            succ = f"Sold {amount} shares of {ticker} at {sell_price}"
            user.print_debug(succ)
            return self.json_resp(True, succ)
        # insufficient shares
        else:
            err = f"Insufficient owned shares to sell {amount} shares of {ticker} at {sell_price}"
            user.print_debug(err)
            return self.json_resp(False, err)
        
        
    def _get_user_balance(self, user: StockMarketUser):
        """Gets a user's balance
        """
        # net worth
        worth = self._net_worth(user, self.latest_stock_info)
        
        # string representation & data repr
        user_rep = str(user) + f"Net Worth: {worth}"
        resp = {"Str": user_rep, "Net Worth": worth, "Cash": user.cash, "Stocks": user.stocks}
        user.print_debug("\n" + user_rep)
        return self.json_resp(True, resp)
    
    def _net_worth(self, user: StockMarketUser, stock_info):
        """Compute the net worth of an individual at a certian stock price
        """
        nw = user.cash
        for t in VALID_TICKERS:
            nw += user.stocks[t] * stock_info[t]
        return nw

    def _calculate_net_worths(self):
        """ Calculates net worth of all users
        """
        # snapshot stock information
        freeze_price = self.latest_stock_info.copy()
        # for every user, compute net worth
        net_worths = {}
        for user in self.users:
            net_worths[user] = self._net_worth(self.users[user], freeze_price)
        return net_worths
        
    ###################
    # Request Handler #
    ###################
        
    def perform_request(self, request):
        """Redirect requests from a client to appropriate function. 
        API calls are register, buy, sell, balance, leaderboard
        """
        # get action
        action = request.get("action", None)
        if action is None: return self.json_resp(False, "Action was not provided")
        
        ## Authenticate or Register
        
        # get username & password
        username = request.get("username", None)
        if username is None: return self.json_resp(False, "Username not provided.")
        password = request.get("password", None)
        if password is None: return self.json_resp(False, "Password not provided")
        if self.latest_stock_info == None:
            return self.json_resp(False, "Malformed request")

        # if the broker is polling us for leaderboard information, send it back all of our clients and their net worth
        if action == "broker_leaderboard":
            self.latest_stock_info = request.get("latest_stock_info", self.latest_stock_info)
            return self.json_resp(True, self._calculate_net_worths())
        # register the user
        elif action == 'register':
            return self._register_user(username, password)
        # autheticate using password
        else:
            result = self._authenticate(username, password)
            # if authentication failed return result
            if result['Success'] == False:
                return result
            # if successful, get the user
            else:
                user = result['Value']

        # switch statement to handle different request action
        if action == "buy":
            return self._user_buy(user, request)
        elif action == "sell":
            return self._user_sell(user, request)
        elif action == 'balance':
            return self._get_user_balance(user)
        elif action == 'leaderboard':
            return self._get_leaderboard()
        else:
            # handle case for invalid action specified
            return self.json_resp(False, f"{action} is an invalid action.")
    
    #######################
    # Persistence Methods #
    #######################
    
    def rebuild_server(self):
        """Rebuild the server by reading through ckpt & transaction log
        """
        # time the last checkpoint was made - used to see which transactions from the transactions log we should actually play back
        ckpt_time = 0
        # only rebuild from checkpoint if the file exists
        if os.path.isfile(f"table{self.chain_num}.ckpt"):
            f = open(f"table{self.chain_num}.ckpt", "r")
            # first line of checkpoint file is timestamp of when checkpoint was made 
            ckpt_time = int(f.readline())
            # read in state of hash table line by line
            for line in f.readlines():
                # the length of the username is seperated from the rest of the entry by the first space in the line
                username_len, rest = line.strip("\n").split(" ", 1)
                # convert to int
                username_len = int(username_len)
                # read in the key as that many characters
                username = rest[:username_len]

                # same for pw
                pw_len, rest = rest[username_len + 1:].split(" ", 1)
                # convert to int
                pw_len = int(pw_len)
                # read in the key as that many characters
                password = rest[:pw_len]

                # cash and stock amounts are the rest of the entry
                cash, stocks = rest[pw_len + 1:].split(" ", 1)
                cash = float(cash)
                stocks = json.loads(stocks)
                # add the entry to memory
                self.users[username] = StockMarketUser(username, password)
                self.users[username].cash = cash
                self.users[username].stocks = stocks
        # once we have rebuild from the checkpoint, attempt to play back the transaction log if it exists
        if os.path.isfile(f"table{self.chain_num}.txn"):
            f = open(f"table{self.chain_num}.txn", "r")
            # go line by line through the log
            for line in f.readlines():
                # format of each entry in the log is as such
                # TRANSACTION_LENGTH TIMESTAMP OPERATION USERNAME_LEN USERNAME TICKER AMOUNT PRICE
                # transaction_length is the total size of the transaction, to ensure no partial transactions get read
                # timestamp is the time in ns when the operation happened
                # OPERATION is either buy or sell
                # USERNAME_LEN is the length of USERNAME
                # TICKER, AMOUNT, and PRICE detail the contents of the transaction
                # each item is delimited by a space

                # read total transaction length and make sure it lines up
                total_length, rest = line.strip("\n").split(" ", 1)
                if len(rest) != int(total_length):
                    # otherwise, if we encounter a half completed transaction we just skip it
                    continue
                # get the timestamp from an entry - delimited by first space
                time, rest = rest.strip("\n").split(" ", 1)
                time = int(time)
                # we only replay this operation if it occured AFTER the latest checkpoint
                if time > ckpt_time:
                    # read the operation from the entry - delimited by second space
                    operation, rest = rest.split(" ", 1)
                    # if its an insert
                    if operation == "BUY":
                        # get the key length, which is delimited by the third space
                        username_len, rest = rest.split(" ", 1)
                        username_len = int(username_len)
                        # get the key and then the value is the rest of the entry
                        username = rest[:username_len]
                        ticker, amount, price = rest[username_len + 1:].split(" ")
                        # perform operation
                        self.users[username].purchase(ticker, float(amount), float(price))
                    elif operation == "SELL":
                        # get the key length, which is delimited by the third space
                        username_len, rest = rest.split(" ", 1)
                        username_len = int(username_len)
                        # get the key and then the value is the rest of the entry
                        username = rest[:username_len]
                        ticker, amount, price = rest[username_len + 1:].split(" ")
                        # perform operation
                        self.users[username].sell(ticker, float(amount), float(price))
                    elif operation == "REGISTER":
                        username_len, rest = rest.split(" ", 1)
                        username_len = int(username_len)
                        # get the key and then the value is the rest of the entry
                        username = rest[:username_len]
                    
                        pw_len, rest = rest[username_len + 1:].split(" ", 1)
                        pw_len = int(pw_len)
                        # get the key and then the value is the rest of the entry
                        password = rest[:pw_len]
                        self._register_user(username, password)
            # once we are done replaying all transactions, create a new checkpoint so we can delete the old transaction log
            self.create_checkpoint()

    def write_txn(self, message):
        """Writes TXN file
        """
        if self.txn_log == None:
            return
        # write transaction message to log
        # prepend length of transaction so we know if we had an incomplete write
        self.txn_log.write(f"{len(message) - 1} {message}")
        # flush and fsync to send data directly to disk
        self.txn_log.flush()
        os.fsync(self.txn_log)
        # another successful transaction
        self.txn_count += 1
        print_debug("TXN LOG written.")

    def create_checkpoint(self):
        """Writes CKPT file
        """
        # open shadow checkpoint file to begin checkpointing
        shadow_ckpt = open("./table.ckpt.shadow", "w")
        # write the current time as a header 
        shadow_ckpt.write(f"{time.time_ns()}\n")
        # iterate over every key value pair currently in the hash table and write it to the checkpoint file
        for username in self.users.keys():
            user = self.users[username]
            shadow_ckpt.write(f"{len(username)} {username} {len(user.password)} {user.password} {user.cash} {json.dumps(user.stocks)}\n")

        shadow_ckpt.close()
        # perform atomic update of checkpoint
        os.rename("./table.ckpt.shadow", f"./table{self.chain_num}.ckpt")
        # clear out the old transaction log only if we are compressing during normal operation. Otherwise, if we are restarting from a crash, the server will already overwrite the transaction log.
        if self.txn_log != None:
            self.txn_log.close()
            self.txn_log = open(f"table{self.chain_num}.txn", "w")
            
        print_debug("CKPT created.")     

    def listen(self):

        while True:

            # checkpoint after 100 transactions
            if self.txn_count >= 100:
                self.create_checkpoint()
                self.txn_count = 0
            
            readable, _, _ = select.select(self.select_socks, [], [], 5)

            if readable == []:
                continue

            # new incoming broker conn
            if self.socket in readable:
                self.accept_new_connection()
                readable.remove(self.socket)

            # broker is forwarding us a request
            if self.broker_conn in readable:
                status, data = receive_data(self.broker_conn)
                if status == 0 and data != None:
                    # update the latest stock info from new request
                    self.latest_stock_info = data.get("latest_stock_info", self.latest_stock_info)
                    # perform the request and forward it back
                    RPC_response = self.perform_request(data)
                    RPC_response = format_message(RPC_response)
                else:
                    RPC_response = format_message(self.json_resp(False, "Unintelligable request"))
                try:
                    self.broker_conn.sendall(RPC_response)
                except Exception:
                    pass
        
if __name__ == "__main__":
    # ensure only a port is given
    if len(sys.argv) != 3:
        print("Error: please enter project name and replication number as arguments")
        exit(1)
    try:
        chain_num = int(sys.argv[2])
    except Exception:
        print("Error: replication number must be an integer")
        exit(1)
        
    # create the replicator instance & listen
    chain = Replicator(sys.argv[1], chain_num)
    chain.listen()