"""
Discovery and info communication for Dspnor plugin
"""

import json
import socket
import struct
import threading
import time
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

import structlog

from .constants import (
    D2D_PROTOCOL,
    D2D_TYPE_TEXT,
    D2D_VERSION,
    DEFAULT_DISCOVERY_MULTICAST,
    DEFAULT_DISCOVERY_PORT,
    DEFAULT_INFO_TCP_PORT,
    DISCOVERY_BEACON_SIZE,
)
from .schemas import D2DHeader, DiscoveryBeacon, UnitInfo

logger = structlog.get_logger(__name__)


class D2DProtocol:
    """D2D protocol handler"""

    @staticmethod
    def build_header(json_data: str) -> str:
        """Build D2D header for JSON data"""
        return (
            f"{D2D_PROTOCOL}={D2D_PROTOCOL}\n"
            f"VERSION={D2D_VERSION}\n"
            f"TYPE={D2D_TYPE_TEXT}\n"
            f"LENGTH={len(json_data.encode('utf-8'))}\n\n"
        )

    @staticmethod
    def parse_response(response: str) -> tuple[D2DHeader, dict[str, Any]]:
        """Parse D2D response into header and JSON data"""
        lines = response.splitlines()
        header = {}
        json_start = 0

        for i, line in enumerate(lines):
            if line.strip() == "":
                json_start = i + 1
                break
            if "=" in line:
                key, value = line.split("=", 1)
                header[key.strip()] = value.strip()

        json_data = "\n".join(lines[json_start:])
        d2d_header = D2DHeader(
            protocol=header.get("PROTOCOL", ""),
            version=header.get("VERSION", ""),
            type=header.get("TYPE", ""),
            length=int(header.get("LENGTH", "0")),
        )

        try:
            data = json.loads(json_data) if json_data.strip() else {}
        except json.JSONDecodeError:
            data = {}

        return d2d_header, data


class DiscoveryClient:
    """Multicast discovery client"""

    def __init__(
        self,
        multicast_group: str = DEFAULT_DISCOVERY_MULTICAST,
        port: int = DEFAULT_DISCOVERY_PORT,
    ):
        self.multicast_group = multicast_group
        self.port = port
        self.socket = None
        self.running = False
        self.discovered_units: dict[str, UnitInfo] = {}
        self.callback: Callable[[UnitInfo], None] | None = None
        self._thread: threading.Thread | None = None
        self.logger = logger.bind(component="discovery")

    def set_callback(self, callback: Callable[[UnitInfo], None]):
        """Set callback for discovered units"""
        self.callback = callback

    def start(self):
        """Start discovery listening"""
        if self.running:
            return

        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind(("", self.port))

            # Join multicast group
            mreq = struct.pack(
                "4sl", socket.inet_aton(self.multicast_group), socket.INADDR_ANY
            )
            self.socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

            self.running = True
            self._thread = threading.Thread(target=self._listen_loop, daemon=True)
            self._thread.start()

            self.logger.info(
                "Discovery client started",
                multicast_group=self.multicast_group,
                port=self.port,
            )

        except Exception as e:
            self.logger.error("Failed to start discovery client", error=str(e))
            self.stop()

    def stop(self):
        """Stop discovery listening"""
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

        self.logger.info("Discovery client stopped")

    def _listen_loop(self):
        """Main discovery listening loop"""
        while self.running:
            try:
                data, addr = self.socket.recvfrom(DISCOVERY_BEACON_SIZE)
                if len(data) == DISCOVERY_BEACON_SIZE:
                    beacon = self._parse_beacon(data, addr[0])
                    if beacon:
                        unit_info = UnitInfo(
                            ip_address=beacon.ip_address,
                            port=beacon.port,
                            unit_name=beacon.unit_name,
                            serial_number=beacon.serial_number,
                            firmware_version=beacon.firmware_version,
                            capabilities=beacon.capabilities,
                            last_seen=datetime.now(),
                        )

                        # Update or add unit
                        self.discovered_units[beacon.serial_number] = unit_info

                        if self.callback:
                            self.callback(unit_info)

            except TimeoutError:
                continue
            except Exception as e:
                if self.running:
                    self.logger.error("Error in discovery loop", error=str(e))

    def _parse_beacon(self, data: bytes, ip: str) -> DiscoveryBeacon | None:
        """Parse discovery beacon data"""
        try:
            # Parse 40-byte beacon structure
            # Format: [4 bytes IP][2 bytes port][32 bytes unit info][2 bytes capabilities]
            ip_bytes = data[0:4]
            port = struct.unpack(">H", data[4:6])[0]
            unit_info = data[6:38].decode("utf-8", errors="ignore").strip("\x00")
            capabilities_raw = struct.unpack(">H", data[38:40])[0]

            # Parse unit info (name, serial, firmware)
            parts = unit_info.split("|")
            unit_name = parts[0] if len(parts) > 0 else "Unknown"
            serial_number = parts[1] if len(parts) > 1 else "Unknown"
            firmware_version = parts[2] if len(parts) > 2 else "Unknown"

            # Parse capabilities from bit flags
            capabilities = []
            if capabilities_raw & 0x01:
                capabilities.append("CAT010")
            if capabilities_raw & 0x02:
                capabilities.append("CAT240")
            if capabilities_raw & 0x04:
                capabilities.append("NMEA")
            if capabilities_raw & 0x08:
                capabilities.append("ExternalINS")

            return DiscoveryBeacon(
                ip_address=ip,
                port=port,
                unit_name=unit_name,
                serial_number=serial_number,
                firmware_version=firmware_version,
                capabilities=capabilities,
            )

        except Exception as e:
            self.logger.error("Failed to parse discovery beacon", error=str(e))
            return None

    def get_discovered_units(self) -> dict[str, UnitInfo]:
        """Get all discovered units"""
        # Remove stale units (older than 30 seconds)
        now = datetime.now()
        stale_units = [
            serial
            for serial, unit in self.discovered_units.items()
            if now - unit.last_seen > timedelta(seconds=30)
        ]
        for serial in stale_units:
            del self.discovered_units[serial]

        return self.discovered_units.copy()


