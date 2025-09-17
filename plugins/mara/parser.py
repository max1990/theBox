"""
MARA data format autodetection and parsing logic.
"""
import json
import csv
import io
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import structlog

from .models import NormalizedDetection, MARARawData

logger = structlog.get_logger(__name__)


class MARAParser:
    """Parser for MARA data with automatic format detection."""
    
    def __init__(self):
        self.logger = logger.bind(component="mara_parser")
    
    def autodetect_and_parse(self, line: str) -> Optional[NormalizedDetection]:
        """
        Automatically detect format and parse MARA data line.
        
        Args:
            line: Raw data line from MARA system
            
        Returns:
            NormalizedDetection or None if parsing fails
        """
        if not line or not line.strip():
            return None
            
        line = line.strip()
        
        # Try JSON first
        if line.startswith('{') and line.endswith('}'):
            return self._parse_json(line)
        
        # Try key=value pairs
        if '=' in line and not line.startswith('#'):
            return self._parse_key_value(line)
        
        # Try CSV (look for comma-separated values)
        if ',' in line and not line.startswith('#'):
            return self._parse_csv(line)
        
        # If none match, log and return None
        self.logger.warning("Unknown format", line=line[:100])
        return None
    
    def _parse_json(self, line: str) -> Optional[NormalizedDetection]:
        """Parse JSON format MARA data."""
        try:
            data = json.loads(line)
            raw_data = MARARawData(**data)
            return self._create_normalized_detection(raw_data, line)
        except (json.JSONDecodeError, Exception) as e:
            self.logger.warning("JSON parse error", error=str(e), line=line[:100])
            return None
    
    def _parse_key_value(self, line: str) -> Optional[NormalizedDetection]:
        """Parse key=value format MARA data."""
        try:
            data = {}
            # Split by spaces but handle quoted values
            parts = self._split_key_value_line(line)
            for part in parts:
                if '=' in part:
                    key, value = part.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"\'')
                    data[key] = value
            
            raw_data = MARARawData(**data)
            return self._create_normalized_detection(raw_data, line)
        except Exception as e:
            self.logger.warning("Key-value parse error", error=str(e), line=line[:100])
            return None
    
    def _parse_csv(self, line: str) -> Optional[NormalizedDetection]:
        """Parse CSV format MARA data."""
        try:
            # Use a simple CSV reader
            reader = csv.reader(io.StringIO(line))
            row = next(reader)
            
            # If this looks like a header row, skip it
            if any(header in str(row).lower() for header in ['timestamp', 'sensor_id', 'object_id']):
                return None
            
            # Map common CSV column names to our schema
            data = {}
            for i, value in enumerate(row):
                if i < len(self._csv_headers):
                    data[self._csv_headers[i]] = value.strip()
            
            raw_data = MARARawData(**data)
            return self._create_normalized_detection(raw_data, line)
        except Exception as e:
            self.logger.warning("CSV parse error", error=str(e), line=line[:100])
            return None
    
    def _split_key_value_line(self, line: str) -> List[str]:
        """Split key=value line handling quoted values."""
        parts = []
        current = ""
        in_quotes = False
        quote_char = None
        
        for char in line:
            if char in ['"', "'"] and not in_quotes:
                in_quotes = True
                quote_char = char
                current += char
            elif char == quote_char and in_quotes:
                in_quotes = False
                quote_char = None
                current += char
            elif char == ' ' and not in_quotes:
                if current.strip():
                    parts.append(current.strip())
                    current = ""
            else:
                current += char
        
        if current.strip():
            parts.append(current.strip())
        
        return parts
    
    def _create_normalized_detection(self, raw_data: MARARawData, original_line: str) -> Optional[NormalizedDetection]:
        """Create normalized detection from parsed raw data."""
        try:
            # Parse timestamp
            timestamp_utc = self._parse_timestamp(raw_data.timestamp)
            
            # Create normalized detection
            detection = NormalizedDetection(
                sensor_channel=raw_data.channel or "UNKNOWN",
                event_type=raw_data.event_type,  # Let model validator determine this
                label=raw_data.label,
                confidence=self._parse_confidence(raw_data.confidence),
                bearing_deg=self._parse_float(raw_data.bearing_deg),
                elev_deg=self._parse_float(raw_data.elevation_deg),
                range_km=self._parse_range(raw_data.range_m),
                lat=self._parse_float(raw_data.lat),
                lon=self._parse_float(raw_data.lon),
                speed_mps=self._parse_float(raw_data.speed_mps),
                heading_deg=self._parse_float(raw_data.heading_deg),
                track_id=raw_data.track_id,
                timestamp_utc=timestamp_utc,
                raw=original_line
            )
            
            self.logger.debug("Created normalized detection", 
                            object_id=raw_data.object_id,
                            sensor_channel=detection.sensor_channel,
                            event_type=detection.event_type)
            
            return detection
            
        except Exception as e:
            self.logger.error("Failed to create normalized detection", 
                            error=str(e), 
                            raw_data=raw_data.dict())
            return None
    
    def _parse_timestamp(self, timestamp_str: Optional[str]) -> datetime:
        """Parse timestamp string to UTC datetime."""
        if not timestamp_str:
            return datetime.now(timezone.utc)
        
        try:
            # Try ISO format first
            if 'T' in timestamp_str and 'Z' in timestamp_str:
                return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            elif 'T' in timestamp_str:
                return datetime.fromisoformat(timestamp_str)
            else:
                # Try other common formats
                for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M:%S.%f']:
                    try:
                        dt = datetime.strptime(timestamp_str, fmt)
                        return dt.replace(tzinfo=timezone.utc)
                    except ValueError:
                        continue
                
                # If all else fails, return current time
                return datetime.now(timezone.utc)
        except Exception:
            return datetime.now(timezone.utc)
    
    def _parse_confidence(self, confidence_val: Any) -> Optional[float]:
        """Parse confidence value to float 0.0-1.0."""
        if confidence_val is None:
            return None
        
        try:
            conf = float(confidence_val)
            # If confidence is > 1, assume it's a percentage
            if conf > 1.0:
                conf = conf / 100.0
            return max(0.0, min(1.0, conf))
        except (ValueError, TypeError):
            return None
    
    def _parse_float(self, value: Any) -> Optional[float]:
        """Parse value to float, return None if invalid."""
        if value is None:
            return None
        
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def _parse_range(self, range_val: Any) -> Optional[float]:
        """Parse range value, converting meters to km if needed."""
        if range_val is None:
            return None
        
        try:
            range_m = float(range_val)
            # Convert meters to kilometers
            return range_m / 1000.0
        except (ValueError, TypeError):
            return None
    
    # Common CSV headers for mapping
    _csv_headers = [
        'timestamp', 'sensor_id', 'object_id', 'confidence', 'bearing_deg',
        'elevation_deg', 'range_m', 'lat', 'lon', 'speed_mps', 'heading_deg',
        'label', 'channel'
    ]
