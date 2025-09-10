"""
Utilities for constructing and sending IEC 61162-450 + NMEA sentences for drone data.

Provides `NMEASender` which can be reused by other modules to send SGT (sighting)
and CLS (classification) messages. It can either manage its own UDP socket or use
an externally managed one (e.g., from a listener) to avoid duplication.
"""

from datetime import datetime
from typing import Dict, Optional
from uuid import UUID
import socket


class NMEASender:
    def __init__(
        self,
        target_ip: str = "192.168.0.255",
        target_port: int = 62000,
        talker_id: str = "DD",
        *,
        debug: bool = False,
        sock: Optional[socket.socket] = None,
        manage_socket: bool = True,
    ) -> None:
        self.target_ip = target_ip
        self.target_port = target_port
        self.talker = talker_id.upper()[:2]
        if len(self.talker) != 2 or not self.talker.isalpha():
            raise ValueError("talker_id must be exactly two uppercase letters (A-Z).")
        self.sfi = f"{self.talker}0001"
        self.debug = debug
        self._manage_socket = sock is None and manage_socket
        self.counter = 1

        # Use provided socket or create our own sending socket
        if sock is not None:
            self.sock = sock
        else:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if hasattr(socket, "SO_REUSEPORT"):
                self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    def close(self) -> None:
        if getattr(self, "sock", None) and self._manage_socket:
            try:
                self.sock.close()
            except Exception:
                pass

    # -------- Formatting helpers --------
    @staticmethod
    def calculate_checksum(sentence: str) -> str:
        checksum = 0
        for ch in sentence:
            checksum ^= ord(ch)
        return f"{checksum:02X}"

    @staticmethod
    def format_uuid(uuid: UUID) -> str:
        return uuid.hex

    @staticmethod
    def format_date(dt: datetime) -> str:
        return dt.strftime("%Y%m%d")

    @staticmethod
    def format_time(dt: datetime) -> str:
        return dt.strftime("%H%M%S.%f")[:-4]

    # -------- Internal send helpers --------
    def _ensure_sentence_checksum(self, sentence: str) -> str:
        if "*" in sentence:
            return sentence
        payload = sentence[1:] if sentence.startswith("$") else sentence
        checksum = self.calculate_checksum(payload)
        return f"{sentence}*{checksum}"

    def _build_tag_block(self, sfi: str, counter: int) -> str:
        tag_content = f"s:{sfi},n:{counter}"
        tag_checksum = self.calculate_checksum(tag_content)
        return f"\\{tag_content}*{tag_checksum}\\"

    def send_sentence(self, sentence: str) -> None:
        # Build IEC 61162-450 wrapped message
        message = "UdPbC\0"
        message += self._build_tag_block(self.sfi, self.counter)
        sentence = self._ensure_sentence_checksum(sentence)
        message += sentence + "\r\n"

        if self.debug:
            print(f"[DEBUG] Sending NMEA message: {message.strip()}")
        self.sock.sendto(message.encode("ascii"), (self.target_ip, self.target_port))
        self.counter += 1

    def set_counter(self, value: int) -> None:
        self.counter = int(value)

    # -------- Public API: SGT and CLS --------
    def send_sighting(
        self,
        *,
        drone_uuid: UUID,
        timestamp: datetime,
        distance_m: float,
        distance_precision_m: float,
        direction_deg: float,
        direction_precision_deg: float,
        altitude_m: float,
        altitude_precision_m: float,
    ) -> None:
        nmea = (
            f"${self.talker}SGT,{self.format_uuid(drone_uuid)},"  # talker + type + uuid
            f"{self.format_date(timestamp)},{self.format_time(timestamp)},"
            f"{distance_m:.1f},{distance_precision_m:.1f},"
            f"{direction_deg:.1f},{direction_precision_deg:.1f},"
            f"{altitude_m:.1f},{altitude_precision_m:.1f}"
        )
        self.send_sentence(nmea)

    def send_sighting_coords(
        self,
        *,
        drone_uuid: UUID,
        timestamp: datetime,
        latitude_deg: float,
        longitude_deg: float,
        coord_precision_m: float,
        altitude_m: float,
        altitude_precision_m: float,
    ) -> None:
        """Send SGC (sighting by coordinates) message.

        Format: $<TALKER>SGC,<UUID>,<Date>,<Time>,<Lat>,<Lon>,<CoordPrec>,<Alt>,<AltPrec>*CS
        """
        nmea = (
            f"${self.talker}SGC,{self.format_uuid(drone_uuid)},"
            f"{self.format_date(timestamp)},{self.format_time(timestamp)},"
            f"{latitude_deg:.6f},{longitude_deg:.6f},{coord_precision_m:.1f},"
            f"{altitude_m:.1f},{altitude_precision_m:.1f}"
        )
        self.send_sentence(nmea)

    def send_classification(
        self,
        *,
        drone_uuid: UUID,
        domain: str,
        type_: Optional[str],
        model: Optional[str],
        affiliation: str,
        additional_info: Optional[Dict[str, str]] = None,
    ) -> None:
        info_str = "" if not additional_info else ";".join(f"{k}={v}" for k, v in additional_info.items())
        nmea = (
            f"${self.talker}CLS,{self.format_uuid(drone_uuid)},"
            f"{domain or ''},{type_ or ''},{model or ''},{affiliation or ''},{info_str}"
        )
        self.send_sentence(nmea)
