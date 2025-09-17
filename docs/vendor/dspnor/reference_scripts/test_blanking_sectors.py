import d2d_protocol
import json

resp = d2d_protocol.d2d_send_json(json.dumps({
    "AntennaSB1": {
        "Active": True,
        "Start": 260,
        "Stops": 290,
        "TrueRelative": "relative"
    }
}))

print("Server replied with the following Antenna values")
print(json.dumps(resp.data));

# resp = d2d_protocol.d2d_send_json(json.dumps({
#     "AntennaSB2": {
#         "Active": True,
#         "Start": 30,
#         "Stop": 40,
#         "TrueRelative": "relative"
#     }
# }))

# print("Server replied with the following Antenna values")
# print(json.dumps(resp.data));

# resp = d2d_protocol.d2d_send_json(json.dumps({
#     "AntennaSB3": {
#         "Active": True,
#         "Start": 50,
#         "Stop": 60,
#         "TrueRelative": "relative"
#     }
# }))

# print("Server replied with the following Antenna values")
# print(json.dumps(resp.data));
