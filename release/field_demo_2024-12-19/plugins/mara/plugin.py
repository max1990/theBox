"""
MARA Plugin - Main entry point for TheBox integration.
"""

import asyncio
import os
import threading
from datetime import datetime, timezone

import structlog

from thebox.plugin_interface import PluginInterface

from .io_serial import SERIAL_AVAILABLE, MARASerialReader
from .io_tcp import MARATCPClient
from .io_udp import MARAUDPReceiver
from .models import NormalizedDetection
from .parser import MARAParser
from .publisher import MARAPublisher

logger = structlog.get_logger(__name__)


class MARAPlugin(PluginInterface):
    """MARA Plugin for TheBox - UDP/Serial parser to normalized detections."""

    def __init__(self, event_manager):
        super().__init__(event_manager)
        self.logger = logger.bind(component="mara_plugin")

        # Configuration from environment
        self.enabled = os.getenv("MARA_ENABLE", "true").lower() == "true"
        self.input_mode = os.getenv("MARA_INPUT_MODE", "udp").lower()

        # UDP configuration
        self.udp_host = os.getenv("MARA_UDP_HOST", "0.0.0.0")
        self.udp_port = int(os.getenv("MARA_UDP_PORT", "8787"))

        # TCP configuration
        self.tcp_host = os.getenv("MARA_TCP_HOST", "127.0.0.1")
        self.tcp_port = int(os.getenv("MARA_TCP_PORT", "9000"))

        # Serial configuration
        self.serial_port = os.getenv("MARA_SERIAL_PORT", "COM5")
        self.serial_baud = int(os.getenv("MARA_BAUD", "115200"))

        # Output configuration
        self.rebroadcast_enable = (
            os.getenv("OUT_REBROADCAST_ENABLE", "false").lower() == "true"
        )
        self.out_udp_host = os.getenv("OUT_UDP_HOST", "127.0.0.1")
        self.out_udp_port = int(os.getenv("OUT_UDP_PORT", "7878"))

        # Runtime configuration
        self.heartbeat_interval = int(os.getenv("MARA_HEARTBEAT_SEC", "10"))
        self.max_queue_size = int(os.getenv("MARA_MAX_QUEUE", "10000"))

        # Components
        self.parser = MARAParser()
        self.publisher = MARAPublisher(
            enable_udp=self.rebroadcast_enable,
            udp_host=self.out_udp_host,
            udp_port=self.out_udp_port,
        )

        # IO components
        self.udp_receiver = None
        self.tcp_client = None
        self.serial_reader = None

        # Async tasks
        self._message_queue = asyncio.Queue(maxsize=self.max_queue_size)
        self._heartbeat_task = None
        self._processor_task = None
        self._running = False

    def load(self):
        """Load the MARA plugin."""
        if not self.enabled:
            self.logger.info("MARA plugin disabled via environment")
            return

        self.logger.info(
            "Loading MARA plugin",
            input_mode=self.input_mode,
            udp_config=f"{self.udp_host}:{self.udp_port}",
            tcp_config=f"{self.tcp_host}:{self.tcp_port}",
            serial_config=f"{self.serial_port}@{self.serial_baud}",
        )

        # Start async tasks in a separate thread
        threading.Thread(target=self._run_async_load, daemon=True).start()

    def unload(self):
        """Unload the MARA plugin."""
        self.logger.info("Unloading MARA plugin")
        threading.Thread(target=self._run_async_unload, daemon=True).start()

    def _run_async_load(self):
        """Run async load in a separate thread."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._async_load())
        finally:
            loop.close()

    def _run_async_unload(self):
        """Run async unload in a separate thread."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._async_unload())
        finally:
            loop.close()

    async def _async_load(self):
        """Async load process."""
        try:
            self._running = True

            # Start message processor
            self._processor_task = asyncio.create_task(self._process_messages())

            # Start heartbeat task
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

            # Start appropriate IO based on mode
            if self.input_mode == "udp":
                await self._start_udp()
            elif self.input_mode == "tcp":
                await self._start_tcp()
            elif self.input_mode == "serial":
                await self._start_serial()
            else:
                self.logger.error("Invalid input mode", mode=self.input_mode)
                return

            self.logger.info("MARA plugin loaded successfully")

        except Exception as e:
            self.logger.error("Failed to load MARA plugin", error=str(e))

    async def _async_unload(self):
        """Async unload process."""
        try:
            self._running = False

            # Cancel tasks
            if self._processor_task:
                self._processor_task.cancel()
            if self._heartbeat_task:
                self._heartbeat_task.cancel()

            # Stop IO components
            if self.udp_receiver:
                await self.udp_receiver.stop()
            if self.tcp_client:
                await self.tcp_client.stop()
            if self.serial_reader:
                await self.serial_reader.stop()

            # Close publisher
            self.publisher.close()

            self.logger.info("MARA plugin unloaded successfully")

        except Exception as e:
            self.logger.error("Error unloading MARA plugin", error=str(e))

    async def _start_udp(self):
        """Start UDP receiver."""
        self.udp_receiver = MARAUDPReceiver(
            host=self.udp_host, port=self.udp_port, message_handler=self._handle_message
        )
        await self.udp_receiver.start()

    async def _start_tcp(self):
        """Start TCP client."""
        self.tcp_client = MARATCPClient(
            host=self.tcp_host, port=self.tcp_port, message_handler=self._handle_message
        )
        await self.tcp_client.start()

    async def _start_serial(self):
        """Start serial reader."""
        if not SERIAL_AVAILABLE:
            self.logger.error(
                "Serial communication not available - install pyserial-asyncio"
            )
            return

        self.serial_reader = MARASerialReader(
            port=self.serial_port,
            baudrate=self.serial_baud,
            message_handler=self._handle_message,
        )
        await self.serial_reader.start()

    def _handle_message(self, message: str):
        """Handle incoming message from IO component."""
        try:
            # Add to queue for processing
            if not self._message_queue.full():
                self._message_queue.put_nowait(message)
            else:
                self.logger.warning("Message queue full, dropping message")
        except Exception as e:
            self.logger.error("Error handling message", error=str(e))

    async def _process_messages(self):
        """Process messages from queue."""
        while self._running:
            try:
                # Get message from queue with timeout
                message = await asyncio.wait_for(self._message_queue.get(), timeout=1.0)

                # Parse message
                detection = self.parser.autodetect_and_parse(message)

                if detection:
                    # Publish normalized detection
                    await self.publisher.publish(detection)

                    # Publish to TheBox event system
                    self.publish(
                        "mara_detection",
                        {"detection": detection.dict()},
                        store_in_db=True,
                    )
                else:
                    self.logger.debug("Failed to parse message", message=message[:100])

            except asyncio.TimeoutError:
                # Continue on timeout
                continue
            except Exception as e:
                self.logger.error("Error processing message", error=str(e))

    async def _heartbeat_loop(self):
        """Send periodic heartbeat events."""
        while self._running:
            try:
                await asyncio.sleep(self.heartbeat_interval)

                # Create heartbeat detection
                heartbeat = NormalizedDetection(
                    sensor_channel="UNKNOWN",
                    event_type="HEARTBEAT",
                    timestamp_utc=datetime.now(timezone.utc),
                    raw={
                        "heartbeat": True,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )

                # Publish heartbeat
                await self.publisher.publish(heartbeat)

                self.logger.debug("Sent heartbeat")

            except Exception as e:
                self.logger.error("Error sending heartbeat", error=str(e))

    def get_blueprint(self):
        """Get Flask blueprint for web interface."""
        from flask import Blueprint, jsonify, render_template

        bp = Blueprint(self.name, __name__, template_folder="templates")

        @bp.route("/")
        def index():
            return render_template("mara_plugin.html")

        @bp.route("/status")
        def status():
            return jsonify(
                {
                    "enabled": self.enabled,
                    "input_mode": self.input_mode,
                    "running": self._running,
                    "udp_config": f"{self.udp_host}:{self.udp_port}",
                    "tcp_config": f"{self.tcp_host}:{self.tcp_port}",
                    "serial_config": f"{self.serial_port}@{self.serial_baud}",
                    "rebroadcast_enabled": self.rebroadcast_enable,
                    "queue_size": self._message_queue.qsize(),
                    "udp_connected": (
                        self.udp_receiver.is_running if self.udp_receiver else False
                    ),
                    "tcp_connected": (
                        self.tcp_client.is_connected if self.tcp_client else False
                    ),
                    "serial_connected": (
                        self.serial_reader.is_connected if self.serial_reader else False
                    ),
                }
            )

        return bp
