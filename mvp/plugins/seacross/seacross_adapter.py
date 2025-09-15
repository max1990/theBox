import socket
from datetime import datetime, timezone
from typing import Tuple

from mvp.schemas import CLSMessage, SGTMessage


def _checksum(payload: str) -> str:
    c = 0
    for ch in payload:
        c ^= ord(ch)
    return f"{c:02X}"


def _wrap(talker: str, typ: str, fields: list[str], extra: str | None = None) -> str:
    payload = f"{talker}{typ}," + ",".join(fields)
    if extra:
        payload += f",{extra}"
    return f"${payload}*{_checksum(payload)}"


def _fmt_now() -> Tuple[str, str]:
    dt = datetime.now(timezone.utc)
    return dt.strftime("%Y%m%d"), dt.strftime("%H%M%S") + f".{int(dt.microsecond/1e4):02d}"


class SeaCrossAdapter:
    def __init__(self, host: str, port: int, *, talker: str = "XA"):
        self.host = host
        self.port = port
        self.talker = talker
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send_cls(self, msg: CLSMessage):
        fields = [msg.object_id, msg.type, "", msg.brand_model, msg.affiliation]
        sentence = _wrap(self.talker, "CLS", fields, f"details_url={msg.details_url}")
        self._send(sentence)
        return sentence

    def send_sgt(self, msg: SGTMessage):
        fields = [
            msg.object_id,
            msg.yyyymmdd or _fmt_now()[0],
            msg.hhmmss or _fmt_now()[1],
            f"{msg.distance_m:.1f}",
            f"{msg.distance_err_m:.1f}",
            f"{msg.bearing_deg:.1f}",
            f"{msg.bearing_err_deg:.1f}",
            f"{msg.altitude_m:.1f}",
            f"{msg.altitude_err_m:.1f}",
        ]
        sentence = _wrap(self.talker, "SGT", fields)
        self._send(sentence)
        return sentence

    def _send(self, sentence: str):
        try:
            self.sock.sendto(sentence.encode("ascii", errors="ignore"), (self.host, self.port))
        except Exception:
            pass


