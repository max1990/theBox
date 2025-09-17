import json

import d2d_protocol

resp = d2d_protocol.d2d_send_json(
    json.dumps(
        {
            "AntennaOperation": "sector",
            "AntennaSecScan": [
                {"Start": -85, "Stop": 91, "TrueRelative": "relative", "Scans": 0}
            ],
            "AntennaRPM": 6,
        }
    )
)

print("Server replied with the following Antenna values")
print("AntennaOperation: " + resp.data["AntennaOperation"])
print("AntennaRPM: " + str(resp.data["AntennaRPM"]))
