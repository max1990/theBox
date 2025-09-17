import json

import d2d_protocol

resp = d2d_protocol.d2d_send_json(
    json.dumps(
        {
            "Quit": "off",
        }
    )
)
