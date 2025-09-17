import d2d_protocol
import json

resp = d2d_protocol.d2d_send_json(json.dumps({
    "AntennaAziOffset": 180
#    "AntennaAziOffsetStore": True #Persist changes
}))

print("Server replied with the following Antenna values")
print("AntennaAziOffset: " + str(resp.data["AntennaAziOffset"]))
