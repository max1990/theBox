import d2d_protocol
import json

print("Attempting to wait for status message")
resp = d2d_protocol.d2d_wait_for_status_message()

print(f"Server returned: {json.dumps(resp.data)}");