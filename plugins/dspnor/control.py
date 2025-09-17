"""
Control interface for Dspnor plugin
"""

import json
import socket
import time
from typing import Optional, Dict, Any, List
import structlog

from .constants import DEFAULT_DISCOVERY_MULTICAST, DEFAULT_RESET_MULTICAST_PORT
from .schemas import D2DCommand, ServiceConfig

logger = structlog.get_logger(__name__)


class DspnorController:
    """Controller for Dspnor unit operations"""
    
    def __init__(self, safe_mode: bool = True, unit_serial: str = ""):
        self.safe_mode = safe_mode
        self.unit_serial = unit_serial
        self.allow_reset = False
        self.allow_reboot = False
        self.logger = logger.bind(component="controller")
    
    def set_permissions(self, allow_reset: bool = False, allow_reboot: bool = False):
        """Set dangerous operation permissions"""
        self.allow_reset = allow_reset
        self.allow_reboot = allow_reboot
        self.logger.info("Controller permissions updated", 
                        allow_reset=allow_reset, allow_reboot=allow_reboot)
    
    def init_system(self, info_client) -> bool:
        """Initialize system"""
        if self.safe_mode:
            self.logger.warning("System initialization blocked in safe mode")
            return False
        
        command = {"InitSystem": True}
        response = info_client.send_command(command)
        
        if response and "InitSystem" in response:
            self.logger.info("System initialized successfully")
            return True
        else:
            self.logger.error("Failed to initialize system")
            return False
    
    def set_tx_mode(self, info_client, mode: str) -> bool:
        """Set transmission mode"""
        if self.safe_mode:
            self.logger.warning("TX mode change blocked in safe mode")
            return False
        
        valid_modes = ["off", "normal", "test"]
        if mode not in valid_modes:
            self.logger.error("Invalid TX mode", mode=mode, valid_modes=valid_modes)
            return False
        
        command = {"TxMode": mode}
        response = info_client.send_command(command)
        
        if response and "TxMode" in response:
            self.logger.info("TX mode set", mode=mode)
            return True
        else:
            self.logger.error("Failed to set TX mode", mode=mode)
            return False
    
    def configure_antenna(self, info_client, operation: str, **kwargs) -> bool:
        """Configure antenna operation"""
        if self.safe_mode:
            self.logger.warning("Antenna configuration blocked in safe mode")
            return False
        
        valid_operations = ["off", "cw", "sector", "blanking", "tilt"]
        if operation not in valid_operations:
            self.logger.error("Invalid antenna operation", 
                            operation=operation, valid_operations=valid_operations)
            return False
        
        command = {"AntennaOperation": operation}
        command.update(kwargs)
        
        response = info_client.send_command(command)
        
        if response and "AntennaOperation" in response:
            self.logger.info("Antenna operation configured", operation=operation, **kwargs)
            return True
        else:
            self.logger.error("Failed to configure antenna", operation=operation)
            return False
    
    def set_antenna_rpm(self, info_client, rpm: float) -> bool:
        """Set antenna RPM"""
        if self.safe_mode:
            self.logger.warning("Antenna RPM change blocked in safe mode")
            return False
        
        if not (0.1 <= rpm <= 60.0):
            self.logger.error("Invalid antenna RPM", rpm=rpm, valid_range="0.1-60.0")
            return False
        
        command = {"AntennaRPM": rpm}
        response = info_client.send_command(command)
        
        if response and "AntennaRPM" in response:
            self.logger.info("Antenna RPM set", rpm=rpm)
            return True
        else:
            self.logger.error("Failed to set antenna RPM", rpm=rpm)
            return False
    
    def set_antenna_sector(self, info_client, start_az: float, end_az: float) -> bool:
        """Set antenna sector"""
        if self.safe_mode:
            self.logger.warning("Antenna sector change blocked in safe mode")
            return False
        
        if not (0.0 <= start_az <= 360.0) or not (0.0 <= end_az <= 360.0):
            self.logger.error("Invalid sector angles", start_az=start_az, end_az=end_az)
            return False
        
        command = {
            "AntennaSector": {
                "StartAzimuth": start_az,
                "EndAzimuth": end_az
            }
        }
        response = info_client.send_command(command)
        
        if response and "AntennaSector" in response:
            self.logger.info("Antenna sector set", start_az=start_az, end_az=end_az)
            return True
        else:
            self.logger.error("Failed to set antenna sector")
            return False
    
    def set_blanking_sectors(self, info_client, sectors: List[Dict[str, float]]) -> bool:
        """Set blanking sectors"""
        if self.safe_mode:
            self.logger.warning("Blanking sectors change blocked in safe mode")
            return False
        
        # Validate sectors
        for sector in sectors:
            if "start" not in sector or "end" not in sector:
                self.logger.error("Invalid blanking sector format", sector=sector)
                return False
            
            start = sector["start"]
            end = sector["end"]
            if not (0.0 <= start <= 360.0) or not (0.0 <= end <= 360.0):
                self.logger.error("Invalid blanking sector angles", start=start, end=end)
                return False
        
        command = {"BlankingSectors": sectors}
        response = info_client.send_command(command)
        
        if response and "BlankingSectors" in response:
            self.logger.info("Blanking sectors set", count=len(sectors))
            return True
        else:
            self.logger.error("Failed to set blanking sectors")
            return False
    
    def configure_service(self, info_client, service_name: str, 
                         config: ServiceConfig) -> bool:
        """Configure service"""
        if self.safe_mode:
            self.logger.warning("Service configuration blocked in safe mode")
            return False
        
        command = {
            service_name: {
                "Enabled": config.enabled,
                "IP": config.ip,
                "Port": config.port,
                "Protocol": config.protocol
            }
        }
        
        response = info_client.send_command(command)
        
        if response and service_name in response:
            self.logger.info("Service configured", 
                           service=service_name, config=config.dict())
            return True
        else:
            self.logger.error("Failed to configure service", service=service_name)
            return False
    
    def enable_cat010_udp(self, info_client, host: str, port: int) -> bool:
        """Enable CAT-010 UDP service"""
        config = ServiceConfig(
            enabled=True,
            ip=host,
            port=port,
            protocol="UDP"
        )
        return self.configure_service(info_client, "AsterixCat010", config)
    
    def disable_cat240(self, info_client) -> bool:
        """Disable CAT-240 video service"""
        config = ServiceConfig(
            enabled=False,
            ip="",
            port=0,
            protocol="TCP"
        )
        return self.configure_service(info_client, "AsterixCat240", config)
    
    def inject_external_ins(self, info_client, heading: float, lat: float, 
                           lon: float, cog: float, sog: float) -> bool:
        """Inject external INS data"""
        if self.safe_mode:
            self.logger.warning("External INS injection blocked in safe mode")
            return False
        
        command = {
            "ExternalINS": {
                "TrueBearing": heading,
                "Latitude": lat,
                "Longitude": lon,
                "CourseOverGround": cog,
                "SpeedOverGround": sog
            }
        }
        
        response = info_client.send_command(command)
        
        if response and "ExternalINS" in response:
            self.logger.info("External INS data injected", 
                           heading=heading, lat=lat, lon=lon)
            return True
        else:
            self.logger.error("Failed to inject external INS data")
            return False
    
    def reset_unit(self, unit_ip: str) -> bool:
        """Reset unit (requires permissions)"""
        if not self.allow_reset:
            self.logger.error("Reset operation not allowed")
            return False
        
        if not self.unit_serial:
            self.logger.error("Unit serial not configured for reset")
            return False
        
        try:
            # Send reset command via multicast
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            reset_command = {
                "Reset": True,
                "SerialNumber": self.unit_serial
            }
            
            message = json.dumps(reset_command).encode('utf-8')
            sock.sendto(message, (DEFAULT_DISCOVERY_MULTICAST, DEFAULT_RESET_MULTICAST_PORT))
            sock.close()
            
            self.logger.warning("Reset command sent", unit_ip=unit_ip, serial=self.unit_serial)
            return True
            
        except Exception as e:
            self.logger.error("Failed to send reset command", error=str(e))
            return False
    
    def reboot_unit(self, unit_ip: str) -> bool:
        """Reboot unit (requires permissions)"""
        if not self.allow_reboot:
            self.logger.error("Reboot operation not allowed")
            return False
        
        if not self.unit_serial:
            self.logger.error("Unit serial not configured for reboot")
            return False
        
        try:
            # Send reboot command via multicast
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            reboot_command = {
                "Reboot": True,
                "SerialNumber": self.unit_serial
            }
            
            message = json.dumps(reboot_command).encode('utf-8')
            sock.sendto(message, (DEFAULT_DISCOVERY_MULTICAST, DEFAULT_RESET_MULTICAST_PORT))
            sock.close()
            
            self.logger.warning("Reboot command sent", unit_ip=unit_ip, serial=self.unit_serial)
            return True
            
        except Exception as e:
            self.logger.error("Failed to send reboot command", error=str(e))
            return False
    
    def get_system_info(self, info_client) -> Optional[Dict[str, Any]]:
        """Get system information"""
        return info_client.send_command({"GetSystemInfo": True})
    
    def get_services(self, info_client) -> Optional[Dict[str, Any]]:
        """Get service configuration"""
        return info_client.send_command({"GetServices": True})
    
    def get_status(self, info_client) -> Optional[Dict[str, Any]]:
        """Get system status"""
        return info_client.send_command({"GetStatus": True})
