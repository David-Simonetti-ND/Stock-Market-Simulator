import json

VALID_TICKERS = ["TSL", "TSF", "PER", "BKF", "NLE"]
VALID_STOCK_NAMES = ["Telsa", "TinySoft", "Pear", "BookFace", "Nile"]

SUBSCRIBE_TIMEOUT = 5 * (10 ** 9)

# this is a helper library that the broker and endpoint both use

# takes in a json message and returns it in binary format ready to send
# the format in which messages are passed is as follows
# {length of request in bytes}\n{request}\n
# with the newlines being sent as bytes and not the character \ followed by the character n
def format_message(json_message):
    # try to turn the request into json
    try:
        request_str = f"{json.dumps(json_message)}"
    except Exception:
        return None
    # create request in binary format
    request_len = f"{str(len(request_str))}"
    encoded_request = f"{request_len}\n{request_str}\n".encode("utf-8")
    return encoded_request

# function that takes a socket and attempts to read a properly formatted message from it
# returns a tuple where the first element is either a 0 for a success or 1 for a failure
# and the second element is the error, complete request, or nothing if applicable
def receive_data(socket):
    full_request = ""
    size = -1
    # we might only get part of the message at a time, so try while socket is still open
    # this first while loop attempts to get the size of the reques
    while True:
        # try and except catches if the client resets the connection
        try:
            partial_request = socket.recv(1024)
        except Exception as e:
            # indicate the client has disconnected
            return (1, "Request timed out")
        # if we read 0 bytes, client has closed connection
        if len(partial_request) == 0:
            return (0, None)
        # decode whatever part of the string we got and add it to the part of the string we have
        partial_string = partial_request.decode("utf-8")
        full_request += partial_string
        # if we encounter a newline, we must have received the sized of the request
        try:
            size_delimiter = full_request.index("\n")
            break
        except Exception:
            pass
    # try and get the size from the request
    try:
        size = int(full_request.split("\n")[0])
    # error if the client formatted message improperly
    except Exception:
        return (2, "Length of request in header must be an integer")
    # remove the length from the rest of the message and keep reading the rest of the message
    full_request = full_request.split("\n", 1)[1]
    # while we haven't found the final delimiting newlije
    while full_request.find("\n") == -1:
        # try and get more data
        try:
            partial_request = socket.recv(1024)
        # if the client reset connection, or closed the connection, quit and wait for a new connection
        except Exception as e:
            return (1, "Request timed out")
        if len(partial_request) == 0:
            return (0, None)
        # add the newly read parts of the request to the running total
        partial_string = partial_request.decode("utf-8")
        full_request += partial_string
    # get rid of the delimiting newline
    full_request = full_request.strip("\n")
    # make sure size of request matches what is in header
    if len(full_request) != size:
        return (2, "Length of request in header does not match actual request length")
    # load the request into json format internally
    try:
        request_json = json.loads(full_request)
    # case when invalid json is given in request
    except Exception:
        return (2, "Json is not valid")
    return (0, request_json)