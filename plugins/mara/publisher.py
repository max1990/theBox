"""
Publisher for normalized MARA detections to stdout and UDP.
"""
import asyncio
import json
import socket
from typing import Optional
import structlog

from .models import NormalizedDetection

logger = structlog.get_logger(__name__)


class MARAPublisher:
    """Publisher for normalized MARA detections."""
    
    def __init__(self, enable_udp: bool = False, 
                 udp_host: str = "127.0.0.1", udp_port: int = 7878):
        self.enable_udp = enable_udp
        self.udp_host = udp_host
        self.udp_port = udp_port
        self.logger = logger.bind(component="mara_publisher")
        self._udp_socket = None
        
        if self.enable_udp:
            self._setup_udp()
    
    def _setup_udp(self):
        """Setup UDP socket for rebroadcast."""
        try:
            self._udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.logger.info("UDP rebroadcast enabled", 
                           host=self.udp_host, 
                           port=self.udp_port)
        except Exception as e:
            self.logger.error("Failed to setup UDP socket", error=str(e))
            self.enable_udp = False
    
    async def publish(self, detection: NormalizedDetection):
        """
        Publish normalized detection to stdout and optionally UDP.
        
        Args:
            detection: Normalized detection to publish
        """
        try:
            # Convert to JSON
            json_data = detection.json()
            
            # Always print to stdout
            print(json_data)
            
            # Optionally send via UDP
            if self.enable_udp and self._udp_socket:
                await self._send_udp(json_data)
            
            self.logger.debug("Published detection", 
                            object_id=detection.track_id,
                            event_type=detection.event_type,
                            sensor_channel=detection.sensor_channel)
            
        except Exception as e:
            self.logger.error("Failed to publish detection", 
                            error=str(e),
                            detection=detection.dict())
    
    async def _send_udp(self, json_data: str):
        """Send JSON data via UDP."""
        try:
            data_bytes = json_data.encode('utf-8')
            self._udp_socket.sendto(data_bytes, (self.udp_host, self.udp_port))
            self.logger.debug("Sent UDP rebroadcast", 
                            host=self.udp_host,
                            port=self.udp_port,
                            size=len(data_bytes))
        except Exception as e:
            self.logger.error("Failed to send UDP", error=str(e))
    
    def close(self):
        """Close UDP socket if open."""
        if self._udp_socket:
            self._udp_socket.close()
            self._udp_socket = None
            self.logger.info("UDP socket closed")
