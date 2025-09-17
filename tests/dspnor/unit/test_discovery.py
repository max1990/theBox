"""
Unit tests for discovery functionality
"""

import unittest
import socket
import struct
import threading
import time
from unittest.mock import Mock, patch

from plugins.dspnor.io_discovery import DiscoveryClient, InfoClient, D2DProtocol
from plugins.dspnor.schemas import DiscoveryBeacon, UnitInfo


class TestD2DProtocol(unittest.TestCase):
    """Test D2D protocol handling"""
    
    def test_build_header(self):
        """Test D2D header building"""
        json_data = '{"test": "data"}'
        header = D2DProtocol.build_header(json_data)
        
        self.assertIn("PROTOCOL=D2D", header)
        self.assertIn("VERSION=1.0", header)
        self.assertIn("TYPE=TEXT", header)
        self.assertIn("LENGTH=16", header)  # len(json_data)
        self.assertIn("\n\n", header)
    
    def test_parse_response(self):
        """Test D2D response parsing"""
        response = "PROTOCOL=D2D\nVERSION=1.0\nTYPE=TEXT\nLENGTH=16\n\n{\"test\": \"data\"}"
        
        header, data = D2DProtocol.parse_response(response)
        
        self.assertEqual(header.protocol, "D2D")
        self.assertEqual(header.version, "1.0")
        self.assertEqual(header.type, "TEXT")
        self.assertEqual(header.length, 16)
        self.assertEqual(data, {"test": "data"})
    
    def test_parse_response_empty_json(self):
        """Test parsing response with empty JSON"""
        response = "PROTOCOL=D2D\nVERSION=1.0\nTYPE=TEXT\nLENGTH=0\n\n"
        
        header, data = D2DProtocol.parse_response(response)
        
        self.assertEqual(header.protocol, "D2D")
        self.assertEqual(data, {})


class TestDiscoveryClient(unittest.TestCase):
    """Test discovery client"""
    
    def setUp(self):
        self.client = DiscoveryClient("224.0.0.1", 12345)
        self.callback_called = False
        self.received_unit = None
    
    def test_callback_setting(self):
        """Test callback setting"""
        callback = Mock()
        self.client.set_callback(callback)
        self.assertEqual(self.client.callback, callback)
    
    def test_parse_beacon_valid(self):
        """Test parsing valid beacon"""
        # Create mock beacon data
        ip_bytes = socket.inet_aton("192.168.1.100")
        port = 12345
        unit_info = "TestUnit|SN123456|v1.0.0".ljust(32, '\x00')
        capabilities = 0x0F  # All capabilities
        
        data = ip_bytes + struct.pack('>H', port) + unit_info.encode() + struct.pack('>H', capabilities)
        
        beacon = self.client._parse_beacon(data, "192.168.1.100")
        
        self.assertIsNotNone(beacon)
        self.assertEqual(beacon.ip_address, "192.168.1.100")
        self.assertEqual(beacon.port, 12345)
        self.assertEqual(beacon.unit_name, "TestUnit")
        self.assertEqual(beacon.serial_number, "SN123456")
        self.assertEqual(beacon.firmware_version, "v1.0.0")
        self.assertIn("CAT010", beacon.capabilities)
        self.assertIn("CAT240", beacon.capabilities)
        self.assertIn("NMEA", beacon.capabilities)
        self.assertIn("ExternalINS", beacon.capabilities)
    
    def test_parse_beacon_invalid_size(self):
        """Test parsing beacon with invalid size"""
        data = b"invalid data"
        beacon = self.client._parse_beacon(data, "192.168.1.100")
        self.assertIsNone(beacon)
    
    def test_parse_beacon_malformed(self):
        """Test parsing malformed beacon"""
        # Create beacon with invalid data
        ip_bytes = socket.inet_aton("192.168.1.100")
        port = 12345
        unit_info = "TestUnit\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        capabilities = 0x0F
        
        data = ip_bytes + struct.pack('>H', port) + unit_info.encode() + struct.pack('>H', capabilities)
        
        beacon = self.client._parse_beacon(data, "192.168.1.100")
        
        # Should still parse but with default values
        self.assertIsNotNone(beacon)
        self.assertEqual(beacon.unit_name, "TestUnit")
    
    def test_get_discovered_units_stale_removal(self):
        """Test that stale units are removed"""
        # Add a unit
        unit = UnitInfo(
            ip_address="192.168.1.100",
            port=12345,
            unit_name="TestUnit",
            serial_number="SN123456",
            firmware_version="v1.0.0",
            capabilities=["CAT010"]
        )
        self.client.discovered_units["SN123456"] = unit
        
        # Make it stale
        unit.last_seen = unit.last_seen.replace(year=2020)
        self.client.discovered_units["SN123456"] = unit
        
        units = self.client.get_discovered_units()
        self.assertEqual(len(units), 0)


class TestInfoClient(unittest.TestCase):
    """Test info client"""
    
    def setUp(self):
        self.client = InfoClient("127.0.0.1", 12345)
    
    @patch('socket.socket')
    def test_connect_success(self, mock_socket):
        """Test successful connection"""
        mock_sock = Mock()
        mock_socket.return_value = mock_sock
        
        result = self.client.connect()
        
        self.assertTrue(result)
        mock_sock.settimeout.assert_called_once_with(5.0)
        mock_sock.connect.assert_called_once_with(("127.0.0.1", 12345))
    
    @patch('socket.socket')
    def test_connect_failure(self, mock_socket):
        """Test connection failure"""
        mock_sock = Mock()
        mock_sock.connect.side_effect = ConnectionRefusedError()
        mock_socket.return_value = mock_sock
        
        result = self.client.connect()
        
        self.assertFalse(result)
    
    def test_disconnect(self):
        """Test disconnection"""
        self.client.socket = Mock()
        self.client.disconnect()
        
        self.client.socket.close.assert_called_once()
        self.assertIsNone(self.client.socket)
    
    @patch('time.time')
    def test_send_command_rate_limiting(self, mock_time):
        """Test rate limiting"""
        mock_time.side_effect = [0, 0.5, 1.0]  # First call, second call, sleep
        
        with patch.object(self.client, 'socket') as mock_socket:
            mock_socket.sendall.return_value = None
            mock_socket.recv.return_value = b'{"response": "ok"}'
            
            # First command should go through
            result1 = self.client.send_command({"test": "data1"})
            self.assertIsNotNone(result1)
            
            # Second command should be rate limited
            with patch('time.sleep') as mock_sleep:
                result2 = self.client.send_command({"test": "data2"})
                mock_sleep.assert_called_once()
                self.assertIsNotNone(result2)


if __name__ == '__main__':
    unittest.main()
