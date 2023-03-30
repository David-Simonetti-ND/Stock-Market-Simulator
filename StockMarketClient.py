import socket, http.client, json, time
from txnLib import format_message, receive_data

class StockMarketClient:

    def __init__(self):
        pass

    # make connection to server with global socket
    def connect_to_server(self, project_name):
        self.project_name = project_name
        # keep track of timeouts - exponentially increase by a factor of 2 each failed attempt
        timeout = 1
        while True:
            # lookup all servers with the right project name and type
            possible_servers = self.lookup_project(project_name)
            # try to connect to each server
            for server in possible_servers:
                try:
                    # create new socket and attempt connection
                    self.hash_table_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.hash_table_socket.settimeout(60)
                    self.hash_table_socket.connect((server["name"], server["port"]))
                    # if we are successful, we can return with a complete connection
                    return
                except Exception as e:
                    # unable to connect, try another
                    pass
            # print error, wait a little, and try again
            print(f"Unable to connect to any potential servers, retrying in {timeout} seconds")
            time.sleep(timeout)
            timeout *= 2
    
    def lookup_project(self, project_name):
        timeout = 1
        while True:
            # make http connection to name server and get json formatted info
            try:
                self.ns_conn = http.client.HTTPConnection('catalog.cse.nd.edu:9097')
                self.ns_conn.request("GET", "/query.json")
                html = self.ns_conn.getresponse().read()
                self.ns_conn.close()
            except Exception:
                print(f"Unable to lookup {project_name} from catalog server, retrying in {timeout} seconds")
                time.sleep(timeout)
                timeout *= 2
                continue

            # load into python dict
            json_response = json.loads(html)
            # iterate over all servers and check which ones have the correct project name and type
            possible_servers = []
            for server in json_response:
                if server.get("project", None) == project_name and server.get("type", None) == "hashtable":
                    possible_servers.append(server)
            # error case for no servers found - try again
            if possible_servers == []:        
                print(f"Unable to lookup {project_name} from catalog server, retrying in {timeout} seconds")
                time.sleep(timeout)
                timeout *= 2
                continue
            return possible_servers

    # takes in a request, formats it to protocol, sends it off, and tries to read a response
    def send_request_to_server(self, request):
        timeout = 1
        encoded_request = format_message(request)
        if encoded_request == None:
            print(f"Error: Unable to convert request {request} to json")
            return None
        while True:
            # try to send request
            try:
                self.hash_table_socket.sendall(encoded_request)
            # if server doesn't accept request, print error, close connection to server, reconnect, and try again
            except Exception:
                print(f"Unable to send request to server, retrying in {timeout} seconds")
                time.sleep(timeout)
                timeout *= 2
                self.close_connection()
                self.connect_to_server(timeout)
                continue
            # wait up to 5 seconds for a response
            self.hash_table_socket.settimeout(5)
            status, response = receive_data(self.hash_table_socket)
            # Error case where we timeout before getting all the data
            if response == None or status == 1:
                print(f"Unable receive response from server, retrying in {timeout} seconds")
                time.sleep(timeout)
                timeout *= 2
                self.close_connection()
                self.connect_to_server(self.project_name)
            else:
                return response

    def close_connection(self):
        self.hash_table_socket.close()

    def buy(self, ticker, amount):
        request = {"action": "buy", "ticker": ticker, "amount": amount}
        return self.send_request_to_server(request)

    def sell(self, ticker, amount):
        request = {"action": "sell", "ticker": ticker, "amount": amount}
        return self.send_request_to_server(request)

    def get_price(self, ticker):
        request = {"action": "get_price", "ticker": ticker}
        return self.send_request_to_server(request)

