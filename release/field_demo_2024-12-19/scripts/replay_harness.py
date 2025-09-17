#!/usr/bin/env python3
"""
Replay Harness for TheBox
=========================

Replays recorded sensor data for testing and validation.
Supports multiple data formats and playback modes.

Usage:
    python scripts/replay_harness.py --file data/droneshield.jsonl --sensor droneshield
    python scripts/replay_harness.py --file data/silvus.txt --sensor silvus --rate 2.0
    python scripts/replay_harness.py --file data/mara.bin --sensor mara --format binary
"""

import argparse
import json
import socket
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, Optional

import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


class DataReplayer:
    """Base class for data replayers"""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 8888, rate: float = 1.0):
        self.host = host
        self.port = port
        self.rate = rate
        self.running = False
        self.sock = None
        
    def start(self):
        """Start the replayer"""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.running = True
        logger.info("Replayer started", host=self.host, port=self.port, rate=self.rate)
        
    def stop(self):
        """Stop the replayer"""
        self.running = False
        if self.sock:
            self.sock.close()
        logger.info("Replayer stopped")
        
    def send_data(self, data: bytes):
        """Send data via UDP"""
        try:
            self.sock.sendto(data, (self.host, self.port))
            logger.debug("Data sent", size=len(data))
        except Exception as e:
            logger.error("Failed to send data", error=str(e))
            
    def replay(self, data_iterator: Iterator[bytes]):
        """Replay data from iterator"""
        self.start()
        try:
            for data in data_iterator:
                if not self.running:
                    break
                self.send_data(data)
                time.sleep(1.0 / self.rate)
        except KeyboardInterrupt:
            logger.info("Replay interrupted by user")
        finally:
            self.stop()


class JSONLReplayer(DataReplayer):
    """Replays JSONL (JSON Lines) data files"""
    
    def __init__(self, file_path: Path, **kwargs):
        super().__init__(**kwargs)
        self.file_path = file_path
        
    def load_data(self) -> Iterator[bytes]:
        """Load and yield data from JSONL file"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    if line.strip():
                        try:
                            data = json.loads(line.strip())
                            yield json.dumps(data).encode('utf-8')
                        except json.JSONDecodeError as e:
                            logger.warning("Invalid JSON on line", line=line_num, error=str(e))
        except Exception as e:
            logger.error("Failed to load JSONL file", error=str(e))
            
    def replay_file(self):
        """Replay the entire file"""
        data_iterator = self.load_data()
        self.replay(data_iterator)


class TextReplayer(DataReplayer):
    """Replays text data files"""
    
    def __init__(self, file_path: Path, **kwargs):
        super().__init__(**kwargs)
        self.file_path = file_path
        
    def load_data(self) -> Iterator[bytes]:
        """Load and yield data from text file"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    if line.strip():
                        # Parse text format (customize based on sensor)
                        data = self.parse_text_line(line.strip())
                        if data:
                            yield json.dumps(data).encode('utf-8')
        except Exception as e:
            logger.error("Failed to load text file", error=str(e))
            
    def parse_text_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse a single text line - override in subclasses"""
        # Default: treat as JSON
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            # Try to parse as space-separated values
            parts = line.split()
            if len(parts) >= 2:
                return {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "value1": parts[0],
                    "value2": parts[1],
                    "raw_line": line
                }
        return None
        
    def replay_file(self):
        """Replay the entire file"""
        data_iterator = self.load_data()
        self.replay(data_iterator)


class SilvusTextReplayer(TextReplayer):
    """Replays Silvus text format data"""
    
    def parse_text_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse Silvus text format"""
        try:
            # Silvus format: timestamp freq_mhz aoa1_deg aoa2_deg heading_deg
            parts = line.split()
            if len(parts) >= 5:
                return {
                    "time_utc": parts[0],
                    "freq_mhz": float(parts[1]),
                    "aoa1_deg": float(parts[2]),
                    "aoa2_deg": float(parts[3]),
                    "heading_deg": float(parts[4]),
                    "confidence": 0.8,  # Default confidence
                    "snr_db": 20.0     # Default SNR
                }
        except (ValueError, IndexError) as e:
            logger.warning("Failed to parse Silvus line", line=line, error=str(e))
        return None


class BinaryReplayer(DataReplayer):
    """Replays binary data files"""
    
    def __init__(self, file_path: Path, **kwargs):
        super().__init__(**kwargs)
        self.file_path = file_path
        
    def load_data(self) -> Iterator[bytes]:
        """Load and yield data from binary file"""
        try:
            with open(self.file_path, 'rb') as f:
                # Read in chunks (customize based on data format)
                chunk_size = 1024
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk
        except Exception as e:
            logger.error("Failed to load binary file", error=str(e))
            
    def replay_file(self):
        """Replay the entire file"""
        data_iterator = self.load_data()
        self.replay(data_iterator)


