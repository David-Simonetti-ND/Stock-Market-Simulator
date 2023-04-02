import random
import time
import socket
import json
import select
import sys
from StockMarketLib import format_message, receive_data, VALID_TICKERS, SUBSCRIBE_TIMEOUT

class StockMarketSimulator:
    def __init__(self, name):
        self.name = name
        self.num_stocks = len(VALID_TICKERS)
        self.stock_prices = [100] * self.num_stocks
        random.seed(time.time())

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.socket.bind((socket.gethostname(), 0))
        # error if port already in use
        except:
            print("Error: port in use")
            exit(1)
        self.port_number = self.socket.getsockname()[1]
        print(f"Listening on port {self.port_number}")

        self.socket.listen()
        self.send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # use a set to keep track of all open sockets 
        self.socket_table = set()

        # send information to name server
        self.ns_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.ns_socket.connect(("catalog.cse.nd.edu", 9097))
        self.ns_update()

    def simulate_one_tick(self):
        for i in range(self.num_stocks):
            self.stock_prices[i] += random.randrange(-10, 10)

    def publish_stock_data(self):
        update = {"type" : "stockmarketsimupdate", "time": time.time_ns()}
        for i in range(self.num_stocks):
            update[VALID_TICKERS[i]] = self.stock_prices[i]
        message = json.dumps(update)
        out_of_date_subs = [sub for sub in self.socket_table if (time.time_ns() - sub[1] > (SUBSCRIBE_TIMEOUT)) ]
        for sub in out_of_date_subs:
            self.socket_table.remove(sub)
        for sub_sock in self.socket_table:
            self.send_sock.sendto(message.encode("utf-8"), sub_sock[0])

    def accept_new_connection(self):
        conn, addr = self.socket.accept()
        error_code, data = receive_data(conn)
        conn.close()
        self.socket_table.add(((data["hostname"], data["port"]), time.time_ns()))

    def ns_update(self):
        # create information message  
        message = json.dumps({"type" : "stockmarketsim", "owner" : "dsimone2", "port" : self.port_number, "project" : self.name})
        # send info to name server
        self.ns_socket.sendall(message.encode("utf-8"))
        # keep track of last name server update
        self.last_ns_update = time.time_ns()

if __name__ == "__main__":
    server = StockMarketSimulator(sys.argv[1])
    while True:
        # if 1 minute has passed, perform a name server update
        if (time.time_ns() - server.last_ns_update) >= (60*1000000000):
            server.ns_update()
        # check if there are new subscribers
        readable, _, _ = select.select([server.socket], [], [], 0)

        # if we have new subscribers, add them
        if readable != []:
            for sock in readable:
                server.accept_new_connection()

        start_time = time.time_ns()
        server.publish_stock_data()
        print(f"Publishing took { (time.time_ns() - start_time) / (10 ** 9)} seconds, {len(server.socket_table)}")
        