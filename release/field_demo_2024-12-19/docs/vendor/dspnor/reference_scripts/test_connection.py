import json

import d2d_protocol

resp = d2d_protocol.d2d_send_json(json.dumps({}))

print(f"Protocol: {resp.header['PROTOCOL']}")
print(f"Version: {resp.header['VERSION']}")
print(f"Type: {resp.header['TYPE']}")
print(f"Length: {resp.header['LENGTH']}")
print(f"Response {resp.data}")
