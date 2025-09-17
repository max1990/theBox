#!/usr/bin/env python3
"""
UDP Simulator for TheBox Sensors
================================

Simulates UDP data from various sensors for testing and development.
Supports DroneShield, Silvus, MARA, Dspnor, and custom sensors.

Usage:
    python scripts/udp_simulator.py --sensor droneshield --port 8888 --rate 1.0
    python scripts/udp_simulator.py --sensor silvus --port 50051 --mode protobuf
    python scripts/udp_simulator.py --sensor mara --port 8787 --format json
"""

import argparse
import json
import random
import socket
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

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


class SensorSimulator:
    """Base class for sensor simulators"""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 8888, rate: float = 1.0):
        self.host = host
        self.port = port
        self.rate = rate
        self.running = False
        self.sock = None
        
    def start(self):
        """Start the simulator"""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.running = True
        logger.info("Simulator started", host=self.host, port=self.port, rate=self.rate)
        
    def stop(self):
        """Stop the simulator"""
        self.running = False
        if self.sock:
            self.sock.close()
        logger.info("Simulator stopped")
        
    def run(self):
        """Main simulation loop"""
        self.start()
        try:
            while self.running:
                data = self.generate_data()
                if data:
                    self.send_data(data)
                time.sleep(1.0 / self.rate)
        except KeyboardInterrupt:
            logger.info("Simulation interrupted by user")
        finally:
            self.stop()
            
    def generate_data(self) -> Optional[bytes]:
        """Generate sensor data - override in subclasses"""
        return None
        
    def send_data(self, data: bytes):
        """Send data via UDP"""
        try:
            self.sock.sendto(data, (self.host, self.port))
            logger.debug("Data sent", size=len(data))
        except Exception as e:
            logger.error("Failed to send data", error=str(e))


