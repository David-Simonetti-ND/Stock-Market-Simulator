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

class StockMarketBroker:
    def __init__(self, broker_name):
        """Initializes the stock market broker, accepting connections from a randomly selected port.
        
        Also opens a UDP connection to the name server

        Args:
            broker_Name (str): name of the broker
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
        
    
    def accept_new_connection(self):
        """Accepts a new connection and adds it to the socket table.
        """
        conn, addr = self.socket.accept()
        conn.settimeout(60)
        self.socket_table.add(conn)

    def ns_update(self):
        """Updates the name server with the current state
        """
        # create information message  
        message = json.dumps({"type" : "stockmarketbroker", "owner" : "dsimone2", "port" : self.port_number, "project" : self.broker_name})
        # send info to name server
        self.ns_socket.sendall(message.encode("utf-8"))
        print("DEBUG: Name Server Updated.")
        # keep track of last name server update
        self.last_ns_update = time.time_ns()

    
    def rebuild_server(self):
        # time the last checkpoint was made - used to see which transactions from the transactions log we should actually play back
        ckpt_time = 0
        # only rebuild from checkpoint if the file exists
        if os.path.isfile("table.ckpt"):
            f = open("table.ckpt", "r")
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
        if os.path.isfile("table.txn"):
            f = open("table.txn", "r")
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
    
    def json_resp(self, success, value):
        return {"Success": success, "Value": value}        
    
    def _register_user(self, username, password):
        """registers Users"""
        # check its not already taken
        if username in self.users: return self.json_resp(False, f"Username is already in use, please select a different one.")
        self.write_txn(f"{time.time_ns()} REGISTER {len(username)} {username} {len(password)} {password}\n")
        self.users[username] = StockMarketUser(username, password)
        print(f"DEBUG: User {username} was registered.")
        return self.json_resp(True, None)
    
    def _authenticate(self, username, password):
        """authenticates and retrieves the associated user"""
        if username not in self.users: 
            return self.json_resp(False, "User associated with Username does not exist.")
        else:
            user = self.users[username]
            # check password
            if user.password == password:
                print(f"DEBUG: User {username} was authenticated.")
                return self.json_resp(True, user)
            else:
                return self.json_resp(False, "Password does not match username provided.")
            
    def _user_buy(self, user, request):
        """Purchase a stock"""
        # check valid ticker to buy
        ticker = request.get("ticker", None)
        if ticker not in VALID_TICKERS or ticker is None:
            return self.json_resp(False, f"Ticker {ticker} is not valid.")
        
        # check amount to purchase
        amount = request.get("amount", None)
        if amount is None:
            return self.json_resp(False, "Amount to purchase was not specified")
        else:
            try: 
                amount = int(amount)
            except Exception as e:
                return self.json_resp(False, f"Amount must be an integer value: {e}")
            if amount < 0:
                return self.json_resp(False, f"Amount must be a positive value >0.")
            elif amount == 0:
                # automatic success
                return self.json_resp(True, f"Purchased 0 shares of {ticker}.")
        
        buy_price = self.latest_stock_info[ticker]
        if user.can_purchase(amount, buy_price):
            self.write_txn(f"{time.time_ns()} BUY {len(user.username)} {user.username} {ticker} {amount} {buy_price}\n")
            user.purchase(ticker, amount, buy_price)
            print(f"DEBUG: {user.username} purchased {amount} stocks of {ticker} at {buy_price}")
            return self.json_resp(True, f"Purchased {amount} shares of {ticker} at {buy_price}.")
        else:
            print(f"DEBUG: {user.username} could not afford {amount} stocks of {ticker} at {buy_price}")
            return self.json_resp(False, f"Insufficient funds to purchase {amount} shares of {ticker} at {buy_price}")
        
        
    def _user_sell(self, user, request):
        """Sell stocks """
        # check valid ticker to buy
        ticker = request.get("ticker", None)
        if ticker not in VALID_TICKERS or ticker is None:
            return self.json_resp(False, f"Ticker {ticker} is not valid.")
        
        # check amount to purchase
        amount = request.get("amount", None)
        if amount is None:
            return self.json_resp(False, "Amount to sell was not specified")
        else:
            try: 
                amount = int(amount)
            except Exception as e:
                return self.json_resp(False, f"Amount must be an integer value: {e}")
            if amount < 0:
                return self.json_resp(False, f"Amount must be a positive value >0.")
            elif amount == 0:
                # automatic success
                return self.json_resp(True, f"Sold 0 shares of {ticker}.")
        
        sell_price = self.latest_stock_info[ticker]
        if user.can_sell(amount, ticker):
            self.write_txn(f"{time.time_ns()} SELL {len(user.username)} {user.username} {ticker} {amount} {sell_price}\n")
            user.sell(ticker, amount, sell_price)
            print(f"DEBUG: {user.username} sold {amount} stocks of {ticker} at {sell_price}")
            return self.json_resp(True, f"Sold {amount} shares of {ticker} at {sell_price}.")
        else:
            print(f"DEBUG: {user.username} could not sell {amount} stocks of {ticker} at {sell_price}")
            return self.json_resp(False, f"Insufficient owned shares to sell {amount} shares of {ticker} at {sell_price}")
        
        
    def _get_user_balance(self, user):
        """Gets a user's balance
        """
        # net worth
        worth = user.cash
        for ticker in VALID_TICKERS:
            worth += self.latest_stock_info[ticker] * self.stocks[ticker]
        
        user_rep = str(user) + f"Net Worth: {worth}"
        return self.json_resp(True, user_rep)
        
    def _get_leaderboard(self):
        """reports the top 10 users
        """
        if self.leaderboard == []:
            self._update_leaderboard(None, None)
        # Top 10
        lstring = "TOP 10\n" + "---------------\n"
        try:
            for i in range(10):
                lstring += self.leaderboard[i][0].username + ' | ' + str(round(self.leaderboard[i][1], 2))
        except:
            pass
        return self.json_resp(True, lstring)
        
    def perform_request(self, request):
        """Redirect requests from a client to appropriate function.

        Args:
            request (_type_): _description_

        Returns:
            _type_: _description_
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

        # register the user
        if action == 'register':
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


    # takes in the transaction message and writes it to the log
    def write_txn(self, message):
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

    def create_checkpoint(self):
        # open shadow checkpoint file to begin checkpointing
        shadow_ckpt = open("table.ckpt.shadow", "w")
        # write the current time as a header 
        shadow_ckpt.write(f"{time.time_ns()}\n")
        # iterate over every key value pair currently in the hash table and write it to the checkpoint file
        for username in self.users.keys():
            user = self.users[username]
            shadow_ckpt.write(f"{len(username)} {username} {len(user.password)} {user.password} {user.cash} {json.dumps(user.stocks)}")

        shadow_ckpt.close()
        # perform atomic update of checkpoint
        os.rename("table.ckpt.shadow", "table.ckpt")
        # clear out the old transaction log only if we are compressing during normal operation. Otherwise, if we are restarting from a crash, the server will already overwrite the transaction log.
        if self.txn_log != None:
            self.txn_log.close()
            self.txn_log = open("table.txn", "w")

def main():
    # ensure only a port is given
    if len(sys.argv) != 2:
        print("Error: please enter project name as the only argument")
        exit(1)

    server = StockMarketBroker(sys.argv[1])

    while True:
        # if 1 minute has passed, perform a name server update
        if (time.time_ns() - server.last_ns_update) >= (60*1000000000):
            server.ns_update()
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
            server.latest_stock_info = json.loads(data)
            readable.remove(server.stockmarketsim_sock)
        # otherwise we have at least one client connection with data available
        # handle all pendings reads before performing select again
        while len(readable) > 0:
            # check if we should perform a name server update
            if (time.time_ns() - server.last_ns_update) >= (60*1000000000):
                server.ns_update()
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

            # peform the request the client submitted
            RPC_response = server.perform_request(request)
            # send response 
            try:
                # if the client disconnects before we try to send, get a new connection
                conn.sendall(format_message(RPC_response))
            except Exception:
                continue


if __name__ == "__main__":
    main()