import json
import os
import socket

host = "127.0.0.1"
port = 25564
global con
con = None


class D2DResponse:
    def __init__(self, resp):
        lines = resp.splitlines()
        self.header = {}
        self.data = ""

        parsing_content = False
        for line in lines:
            if parsing_content:
                self.data = self.data + line + os.linesep
            elif line.strip() == "":
                parsing_content = True
            else:
                key, value = line.split("=", 1)
                self.header[key.strip()] = value.strip()
        self.data = json.loads(self.data)


def d2d_send_json(json):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print(f"Connecting to ({host},{port})")
    sock.connect((host, port))
    data = "PROTOCOL=D2D\n"
    data += "VERSION=1.0\n"
    data += "TYPE=TEXT\n"
    data += "LENGTH=" + str(len(json.encode("utf-8"))) + "\n\n"
    data += json
    sock.sendall(data.encode("utf-8"))
    resp = sock.recv(8192)
    sock.close()
    if len(resp) == 0:
        print("Host closed connection")
        return b""
    return D2DResponse(resp.decode("utf-8"))


def d2d_wait_for_status_message():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print(f"Connecting to ({host},{port})")
    sock.connect((host, port))
    resp = sock.recv(8192)
    sock.close()
    if len(resp) == 0:
        print("Host closed connection")
        return b""
    return D2DResponse(resp.decode("utf-8"))
