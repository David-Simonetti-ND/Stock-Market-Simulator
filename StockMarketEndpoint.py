import socket, http.client, json, time
from StockMarketLib import format_message, receive_data, SUBSCRIBE_TIMEOUT

class StockMarketEndpoint:

    def __init__(self, name):
        self.name = name
        self.subscribe_to_simulator()

    # make connection to broker
    def connect_to_broker(self):
        # keep track of timeouts - exponentially increase by a factor of 2 each failed attempt
        timeout = 1
        while True:
            # lookup all brokers with the right name and type
            possible_brokers = self.lookup_server(self.name, "stockmarketbroker")
            # try to connect to each server
            for broker in possible_brokers:
                try:
                    # create new socket and attempt connection
                    self.broker_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.broker_socket.connect((broker["name"], broker["port"]))
                    # if we are successful, we can return with a complete connection
                    return
                except Exception as e:
                    # unable to connect, try another
                    pass
            # print error, wait a little, and try again
            print(f"Unable to connect to any potential brokers, retrying in {timeout} seconds")
            time.sleep(timeout)
            timeout *= 2

    def subscribe_to_simulator(self):
        # keep track of timeouts - exponentially increase by a factor of 2 each failed attempt
        self.info_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.info_sock.bind((socket.gethostname(), 0))
        self.info_sock.settimeout(5)
        sock_info = self.info_sock.getsockname()
        timeout = 1
        while True:
            # lookup all brokers with the right name and type
            possible_brokers = self.lookup_server(self.name, "stockmarketsim")
            # try to connect to each server
            for broker in possible_brokers:
                try:
                    # create new socket and attempt connection
                    self.broker_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.broker_socket.connect((broker["name"], broker["port"]))
                    self.broker_socket.sendall(format_message({"hostname": sock_info[0], "port": sock_info[1]}))
                    self.broker_socket.close()
                    self.last_sub_time = time.time_ns()
                    # if we are successful, we can return with a complete connection
                    return
                except Exception as e:
                    # unable to connect, try another
                    pass
            # print error, wait a little, and try again
            print(f"Unable to connect to any potential brokers, retrying in {timeout} seconds")
            time.sleep(timeout)
            timeout *= 2
        

    def receive_latest_stock_update(self):
        if (time.time_ns() - self.last_sub_time) > SUBSCRIBE_TIMEOUT:
            self.subscribe_to_simulator()
        try:
            return self.info_sock.recv(1024)
        except Exception:
            return self.receive_latest_stock_update()
    
    def lookup_server(self, broker_name, type):
        timeout = 1
        while True:
            # make http connection to name server and get json formatted info
            try:
                self.ns_conn = http.client.HTTPConnection('catalog.cse.nd.edu:9097')
                self.ns_conn.request("GET", "/query.json")
                html = self.ns_conn.getresponse().read()
                self.ns_conn.close()
            except Exception:
                print(f"Unable to lookup {broker_name} from catalog server, retrying in {timeout} seconds")
                time.sleep(timeout)
                timeout *= 2
                continue

            # load into python dict
            json_response = json.loads(html)
            # iterate over all servers and check which ones have the correct broker name and type
            possible_brokers = []
            for broker in json_response:
                if broker.get("project", None) == broker_name and broker.get("type", None) == type:
                    possible_brokers.append(broker)
            # error case for no servers found - try again
            if possible_brokers == []:        
                print(f"Unable to lookup {broker_name} from catalog server, retrying in {timeout} seconds")
                time.sleep(timeout)
                timeout *= 2
                continue
            return possible_brokers

    # takes in a request, formats it to protocol, sends it off, and tries to read a response
    def send_request_to_broker(self, request):
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
            self.broker_socket.settimeout(5)
            status, response = receive_data(self.broker_socket)
            # Error case where we timeout before getting all the data
            if response == None or status == 1:
                print(f"Unable receive response from broker, retrying in {timeout} seconds")
                time.sleep(timeout)
                timeout *= 2
                self.close_connection()
                self.connect_to_broker(self.broker_name)
            else:
                return response

    def close_connection(self):
        self.broker_socket.close()

    def buy(self, ticker, amount):
        request = {"action": "buy", "ticker": ticker, "amount": amount}
        return self.send_request_to_broker(request)

    def sell(self, ticker, amount):
        request = {"action": "sell", "ticker": ticker, "amount": amount}
        return self.send_request_to_broker(request)

    def get_price(self, ticker):
        request = {"action": "get_price", "ticker": ticker}
        return self.send_request_to_broker(request)