class InfoClient:
    """TCP info client with rate limiting"""

    def __init__(self, host: str, port: int = DEFAULT_INFO_TCP_PORT):
        self.host = host
        self.port = port
        self.socket = None
        self.last_request_time = 0
        self.min_interval = 1.0  # 1 Hz rate limit
        self.logger = logger.bind(component="info_client")

    def connect(self) -> bool:
        """Connect to info port"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5.0)
            self.socket.connect((self.host, self.port))
            self.logger.info("Connected to info port", host=self.host, port=self.port)
            return True
        except Exception as e:
            self.logger.error(
                "Failed to connect to info port",
                host=self.host,
                port=self.port,
                error=str(e),
            )
            return False

    def disconnect(self):
        """Disconnect from info port"""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None

    def send_command(self, command: dict[str, Any]) -> dict[str, Any] | None:
        """Send D2D command with rate limiting"""
        # Check rate limit
        now = time.time()
        if now - self.last_request_time < self.min_interval:
            time.sleep(self.min_interval - (now - self.last_request_time))

        if not self.socket:
            if not self.connect():
                return None

        try:
            # Build D2D message
            json_data = json.dumps(command)
            header = D2DProtocol.build_header(json_data)
            message = header + json_data

            # Send command
            self.socket.sendall(message.encode("utf-8"))

            # Receive response
            response = self.socket.recv(8192).decode("utf-8")
            if not response:
                self.logger.warning("Empty response from unit")
                return None

            # Parse response
            _, data = D2DProtocol.parse_response(response)
            self.last_request_time = time.time()

            return data

        except Exception as e:
            self.logger.error("Failed to send command", command=command, error=str(e))
            self.disconnect()
            return None

    def get_status(self) -> dict[str, Any] | None:
        """Get unit status"""
        return self.send_command({"GetStatus": True})

    def get_services(self) -> dict[str, Any] | None:
        """Get service configuration"""
        return self.send_command({"GetServices": True})
