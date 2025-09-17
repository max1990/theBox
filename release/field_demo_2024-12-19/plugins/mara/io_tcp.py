"""
TCP client for receiving MARA data.
"""

import asyncio
from collections.abc import Callable

import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger(__name__)


class MARATCPClient:
    """TCP client for receiving MARA data."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 9000,
        message_handler: Callable[[str], None] | None = None,
        reconnect_delay: float = 1.0,
    ):
        self.host = host
        self.port = port
        self.message_handler = message_handler
        self.reconnect_delay = reconnect_delay
        self.logger = logger.bind(component="mara_tcp")
        self._reader = None
        self._writer = None
        self._running = False
        self._reconnect_task = None

    async def start(self):
        """Start the TCP client with auto-reconnect."""
        self._running = True
        self._reconnect_task = asyncio.create_task(self._reconnect_loop())
        self.logger.info("TCP client started", host=self.host, port=self.port)

    async def stop(self):
        """Stop the TCP client."""
        self._running = False
        if self._reconnect_task:
            self._reconnect_task.cancel()
            try:
                await self._reconnect_task
            except asyncio.CancelledError:
                pass

        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()

        self.logger.info("TCP client stopped")

    async def _reconnect_loop(self):
        """Main reconnection loop."""
        while self._running:
            try:
                await self._connect_and_read()
            except Exception as e:
                self.logger.error("TCP connection error", error=str(e))
                if self._running:
                    self.logger.info(
                        "Reconnecting in {delay}s", delay=self.reconnect_delay
                    )
                    await asyncio.sleep(self.reconnect_delay)

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    async def _connect_and_read(self):
        """Connect to TCP server and read data."""
        self.logger.info("Connecting to TCP server", host=self.host, port=self.port)

        self._reader, self._writer = await asyncio.open_connection(self.host, self.port)

        self.logger.info("TCP connection established")

        try:
            await self._read_loop()
        finally:
            if self._writer:
                self._writer.close()
                await self._writer.wait_closed()
                self._reader = None
                self._writer = None

    async def _read_loop(self):
        """Read data from TCP connection."""
        buffer = ""

        while self._running and self._reader:
            try:
                # Read with timeout
                data = await asyncio.wait_for(self._reader.read(4096), timeout=2.5)

                if not data:
                    self.logger.warning("TCP connection closed by server")
                    break

                # Decode and process lines
                buffer += data.decode("utf-8", errors="replace")

                # Process complete lines
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()

                    if line and self.message_handler:
                        self.logger.debug(
                            "Received TCP message",
                            length=len(line),
                            message_preview=line[:100],
                        )
                        self.message_handler(line)

            except asyncio.TimeoutError:
                # Send heartbeat or keep-alive if needed
                continue
            except Exception as e:
                self.logger.error("Error reading TCP data", error=str(e))
                break

    @property
    def is_connected(self) -> bool:
        """Check if TCP client is connected."""
        return self._writer is not None and not self._writer.is_closing()
