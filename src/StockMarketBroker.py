import socket
import sys
import time
import os
import json
import select
import random
import http.client
from StockMarketLib import format_message, receive_data, VALID_TICKERS

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
            self.socket.bind((socket.gethostname(), 1))
        # error if port already in use
        except:
            print("Error: port in use")
            exit(1)

        self.port_number = self.socket.getsockname()[1]
        print(f"Listening on port {self.port_number}")
        
        self.socket.listen()
        # use a set to keep track of all open sockets - master socket is the first socket
        self.socket_table = set([self.socket])

        #!!!!!!!!!!!!!!!!!!! TODO
        '''
        # see if we need to perform a rebuild after a crash
        # if there is a checkpoint file or a transaction log, we will reload in stock market data from those files
        # set the txn_log to none to indicate that we are rebuilding from crash
        self.txn_log = None
        self.rebuild_server()
        # once the server is rebuilt, there is two cases
        # start new transaction log
        self.txn_log = open("table.txn", "w")
        self.txn_count = 0
        '''

        # send information to name server
        self.ns_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.ns_socket.connect(("catalog.cse.nd.edu", 9097))
        self.ns_update()

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
        # keep track of last name server update
        self.last_ns_update = time.time_ns()

    
    def rebuild_server(self):
        return
        # time the last checkpoint was made - used to see which transactions from the transactions log we should actually play back
        ckpt_time = 0
        # only rebuild from checkpoint if the file exists
        if os.path.isfile("table.ckpt"):
            f = open("table.ckpt", "r")
            # first line of checkpoint file is timestamp of when checkpoint was made 
            ckpt_time = int(f.readline())
            # read in state of hash table line by line
            for line in f.readlines():
                # format of checkpoint entry
                # KEY_LENTH KEY VALUE
                # where KEY_LENGTH is the length of KEY
                # each element is delimited by a space

                # the length of the key is seperated from the rest of the entry by the first space in the line
                key_len, rest = line.strip("\n").split(" ", 1)
                # convert to int
                key_len = int(key_len)
                # read in the key as that many characters
                key = rest[:key_len]
                # the value is then the rest of the entry
                value = json.loads(rest[key_len:])
                # add the entry to memory
                self.hash_table.insert(key, value)
        # once we have rebuild from the checkpoint, attempt to play back the transaction log if it exists
        if os.path.isfile("table.txn"):
            f = open("table.txn", "r")
            # go line by line through the log
            for line in f.readlines():
                # format of each entry in the log is as such
                # TRANSACTION_LENGTH TIMESTAMP METHOD KEY_LENGTH KEY [VALUE]
                # where value is optional depending on the method
                # transaction_length is the total size of the transaction, to ensure no partial transactions get read
                # timestamp is the time in ns when the operation happened
                # method is which hash table method was invoked (either INSERT or REMOVE)
                # KEY_LENGTH is the length of KEY
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
                    if operation == "INSERT":
                        # get the key length, which is delimited by the third space
                        key_len, rest = rest.split(" ", 1)
                        key_len = int(key_len)
                        # get the key and then the value is the rest of the entry
                        key = rest[:key_len]
                        value = json.loads(rest[key_len:])
                        # perform operation
                        self.hash_table.insert(key, value)
                    elif operation == "REMOVE":
                        # if its a remove operation, we only have key length and key
                        key_len, rest = rest.split(" ", 1)
                        key_len = int(key_len)
                        key = rest[:key_len]
                        self.hash_table.remove(key)
            # once we are done replaying all transactions, create a new checkpoint so we can delete the old transaction log
            self.create_checkpoint()
            
    def perform_request(self, request):
        """Redirect requests from a client to appropriate function.

        Args:
            request (_type_): _description_

        Returns:
            _type_: _description_
        """
        # see what parameters are provided in json
        action = request.get("action", None)
        ticker = request.get("ticker", None)
        if ticker not in VALID_TICKERS:
            error_msg = {"Result": "Error", "Value": f"Ticker {ticker} is not valid"}
            return error_msg
        amount = request.get("amount", None)
        if amount != None:
            try:
                amount = int(amount)
            except Exception as e:
                error_msg = {"Result": "Error", "Value": "Amount must be an integer value"}
                return error_msg
            if amount <= 0:
                error_msg = {"Result": "Error", "Value": "Amount must be greater than 0"}
                return error_msg

        # switch statement to handle different request action
        if action == "buy":
            # ticker and amount required
            if ticker == None or amount == None:
                error_msg = {"Result": "Error", "Value": "Ticker and amount required for buy request"}
                return error_msg
            print(f"Buying {amount} stocks of {ticker}")
            # before we perform the operation, we write to the transaction log
            #self.write_txn(f"{time.time_ns()} INSERT {len(key)} {key} {json.dumps(value)}\n")
            # preform operation
            # return code is 0 for success, 1 for failure
            # message indicates what failure it was 
            # hash_value is returned value (optional)
            #return_code, msg, hash_value = self.hash_table.insert(key, value)
        elif action == "sell":
            if ticker == None or amount == None:
                error_msg = {"Result": "Error", "Value": "Ticker and amount required for sell request"}
                return error_msg
            print(f"Selling {amount} stocks of {ticker}")
            #return_code, msg, hash_value = self.hash_table.lookup(key)
        elif action == "get_price":
            if ticker == None:
                error_msg = {"Result": "Error", "Value": "Ticker required for get_price request"}
                return error_msg
            # before we perform the operation, we write to the transaction log
            # self.write_txn(f"{time.time_ns()} REMOVE {len(key)} {key}\n")
            # return_code, msg, hash_value = self.hash_table.remove(key)
        else:
            # handle case for invalid action specified
            error_msg = {"Result": "Error", "Value": "Invalid action specified"}
            return error_msg

        return {"Result": "Success", "Value": 0}
        # case where operation occured successfully
        if return_code == 0:
            ret_msg = {"Result": "Success", "Value": hash_value}
            return ret_msg
        # case where operation failed
        else:
            ret_msg = {"Result": "Error", "Value": msg}
            return ret_msg

    # takes in the transaction message and writes it to the log
    def write_txn(self, message):
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
        for key, value in self.hash_table.get_hash_table_contents():
            # KEY_LENGTH KEY VALUE
            shadow_ckpt.write(f"{len(key)} {key} {json.dumps(value)}\n")

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
        readable, _, _ = select.select(list(server.socket_table), [], [], 5)
        # if no sockets are readable, try again
        if readable == []:
            continue
        # if the master socket is in the readable list, give it priority and accept the new incomming client
        if server.socket in readable:
            server.accept_new_connection()
            readable.remove(server.socket)
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
                error_msg = {"Result": "Error", "Value": request}
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