class DroneShieldReplayer(JSONLReplayer):
    """Replays DroneShield data with proper formatting"""
    
    def load_data(self) -> Iterator[bytes]:
        """Load and format DroneShield data"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    if line.strip():
                        try:
                            data = json.loads(line.strip())
                            # Ensure proper DroneShield format
                            formatted_data = self.format_droneshield_data(data)
                            yield json.dumps(formatted_data).encode('utf-8')
                        except json.JSONDecodeError as e:
                            logger.warning("Invalid JSON on line", line=line_num, error=str(e))
        except Exception as e:
            logger.error("Failed to load DroneShield file", error=str(e))
            
    def format_droneshield_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format data to DroneShield specification"""
        # Ensure required fields
        if "timestamp" not in data:
            data["timestamp"] = datetime.now(timezone.utc).isoformat()
        if "bearing" not in data:
            data["bearing"] = 0.0
        if "rssi" not in data:
            data["rssi"] = -70
        if "protocol" not in data:
            data["protocol"] = "UNKNOWN"
        if "device_name" not in data:
            data["device_name"] = "UNKNOWN"
            
        return data


class MARAReplayer(JSONLReplayer):
    """Replays MARA data with proper formatting"""
    
    def load_data(self) -> Iterator[bytes]:
        """Load and format MARA data"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    if line.strip():
                        try:
                            data = json.loads(line.strip())
                            # Ensure proper MARA format
                            formatted_data = self.format_mara_data(data)
                            yield json.dumps(formatted_data).encode('utf-8')
                        except json.JSONDecodeError as e:
                            logger.warning("Invalid JSON on line", line=line_num, error=str(e))
        except Exception as e:
            logger.error("Failed to load MARA file", error=str(e))
            
    def format_mara_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format data to MARA specification"""
        # Ensure required fields
        if "timestamp" not in data:
            data["timestamp"] = datetime.now(timezone.utc).isoformat()
        if "bearing_deg" not in data:
            data["bearing_deg"] = 0.0
        if "range_m" not in data:
            data["range_m"] = 500.0
        if "confidence" not in data:
            data["confidence"] = 0.8
        if "sensor_type" not in data:
            data["sensor_type"] = "EO"
            
        return data


def create_replayer(sensor_type: str, file_path: Path, **kwargs) -> DataReplayer:
    """Factory function to create appropriate replayer"""
    replayers = {
        "droneshield": DroneShieldReplayer,
        "silvus": SilvusTextReplayer,
        "mara": MARAReplayer,
        "dspnor": JSONLReplayer,
        "custom": JSONLReplayer
    }
    
    if sensor_type not in replayers:
        raise ValueError(f"Unknown sensor type: {sensor_type}")
        
    return replayers[sensor_type](file_path, **kwargs)


def detect_file_format(file_path: Path) -> str:
    """Detect file format based on extension and content"""
    suffix = file_path.suffix.lower()
    
    if suffix == '.jsonl':
        return 'jsonl'
    elif suffix == '.txt':
        return 'text'
    elif suffix in ['.bin', '.dat']:
        return 'binary'
    elif suffix == '.json':
        # Check if it's JSONL or single JSON
        try:
            with open(file_path, 'r') as f:
                first_line = f.readline().strip()
                if first_line:
                    json.loads(first_line)
                    # Check if there's a second line
                    second_line = f.readline().strip()
                    if second_line:
                        return 'jsonl'
                    else:
                        return 'json'
        except:
            pass
    elif suffix == '.csv':
        return 'text'
    
    return 'text'  # Default


def main():
    parser = argparse.ArgumentParser(description="Replay Harness for TheBox")
    parser.add_argument("--file", required=True, type=Path, help="Data file to replay")
    parser.add_argument("--sensor", required=True,
                       choices=["droneshield", "silvus", "mara", "dspnor", "custom"],
                       help="Sensor type")
    parser.add_argument("--host", default="127.0.0.1", help="Target host")
    parser.add_argument("--port", type=int, required=True, help="Target port")
    parser.add_argument("--rate", type=float, default=1.0, help="Replay rate (Hz)")
    parser.add_argument("--format", choices=["jsonl", "text", "binary", "auto"],
                       default="auto", help="File format (auto-detect if not specified)")
    parser.add_argument("--loop", action="store_true", help="Loop playback")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    # Check if file exists
    if not args.file.exists():
        logger.error("File not found", file=str(args.file))
        return 1
    
    # Configure logging level
    if args.verbose:
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.dev.ConsoleRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
    
    # Detect file format if auto
    if args.format == "auto":
        args.format = detect_file_format(args.file)
        logger.info("Detected file format", format=args.format)
    
    # Create and run replayer
    try:
        replayer = create_replayer(
            args.sensor,
            args.file,
            host=args.host,
            port=args.port,
            rate=args.rate
        )
        
        logger.info("Starting replay", 
                   file=str(args.file),
                   sensor=args.sensor, 
                   host=args.host, 
                   port=args.port, 
                   rate=args.rate,
                   format=args.format)
        
        if args.loop:
            while True:
                replayer.replay_file()
                logger.info("Replay completed, looping...")
        else:
            replayer.replay_file()
        
    except Exception as e:
        logger.error("Replay failed", error=str(e))
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
