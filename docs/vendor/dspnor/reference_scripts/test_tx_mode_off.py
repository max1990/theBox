import d2d_protocol
import json

resp = d2d_protocol.d2d_send_json(json.dumps({
    "TxMode": "off"
}))

print("Server replied with the following Tx values")
print("TxMode: " + resp.data["TxMode"])
print("TxPower: " + str(resp.data["TxPower"]))
print("TxRange: " + str(resp.data["TxRange"]))
