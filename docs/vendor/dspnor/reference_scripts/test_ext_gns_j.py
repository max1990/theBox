import d2d_protocol
import json
import time


while True:
    resp = d2d_protocol.d2d_send_json(json.dumps({
        "INS": {
            "TrueBearing": 120.0,
            "Lat": 60.5,
            "Lon": 5.1,
            "COG": 111,
            "SOG": 15
        }
    }))
    time.sleep(0.05) # 500ms
