import d2d_protocol
import json

resp = d2d_protocol.d2d_send_json(json.dumps({
    "AntennaOperation": "ccw",
    "AntennaRPM": 4
}))

print("Server replied with the following Antenna values")
print("AntennaOperation: " + resp.data["AntennaOperation"])
print("AntennaRPM: " + str(resp.data["AntennaRPM"]))

