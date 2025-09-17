import json

import d2d_protocol

asterix_host = "192.168.4.100"
asterix_port = 25563

resp = d2d_protocol.d2d_send_json(
    json.dumps(
        {
            "AsterixCat010": {
                "Enabled": True,
                "IP": asterix_host,
                "Port": asterix_port,
                "Protocol": "UDP",
            }
        }
    )
)

print("Server replied with the following Asterix Cat 010 Values")
print(resp.data["AsterixCat010"])

# Enable TX Mode Normal
# resp = d2d_protocol.d2d_send_json(json.dumps({
#    "TxMode": "normal"
# }))

# Listen for tracks
# sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# sock.bind((asterix_host, asterix_port))

# print(f"Listening for asterix messages")
# recvd = sock.recv(8192)
# if recvd[0] != 0x0a:
#     print("Not Asterix Cat 010")
# else:
#     print("Got Asterix Cat 010 Message")

# sock.close()
