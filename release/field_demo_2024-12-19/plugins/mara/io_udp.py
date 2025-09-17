"""
UDP server for receiving MARA data.
"""

import asyncio
import socket
from collections.abc import Callable

import structlog

logger = structlog.get_logger(__name__)


class MARAUDPReceiver:
    """UDP server for receiving MARA data."""

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8787,
        message_handler: Callable[[str], None] | None = None,
    ):
        self.host = host
        self.port = port
        self.message_handler = message_handler
        self.logger = logger.bind(component="mara_udp")
        self._transport = None
        self._protocol = None
        self._running = False

    async def start(self):
        """Start the UDP server."""
        try:
            # Create UDP socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((self.host, self.port))
            sock.setblocking(False)

            # Create protocol
            self._protocol = MARAUDPProtocol(self.message_handler, self.logger)
            (
                self._transport,
                self._protocol,
            ) = await asyncio.get_event_loop().create_datagram_endpoint(
                lambda: self._protocol, sock=sock
            )

            self._running = True
            self.logger.info("UDP server started", host=self.host, port=self.port)
        except Exception as e:
            self.logger.error("Failed to start UDP server", error=str(e))
            raise

    async def stop(self):
        """Stop the UDP server."""
        if self._transport:
            self._transport.close()
            self._running = False
            self.logger.info("UDP server stopped")

    @property
    def is_running(self) -> bool:
        """Check if server is running."""
        return self._running


class MARAUDPProtocol(asyncio.DatagramProtocol):
    """UDP protocol handler for MARA data."""

    def __init__(self, message_handler: Callable[[str], None] | None, logger):
        self.message_handler = message_handler
        self.logger = logger

    def datagram_received(self, data: bytes, addr):
        """Handle received UDP datagram."""
        try:
            # Decode with error handling
            message = data.decode("utf-8", errors="replace")
            self.logger.debug(
                "Received UDP message",
                addr=addr,
                length=len(data),
                message_preview=message[:100],
            )

            if self.message_handler:
                self.message_handler(message)
        except Exception as e:
            self.logger.error(
                "Error processing UDP message",
                error=str(e),
                addr=addr,
                data_length=len(data),
            )

    def error_received(self, exc):
        """Handle UDP errors."""
        self.logger.error("UDP error received", error=str(exc))

    def connection_lost(self, exc):
        """Handle connection loss."""
        if exc:
            self.logger.warning("UDP connection lost", error=str(exc))
        else:
            self.logger.info("UDP connection closed")
