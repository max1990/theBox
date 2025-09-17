import d2d_protocol
import json
import time
import socket

gns_ip = "127.0.0.1"
gns_port = 4444

resp = d2d_protocol.d2d_send_json(json.dumps({
    "ExternalGNS": 
    {
        "Enabled": True,
        "IP": gns_ip,
        "Port": gns_port,
        "Protocol": "UDP"
    }
}))

print("Server replied with the following External GNS Values")
print(resp.data["ExternalGNS"])

print("Sending some gyro data")
time.sleep(2.5)
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.sendto("$HEHDT,55,T*01\r\n".encode('utf-8'), (gns_ip, gns_port))
sock.close()

resp = d2d_protocol.d2d_wait_for_status_message()
print("Server replied with")
print("ExternalGNS: " + str(resp.data["ExternalGNS"]))
