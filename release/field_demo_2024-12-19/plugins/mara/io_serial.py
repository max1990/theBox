"""
Serial communication for receiving MARA data.
"""

import asyncio
from collections.abc import Callable

import structlog

try:
    import serial_asyncio

    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False
    serial_asyncio = None

logger = structlog.get_logger(__name__)


class MARASerialReader:
    """Serial reader for MARA data."""

    def __init__(
        self,
        port: str = "COM5",
        baudrate: int = 115200,
        message_handler: Callable[[str], None] | None = None,
        read_timeout: float = 2.5,
    ):
        if not SERIAL_AVAILABLE:
            raise ImportError("pyserial-asyncio is required for serial communication")

        self.port = port
        self.baudrate = baudrate
        self.message_handler = message_handler
        self.read_timeout = read_timeout
        self.logger = logger.bind(component="mara_serial")
        self._reader = None
        self._writer = None
        self._running = False
        self._read_task = None

    async def start(self):
        """Start the serial reader."""
        try:
            self._reader, self._writer = await serial_asyncio.open_serial_connection(
                url=self.port, baudrate=self.baudrate, timeout=self.read_timeout
            )
            self._running = True
            self._read_task = asyncio.create_task(self._read_loop())
            self.logger.info(
                "Serial reader started", port=self.port, baudrate=self.baudrate
            )
        except Exception as e:
            self.logger.error("Failed to start serial reader", error=str(e))
            raise

    async def stop(self):
        """Stop the serial reader."""
        self._running = False

        if self._read_task:
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass

        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()

        self.logger.info("Serial reader stopped")

    async def _read_loop(self):
        """Main read loop for serial data."""
        buffer = ""

        while self._running and self._reader:
            try:
                # Read data with timeout
                data = await asyncio.wait_for(
                    self._reader.read(1024), timeout=self.read_timeout
                )

                if not data:
                    self.logger.warning("Serial connection closed")
                    break

                # Decode data
                text = data.decode("utf-8", errors="replace")
                buffer += text

                # Process complete lines
                while "\n" in buffer or "\r" in buffer:
                    # Handle both \n and \r\n line endings
                    if "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                    else:
                        line, buffer = buffer.split("\r", 1)

                    line = line.strip()

                    if line and self.message_handler:
                        self.logger.debug(
                            "Received serial message",
                            length=len(line),
                            message_preview=line[:100],
                        )
                        self.message_handler(line)

            except asyncio.TimeoutError:
                # Continue reading on timeout
                continue
            except Exception as e:
                self.logger.error("Error reading serial data", error=str(e))
                break

    @property
    def is_connected(self) -> bool:
        """Check if serial reader is connected."""
        return self._writer is not None and not self._writer.is_closing()
