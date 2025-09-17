"""
CAT-010 parser for Dspnor plugin
"""

import struct
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import structlog

from .constants import (
    CAT010_ITEM_140, CAT010_ITEM_161, CAT010_ITEM_040, CAT010_ITEM_041,
    CAT010_ITEM_042, CAT010_ITEM_200, CAT010_ITEM_202, CAT010_ITEM_220,
    CAT010_ITEM_245, MMSI_BIT_POSITION
)
from .schemas import CAT010Track

logger = structlog.get_logger(__name__)


class CAT010Parser:
    """Parser for CAT-010 track messages"""
    
    def __init__(self):
        self.logger = logger.bind(component="cat010_parser")
    
    def parse(self, data: bytes) -> Optional[CAT010Track]:
        """Parse CAT-010 message"""
        try:
            if len(data) < 3:
                self.logger.warning("Message too short for CAT-010")
                return None
            
            # Check CAT-010 identifier (0x0A)
            if data[0] != 0x0A:
                self.logger.warning("Not a CAT-010 message", first_byte=data[0])
                return None
            
            # Parse length (next 2 bytes, big-endian)
            length = struct.unpack('>H', data[1:3])[0]
            if len(data) < length + 3:
                self.logger.warning("Message length mismatch", 
                                  expected=length + 3, actual=len(data))
                return None
            
            # Parse FSPEC and data items
            track = CAT010Track()
            pos = 3  # Skip CAT, LEN
            
            # Parse FSPEC (variable length)
            fspec_length = self._parse_fspec_length(data, pos)
            if fspec_length is None:
                return None
            
            fspec = data[pos:pos + fspec_length]
            pos += fspec_length
            
            # Parse data items based on FSPEC
            track = self._parse_data_items(data, pos, fspec, track)
            
            return track
            
        except Exception as e:
            self.logger.error("Failed to parse CAT-010 message", error=str(e))
            return None
    
    def _parse_fspec_length(self, data: bytes, pos: int) -> Optional[int]:
        """Parse FSPEC length"""
        if pos >= len(data):
            return None
        
        # FSPEC is variable length, terminated by 0 bit
        fspec_length = 0
        for i in range(pos, min(pos + 8, len(data))):
            fspec_length += 1
            if (data[i] & 0x01) == 0:  # Last bit is 0
                break
        
        return fspec_length
    
    def _parse_data_items(self, data: bytes, pos: int, fspec: bytes, track: CAT010Track) -> CAT010Track:
        """Parse data items based on FSPEC"""
        bit_pos = 0
        fspec_byte = 0
        
        for i in range(len(fspec)):
            fspec_byte = fspec[i]
            
            for bit in range(7, -1, -1):  # MSB first
                if (fspec_byte >> bit) & 1:
                    item_id = (i * 8) + (7 - bit) + 1
                    pos = self._parse_item(data, pos, item_id, track)
                    if pos is None:
                        break
                else:
                    break  # FSPEC terminated
            
            if (fspec_byte & 0x01) == 0:  # Last bit is 0
                break
        
        return track
    
    def _parse_item(self, data: bytes, pos: int, item_id: int, track: CAT010Track) -> Optional[int]:
        """Parse individual data item"""
        try:
            if item_id == CAT010_ITEM_140:  # Time of Day
                if pos + 3 > len(data):
                    return None
                # 3-byte time of day in 1/128 seconds
                tod_raw = struct.unpack('>I', b'\x00' + data[pos:pos+3])[0]
                track.time_of_day = tod_raw / 128.0
                return pos + 3
            
            elif item_id == CAT010_ITEM_161:  # Track Number
                if pos + 2 > len(data):
                    return None
                track.track_number = struct.unpack('>H', data[pos:pos+2])[0]
                return pos + 2
            
            elif item_id == CAT010_ITEM_040:  # Target Report Descriptor
                if pos + 1 > len(data):
                    return None
                # Parse descriptor bits
                desc = data[pos]
                # Could extract additional info from descriptor
                return pos + 1
            
            elif item_id == CAT010_ITEM_041:  # Target Address
                if pos + 3 > len(data):
                    return None
                track.target_address = struct.unpack('>I', b'\x00' + data[pos:pos+3])[0]
                return pos + 3
            
            elif item_id == CAT010_ITEM_042:  # Track Quality
                if pos + 1 > len(data):
                    return None
                track.track_quality = data[pos]
                return pos + 1
            
            elif item_id == CAT010_ITEM_200:  # Ground Speed
                if pos + 2 > len(data):
                    return None
                # Speed in 0.25 m/s units
                speed_raw = struct.unpack('>H', data[pos:pos+2])[0]
                track.ground_speed = speed_raw * 0.25
                return pos + 2
            
            elif item_id == CAT010_ITEM_202:  # Track Angle Rate
                if pos + 2 > len(data):
                    return None
                # Angle rate in 0.01 degrees/second
                rate_raw = struct.unpack('>h', data[pos:pos+2])[0]
                track.track_angle_rate = rate_raw * 0.01
                return pos + 2
            
            elif item_id == CAT010_ITEM_220:  # Mode 3/A Code
                if pos + 2 > len(data):
                    return None
                track.mode_3a_code = struct.unpack('>H', data[pos:pos+2])[0]
                return pos + 2
            
            elif item_id == CAT010_ITEM_245:  # Target Identification
                if pos + 6 > len(data):
                    return None
                # 6-byte target ID
                track.target_id = data[pos:pos+6].decode('ascii', errors='ignore')
                
                # Check MMSI bit (bit 54 in the 6-byte field)
                # MMSI bit is in the 2nd byte, bit 6 (0-indexed)
                mmsi_byte = data[pos + 1]
                track.has_mmsi = bool(mmsi_byte & 0x40)  # Bit 6
                
                return pos + 6
            
            else:
                # Unknown item, skip based on common sizes
                if pos + 1 <= len(data):
                    return pos + 1
                return None
                
        except Exception as e:
            self.logger.error("Failed to parse item", item_id=item_id, error=str(e))
            return None
    
    def extract_position(self, track: CAT010Track) -> Optional[tuple]:
        """Extract position from track (polar or cartesian)"""
        if track.position_polar:
            return track.position_polar
        elif track.position_cartesian:
            return track.position_cartesian
        return None
    
    def extract_velocity(self, track: CAT010Track) -> Optional[tuple]:
        """Extract velocity from track (polar or cartesian)"""
        if track.velocity_polar:
            return track.velocity_polar
        elif track.velocity_cartesian:
            return track.velocity_cartesian
        elif track.ground_speed is not None:
            # Convert ground speed to polar velocity
            return (track.ground_speed, 0.0)  # (speed, heading)
        return None
    
    def get_track_id(self, track: CAT010Track) -> str:
        """Get unique track identifier"""
        if track.track_number is not None:
            return f"dspnor_track_{track.track_number}"
        elif track.target_address is not None:
            return f"dspnor_addr_{track.target_address:06x}"
        else:
            return f"dspnor_unknown_{id(track)}"
    
    def is_valid_track(self, track: CAT010Track) -> bool:
        """Check if track has minimum required data"""
        return (track.track_number is not None or 
                track.target_address is not None or
                track.position_polar is not None or
                track.position_cartesian is not None)
