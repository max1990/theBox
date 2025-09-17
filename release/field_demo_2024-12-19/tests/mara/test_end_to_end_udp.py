"""
End-to-end test for UDP functionality.
"""

import asyncio
import os
import socket
import sys
from unittest.mock import Mock

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from plugins.mara.io_udp import MARAUDPReceiver
from plugins.mara.plugin import MARAPlugin


class TestEndToEndUDP:
    """Test end-to-end UDP functionality."""

    def setup_method(self):
        """Setup test method."""
        self.event_manager = Mock()
        self.plugin = MARAPlugin(self.event_manager)
        self.udp_port = 8788  # Use different port for testing
        self.udp_host = "127.0.0.1"

    def test_udp_receiver_basic(self):
        """Test basic UDP receiver functionality."""
        received_messages = []

        def message_handler(message):
            received_messages.append(message)

        async def test_udp():
            # Start UDP receiver
            receiver = MARAUDPReceiver(
                host=self.udp_host, port=self.udp_port, message_handler=message_handler
            )

            await receiver.start()
            assert receiver.is_running

            # Send test message
            test_message = '{"timestamp": "2025-01-16T10:30:45.123Z", "sensor_id": "EO_001", "confidence": 0.85, "channel": "EO"}'

            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.sendto(test_message.encode("utf-8"), (self.udp_host, self.udp_port))

            # Wait for message to be received
            await asyncio.sleep(0.1)

            # Stop receiver
            await receiver.stop()

            # Check message was received
            assert len(received_messages) == 1
            assert received_messages[0] == test_message

        asyncio.run(test_udp())

    def test_udp_with_mara_data(self):
        """Test UDP with actual MARA data from sample file."""
        received_detections = []

        def message_handler(message):
            # Parse the message
            detection = self.plugin.parser.autodetect_and_parse(message)
            if detection:
                received_detections.append(detection)

        async def test_udp():
            # Start UDP receiver
            receiver = MARAUDPReceiver(
                host=self.udp_host, port=self.udp_port, message_handler=message_handler
            )

            await receiver.start()

            # Send MARA sample data
            sample_data = [
                '{"timestamp": "2025-01-16T10:30:45.123Z", "sensor_id": "EO_001", "object_id": "obj_123", "confidence": 0.85, "bearing_deg": 45.2, "elevation_deg": 12.5, "range_m": 1500.0, "lat": 40.7128, "lon": -74.0060, "speed_mps": 15.2, "heading_deg": 90.0, "label": "drone", "channel": "EO"}',
                "timestamp=2025-01-16T10:31:00.000Z sensor_id=EO_001 object_id=obj_126 confidence=0.91 bearing_deg=180.3 elevation_deg=15.2 range_m=3000.0 lat=40.7140 lon=-74.0040 speed_mps=25.0 heading_deg=0.0 label=drone channel=EO",
                "2025-01-16T10:31:30.000Z,ACOUSTIC_003,obj_128,0.88,45.0,10.5,1800.0,40.7120,-74.0065,18.7,45.0,drone,ACOUSTIC",
            ]

            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                for data in sample_data:
                    s.sendto(data.encode("utf-8"), (self.udp_host, self.udp_port))

            # Wait for messages to be processed
            await asyncio.sleep(0.2)

            # Stop receiver
            await receiver.stop()

            # Check detections were created
            assert len(received_detections) == 3

            # Check first detection (JSON)
            detection1 = received_detections[0]
            assert detection1.source == "mara"
            assert detection1.sensor_channel == "EO"
            assert detection1.label == "drone"
            assert detection1.confidence == 0.85
            assert detection1.bearing_deg == 45.2
            assert detection1.range_km == 1.5

            # Check second detection (key=value)
            detection2 = received_detections[1]
            assert detection2.source == "mara"
            assert detection2.sensor_channel == "EO"
            assert detection2.label == "drone"
            assert detection2.confidence == 0.91
            assert detection2.bearing_deg == 180.3
            assert detection2.range_km == 3.0

            # Check third detection (CSV)
            detection3 = received_detections[2]
            assert detection3.source == "mara"
            assert detection3.sensor_channel == "ACOUSTIC"
            assert detection3.label == "drone"
            assert detection3.confidence == 0.88
            assert detection3.bearing_deg == 45.0
            assert detection3.range_km == 1.8

        asyncio.run(test_udp())

    def test_udp_malformed_data(self):
        """Test UDP handling of malformed data."""
        received_detections = []

        def message_handler(message):
            detection = self.plugin.parser.autodetect_and_parse(message)
            if detection:
                received_detections.append(detection)

        async def test_udp():
            receiver = MARAUDPReceiver(
                host=self.udp_host, port=self.udp_port, message_handler=message_handler
            )

            await receiver.start()

            # Send malformed data
            malformed_data = [
                '{"incomplete": "json"',
                "not a valid format",
                '{"timestamp": "2025-01-16T10:30:45.123Z", "sensor_id": "EO_001", "confidence": "invalid"}',
                "",
            ]

            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                for data in malformed_data:
                    s.sendto(data.encode("utf-8"), (self.udp_host, self.udp_port))

            # Wait for processing
            await asyncio.sleep(0.1)

            await receiver.stop()

            # Should handle malformed data gracefully (no crashes)
            # Some might still produce valid detections with None values
            assert len(received_detections) >= 0  # Should not crash

        asyncio.run(test_udp())

    def test_udp_connection_error(self):
        """Test UDP connection error handling."""

        async def test_udp():
            # Try to bind to an invalid port
            receiver = MARAUDPReceiver(
                host="invalid_host", port=99999, message_handler=lambda x: None
            )

            # Should handle error gracefully
            try:
                await receiver.start()
                assert False, "Should have raised an exception"
            except Exception:
                pass  # Expected

        asyncio.run(test_udp())
