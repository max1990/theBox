import json

import d2d_protocol

resp = d2d_protocol.d2d_send_json(json.dumps({"TxMode": "normal"}))

print("Server replied with the following Tx values")
print(resp.data)
print("TxMode: " + resp.data["TxMode"])
print("TxPower: " + str(resp.data["TxPower"]))
print("TxRange: " + str(resp.data["TxRange"]))