class DroneShieldSimulator(SensorSimulator):
    """Simulates DroneShield DS-X Mk2 detections"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.protocols = ["DJI", "AUTEL", "PARROT", "SKYDIO", "CUSTOM"]
        self.device_names = [
            "DJI Mavic Pro", "DJI Phantom 4", "DJI Mini 2", "DJI Air 2S",
            "AUTEL EVO II", "PARROT Anafi", "SKYDIO 2", "CUSTOM DRONE"
        ]
        self.bearing = 0.0
        
    def generate_data(self) -> bytes:
        """Generate DroneShield detection data"""
        # Rotate bearing for realistic movement
        self.bearing = (self.bearing + random.uniform(-30, 30)) % 360
        
        detection = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "bearing": round(self.bearing, 1),
            "rssi": random.randint(-85, -45),
            "signal_bars": random.randint(1, 10),
            "protocol": random.choice(self.protocols),
            "device_name": random.choice(self.device_names),
            "frequency_mhz": random.uniform(2400, 2500),
            "bandwidth_hz": random.choice([20000, 40000, 80000]),
            "modulation": random.choice(["FHSS", "DSSS", "OFDM"]),
            "snr_db": random.uniform(10, 30)
        }
        
        return json.dumps(detection).encode('utf-8')


class SilvusSimulator(SensorSimulator):
    """Simulates Silvus FASST AoA detections"""
    
    def __init__(self, mode: str = "text", **kwargs):
        super().__init__(**kwargs)
        self.mode = mode
        self.frequencies = [2400, 2450, 2500, 2550, 2600]
        self.bearing = 0.0
        self.heading = 0.0
        
    def generate_data(self) -> bytes:
        """Generate Silvus AoA data"""
        # Simulate vessel movement
        self.heading = (self.heading + random.uniform(-5, 5)) % 360
        self.bearing = (self.bearing + random.uniform(-20, 20)) % 360
        
        if self.mode == "text":
            # Text format
            data = {
                "time_utc": datetime.now(timezone.utc).isoformat(),
                "freq_mhz": random.choice(self.frequencies),
                "aoa1_deg": self.bearing,
                "aoa2_deg": (self.bearing + random.uniform(-10, 10)) % 360,
                "heading_deg": self.heading,
                "confidence": random.uniform(0.7, 0.95),
                "snr_db": random.uniform(15, 25)
            }
            return json.dumps(data).encode('utf-8')
        else:
            # Protobuf format (simplified)
            # In real implementation, would use actual protobuf serialization
            data = {
                "time_utc": datetime.now(timezone.utc).isoformat(),
                "freq_mhz": random.choice(self.frequencies),
                "aoa1_deg": self.bearing,
                "aoa2_deg": (self.bearing + random.uniform(-10, 10)) % 360,
                "heading_deg": self.heading
            }
            return json.dumps(data).encode('utf-8')


class MARASimulator(SensorSimulator):
    """Simulates MARA Spotter detections"""
    
    def __init__(self, format_type: str = "json", **kwargs):
        super().__init__(**kwargs)
        self.format_type = format_type
        self.bearing = 0.0
        self.range_m = 500.0
        
    def generate_data(self) -> bytes:
        """Generate MARA detection data"""
        # Simulate target movement
        self.bearing = (self.bearing + random.uniform(-15, 15)) % 360
        self.range_m = max(100, self.range_m + random.uniform(-50, 50))
        
        detection = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "bearing_deg": round(self.bearing, 1),
            "range_m": round(self.range_m, 1),
            "confidence": random.uniform(0.6, 0.9),
            "sensor_type": random.choice(["EO", "IR", "ACOUSTIC"]),
            "spl_dba": random.uniform(60, 90),
            "frequency_hz": random.uniform(100, 1000),
            "snr_db": random.uniform(10, 25),
            "sea_state": random.randint(0, 4)
        }
        
        if self.format_type == "json":
            return json.dumps(detection).encode('utf-8')
        else:
            # Binary format (simplified)
            return struct.pack('>f', self.bearing) + struct.pack('>f', self.range_m)


class DspnorSimulator(SensorSimulator):
    """Simulates Dspnor Dronnur 2D radar detections"""
    
    def __init__(self, protocol: str = "udp", **kwargs):
        super().__init__(**kwargs)
        self.protocol = protocol
        self.bearing = 0.0
        self.range_m = 800.0
        self.elevation = 0.0
        
    def generate_data(self) -> bytes:
        """Generate Dspnor radar data"""
        # Simulate target movement
        self.bearing = (self.bearing + random.uniform(-10, 10)) % 360
        self.range_m = max(200, self.range_m + random.uniform(-100, 100))
        self.elevation = max(-10, min(10, self.elevation + random.uniform(-2, 2)))
        
        detection = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "bearing_deg": round(self.bearing, 1),
            "range_m": round(self.range_m, 1),
            "elevation_deg": round(self.elevation, 1),
            "confidence": random.uniform(0.7, 0.95),
            "track_id": f"T{random.randint(1000, 9999)}",
            "doppler_hz": random.uniform(-100, 100),
            "rcs_dbsm": random.uniform(-20, 10),
            "scan_mode": random.choice(["SECTOR", "CIRCULAR", "TRACK"]),
            "pulse_width_us": random.uniform(1, 10),
            "prf_hz": random.uniform(1000, 5000)
        }
        
        return json.dumps(detection).encode('utf-8')


class CustomSimulator(SensorSimulator):
    """Simulates custom sensor data"""
    
    def __init__(self, data_file: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.data_file = data_file
        self.data_records = []
        self.current_index = 0
        
        if data_file:
            self.load_data_file()
            
    def load_data_file(self):
        """Load data from file for replay"""
        try:
            with open(self.data_file, 'r') as f:
                for line in f:
                    if line.strip():
                        self.data_records.append(json.loads(line.strip()))
            logger.info("Loaded data file", records=len(self.data_records))
        except Exception as e:
            logger.error("Failed to load data file", error=str(e))
            
    def generate_data(self) -> bytes:
        """Generate custom sensor data"""
        if self.data_records:
            # Replay mode
            if self.current_index >= len(self.data_records):
                self.current_index = 0  # Loop back
                
            record = self.data_records[self.current_index]
            self.current_index += 1
            return json.dumps(record).encode('utf-8')
        else:
            # Generate mode
            detection = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "bearing_deg": random.uniform(0, 360),
                "range_m": random.uniform(100, 2000),
                "confidence": random.uniform(0.5, 1.0),
                "sensor_id": f"SENSOR_{random.randint(1, 10)}",
                "data_type": "CUSTOM"
            }
            return json.dumps(detection).encode('utf-8')


def create_simulator(sensor_type: str, **kwargs) -> SensorSimulator:
    """Factory function to create appropriate simulator"""
    simulators = {
        "droneshield": DroneShieldSimulator,
        "silvus": SilvusSimulator,
        "mara": MARASimulator,
        "dspnor": DspnorSimulator,
        "custom": CustomSimulator
    }
    
    if sensor_type not in simulators:
        raise ValueError(f"Unknown sensor type: {sensor_type}")
        
    return simulators[sensor_type](**kwargs)


def main():
    parser = argparse.ArgumentParser(description="UDP Simulator for TheBox Sensors")
    parser.add_argument("--sensor", required=True, 
                       choices=["droneshield", "silvus", "mara", "dspnor", "custom"],
                       help="Sensor type to simulate")
    parser.add_argument("--host", default="127.0.0.1", help="Target host")
    parser.add_argument("--port", type=int, required=True, help="Target port")
    parser.add_argument("--rate", type=float, default=1.0, help="Data rate (Hz)")
    parser.add_argument("--mode", default="text", choices=["text", "protobuf"], 
                       help="Data format mode (for Silvus)")
    parser.add_argument("--format", default="json", choices=["json", "binary"], 
                       help="Data format (for MARA)")
    parser.add_argument("--protocol", default="udp", choices=["udp", "tcp"], 
                       help="Protocol (for Dspnor)")
    parser.add_argument("--data-file", help="Data file for replay mode (for custom)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
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
    
    # Create and run simulator
    try:
        simulator = create_simulator(
            args.sensor,
            host=args.host,
            port=args.port,
            rate=args.rate,
            mode=args.mode,
            format_type=args.format,
            protocol=args.protocol,
            data_file=args.data_file
        )
        
        logger.info("Starting simulator", 
                   sensor=args.sensor, 
                   host=args.host, 
                   port=args.port, 
                   rate=args.rate)
        
        simulator.run()
        
    except Exception as e:
        logger.error("Simulator failed", error=str(e))
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
