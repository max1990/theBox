"""
Silvus live UDP client (text or protobuf placeholder).

Usage from SilvusListenerPlugin:
--------------------------------
from .live_udp_client import SilvusUDPClient, example_protobuf_decoder

self._udp = SilvusUDPClient(
    host=os.getenv("SILVUS_UDP_HOST", "0.0.0.0"),
    port=int(os.getenv("SILVUS_UDP_PORT", "50051")),
    mode=os.getenv("SILVUS_UDP_MODE", "text"),  # 'text' or 'protobuf'
    on_record=self._emit_bearing,               # callback(rec_dict)
    decoder=None                                # optional for 'protobuf' mode
)
self._udp.start()

To stop: self._udp.stop()

Record format expected by on_record(rec):
-----------------------------------------
{
  "time_utc": "<ISO8601 UTC>",
  "freq_mhz": <float>,
  "aoa1_deg": <float> | None,
  "aoa2_deg": <float> | None,
  "heading_deg": <float> | None
}
"""

import socket
import threading
import datetime
import re
from typing import Callable, Optional, Iterable, Dict

# Same patterns as the text log parser
HDR = re.compile(
    r"\[(?P<ip>\d+\.\d+\.\d+\.\d+)\]\s+Lat/Lon\s*:\s*\((?P<lat>[-\d\.]+)\s*,\s*(?P<lon>[-\d\.]+)\)\s*,\s*Heading\s*\(deg\)\s*:\s*(?P<hdg>[-\d\.]+)"
)
DAT = re.compile(
    r"\[(?P<ip>\d+\.\d+\.\d+\.\d+):(?P<ts>\d+)\]\s*(?P<power>[-\d\.]+)\s*,\s*(?P<fc>[-\d\.]+)\s*,\s*(?P<bw>[-\d\.]+)\s*,\s*\[(?P<aoa1>[-\d\.]+)\s*,\s*(?P<aoa2>[-\d\.]+)\]"
)

def us_to_iso(ts_us: int) -> str:
    return datetime.datetime.utcfromtimestamp(ts_us / 1_000_000).replace(
        tzinfo=datetime.timezone.utc
    ).isoformat()

class SilvusUDPClient:
    """
    UDP listener that parses Silvus lines in streaming mode (text) or
    hands bytes to a protobuf decoder (when provided).

    Parameters
    ----------
    host : str
        Bind address, e.g. "0.0.0.0"
    port : int
        UDP port to listen on
    mode : str
        "text" or "protobuf"
    on_record : Callable[[Dict], None]
        Callback invoked for each normalized record dict
    decoder : Optional[Callable[[bytes], Iterable[Dict]]]
        Optional decoder for "protobuf" mode. Must yield record dicts with keys:
        time_utc, freq_mhz, aoa1_deg, aoa2_deg, heading_deg
    recv_buf : int
        UDP receive buffer size in bytes
    """

    def __init__(
        self,
        host: str,
        port: int,
        mode: str,
        on_record: Callable[[Dict], None],
        decoder: Optional[Callable[[bytes], Iterable[Dict]]] = None,
        recv_buf: int = 65535,
    ):
        self.host = host
        self.port = port
        self.mode = mode.lower()
        self.on_record = on_record
        self.decoder = decoder
        self.recv_buf = recv_buf

        self._sock: Optional[socket.socket] = None
        self._thr: Optional[threading.Thread] = None
        self._stop = threading.Event()

        # streaming state (for text mode)
        self._last_heading: Optional[float] = None

    # ---------- lifecycle ----------
    def start(self):
        if self._thr and self._thr.is_alive():
            return
        self._stop.clear()
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.bind((self.host, self.port))
        self._sock.settimeout(1.0)
        self._thr = threading.Thread(target=self._run, name="SilvusUDPClient", daemon=True)
        self._thr.start()

    def stop(self):
        self._stop.set()
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None
        if self._thr:
            self._thr.join(timeout=2.0)
            self._thr = None

    # ---------- internals ----------
    def _run(self):
        if not self._sock:
            return
        while not self._stop.is_set():
            try:
                data, addr = self._sock.recvfrom(self.recv_buf)
            except socket.timeout:
                continue
            except OSError:
                break  # socket closed

            if not data:
                continue

            if self.mode == "text":
                self._handle_text_packet(data)
            elif self.mode == "protobuf":
                self._handle_protobuf_packet(data)
            else:
                continue

    def _handle_text_packet(self, data: bytes):
        """Handle UDP payloads that are plain-text lines identical to the Silvus sample logs."""
        try:
            text = data.decode("utf-8", errors="ignore")
        except Exception:
            return

        # Some transports may bundle multiple lines per datagram
        for raw in text.splitlines():
            line = raw.strip()
            if not line:
                continue

            m = HDR.search(line)
            if m:
                try:
                    self._last_heading = float(m.group("hdg"))
                except Exception:
                    pass  # keep previous heading if parse fails
                continue

            m = DAT.search(line)
            if m:
                try:
                    ts_us = int(m.group("ts"))
                    rec = {
                        "time_utc": us_to_iso(ts_us),
                        "freq_mhz": float(m.group("fc")),
                        "aoa1_deg": float(m.group("aoa1")),
                        "aoa2_deg": float(m.group("aoa2")),
                        "heading_deg": self._last_heading,  # may be None if no HDR yet
                    }
                    self.on_record(rec)
                except Exception:
                    continue  # ignore malformed lines, keep streaming

    def _handle_protobuf_packet(self, data: bytes):
        """Delegate to a caller-provided decoder that turns bytes → iterable of rec dicts."""
        if not self.decoder:
            return
        try:
            for rec in self.decoder(data):
                self.on_record(rec)
        except Exception:
            # swallow decode errors to keep listener alive
            pass

# ------- Example protobuf decoder stub (replace when Silvus provides .proto) -------
def example_protobuf_decoder(payload: bytes):
    """
    Placeholder: implement once Silvus provides the protobuf schema.
    Should yield dicts like:
        {
          "time_utc": "2025-09-12T19:36:05.123456+00:00",
          "freq_mhz": 2462.0,
          "aoa1_deg": 15.0,
          "aoa2_deg": 195.0,
          "heading_deg": 101.2
        }
    """
    raise NotImplementedError("Provide a decoder using Silvus protobuf definitions.")
