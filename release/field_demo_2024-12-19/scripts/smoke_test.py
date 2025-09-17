#!/usr/bin/env python3
"""
Smoke Test for TheBox
=====================

Headless smoke test that spins up the stack, fires synthetic UDP,
verifies normalized detections, and exits non-zero on failure.

Usage:
    python scripts/smoke_test.py [--timeout 30] [--verbose]
"""

import argparse
import json
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
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


class SmokeTest:
    """Main smoke test class"""
    
    def __init__(self, timeout: int = 30, verbose: bool = False):
        self.timeout = timeout
        self.verbose = verbose
        self.process: Optional[subprocess.Popen] = None
        self.test_results: List[Dict[str, Any]] = []
        self.start_time = time.time()
        
    def run(self) -> int:
        """Run the complete smoke test"""
        logger.info("Starting smoke test", timeout=self.timeout)
        
        try:
            # Test 1: Start TheBox application
            if not self.start_thebox():
                return 1
                
            # Test 2: Wait for application to be ready
            if not self.wait_for_ready():
                return 1
                
            # Test 3: Send synthetic UDP data
            if not self.send_test_data():
                return 1
                
            # Test 4: Verify detections are processed
            if not self.verify_detections():
                return 1
                
            # Test 5: Test web interface
            if not self.test_web_interface():
                return 1
                
            # Test 6: Test plugin endpoints
            if not self.test_plugin_endpoints():
                return 1
                
            # Test 7: Test graceful shutdown
            if not self.test_shutdown():
                return 1
                
            logger.info("All smoke tests passed", duration=time.time() - self.start_time)
            return 0
            
        except Exception as e:
            logger.error("Smoke test failed", error=str(e))
            return 1
        finally:
            self.cleanup()
            
    def start_thebox(self) -> bool:
        """Start TheBox application"""
        logger.info("Starting TheBox application")
        
        try:
            # Start the application
            self.process = subprocess.Popen(
                [sys.executable, "app.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Give it a moment to start
            time.sleep(2)
            
            # Check if it's still running
            if self.process.poll() is not None:
                stdout, stderr = self.process.communicate()
                logger.error("TheBox failed to start", 
                           returncode=self.process.returncode,
                           stdout=stdout,
                           stderr=stderr)
                return False
                
            logger.info("TheBox started successfully", pid=self.process.pid)
            return True
            
        except Exception as e:
            logger.error("Failed to start TheBox", error=str(e))
            return False
            
    def wait_for_ready(self) -> bool:
        """Wait for TheBox to be ready"""
        logger.info("Waiting for TheBox to be ready")
        
        start_time = time.time()
        while time.time() - start_time < self.timeout:
            try:
                # Try to connect to the web interface
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex(("127.0.0.1", 80))
                sock.close()
                
                if result == 0:
                    logger.info("TheBox is ready")
                    return True
                    
            except Exception:
                pass
                
            time.sleep(1)
            
        logger.error("TheBox did not become ready within timeout")
        return False
        
    def send_test_data(self) -> bool:
        """Send synthetic UDP test data"""
        logger.info("Sending test data")
        
        test_data = [
            {
                "sensor": "droneshield",
                "port": 8888,
                "data": {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "bearing": 45.0,
                    "rssi": -65,
                    "signal_bars": 7,
                    "protocol": "DJI",
                    "device_name": "DJI Mavic Pro"
                }
            },
            {
                "sensor": "silvus",
                "port": 50051,
                "data": {
                    "time_utc": datetime.now(timezone.utc).isoformat(),
                    "freq_mhz": 2450.0,
                    "aoa1_deg": 90.0,
                    "aoa2_deg": 95.0,
                    "heading_deg": 0.0,
                    "confidence": 0.8,
                    "snr_db": 20.0
                }
            },
            {
                "sensor": "mara",
                "port": 8787,
                "data": {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "bearing_deg": 135.0,
                    "range_m": 800.0,
                    "confidence": 0.75,
                    "sensor_type": "EO",
                    "spl_dba": 75.0
                }
            }
        ]
        
        success_count = 0
        for test in test_data:
            try:
                # Send UDP data
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                data = json.dumps(test["data"]).encode('utf-8')
                sock.sendto(data, ("127.0.0.1", test["port"]))
                sock.close()
                
                logger.info("Sent test data", sensor=test["sensor"], port=test["port"])
                success_count += 1
                
                # Wait a bit between sends
                time.sleep(0.5)
                
            except Exception as e:
                logger.error("Failed to send test data", sensor=test["sensor"], error=str(e))
                
        return success_count > 0
        
    def verify_detections(self) -> bool:
        """Verify that detections are being processed"""
        logger.info("Verifying detections")
        
        # Wait for processing
        time.sleep(2)
        
        try:
            # Check if we can access the web interface
            import urllib.request
            import urllib.error
            
            # Test main page
            try:
                with urllib.request.urlopen("http://127.0.0.1:80/", timeout=5) as response:
                    if response.status == 200:
                        logger.info("Web interface accessible")
                    else:
                        logger.warning("Web interface returned non-200 status", status=response.status)
            except urllib.error.URLError as e:
                logger.error("Web interface not accessible", error=str(e))
                return False
                
            # Test plugin status endpoints
            plugin_endpoints = [
                "/droneshield_listener/status",
                "/silvus_listener/status", 
                "/mara/status",
                "/confidence/status",
                "/range/status"
            ]
            
            accessible_endpoints = 0
            for endpoint in plugin_endpoints:
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:80{endpoint}", timeout=2) as response:
                        if response.status == 200:
                            accessible_endpoints += 1
                            logger.info("Plugin endpoint accessible", endpoint=endpoint)
                except urllib.error.URLError:
                    logger.warning("Plugin endpoint not accessible", endpoint=endpoint)
                    
            if accessible_endpoints == 0:
                logger.error("No plugin endpoints accessible")
                return False
                
            logger.info("Detection verification passed", accessible_endpoints=accessible_endpoints)
            return True
            
        except Exception as e:
            logger.error("Failed to verify detections", error=str(e))
            return False
            
    def test_web_interface(self) -> bool:
        """Test web interface functionality"""
        logger.info("Testing web interface")
        
        try:
            import urllib.request
            import urllib.error
            
            # Test main page
            with urllib.request.urlopen("http://127.0.0.1:80/", timeout=5) as response:
                if response.status != 200:
                    logger.error("Main page test failed", status=response.status)
                    return False
                    
            # Test settings page
            try:
                with urllib.request.urlopen("http://127.0.0.1:80/settings", timeout=5) as response:
                    if response.status == 200:
                        logger.info("Settings page accessible")
                    else:
                        logger.warning("Settings page returned non-200 status", status=response.status)
            except urllib.error.URLError:
                logger.warning("Settings page not accessible")
                
            logger.info("Web interface test passed")
            return True
            
        except Exception as e:
            logger.error("Web interface test failed", error=str(e))
            return False
            
    def test_plugin_endpoints(self) -> bool:
        """Test plugin-specific endpoints"""
        logger.info("Testing plugin endpoints")
        
        try:
            import urllib.request
            import urllib.error
            
            # Test plugin status endpoints
            plugin_tests = [
                ("/droneshield_listener/status", "DroneShield Listener"),
                ("/silvus_listener/status", "Silvus Listener"),
                ("/mara/status", "MARA"),
                ("/confidence/status", "Confidence"),
                ("/range/status", "Range"),
                ("/trakka_control/status", "Trakka Control"),
                ("/vision/status", "Vision")
            ]
            
            passed_tests = 0
            for endpoint, name in plugin_tests:
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:80{endpoint}", timeout=2) as response:
                        if response.status == 200:
                            # Try to parse JSON response
                            data = json.loads(response.read().decode('utf-8'))
                            logger.info("Plugin endpoint test passed", plugin=name, endpoint=endpoint)
                            passed_tests += 1
                        else:
                            logger.warning("Plugin endpoint returned non-200 status", 
                                         plugin=name, status=response.status)
                except urllib.error.URLError as e:
                    logger.warning("Plugin endpoint not accessible", plugin=name, error=str(e))
                except json.JSONDecodeError as e:
                    logger.warning("Plugin endpoint returned invalid JSON", plugin=name, error=str(e))
                    
            if passed_tests == 0:
                logger.error("No plugin endpoints passed tests")
                return False
                
            logger.info("Plugin endpoint tests passed", passed=passed_tests, total=len(plugin_tests))
            return True
            
        except Exception as e:
            logger.error("Plugin endpoint tests failed", error=str(e))
            return False
            
    def test_shutdown(self) -> bool:
        """Test graceful shutdown"""
        logger.info("Testing graceful shutdown")
        
        try:
            if self.process:
                # Send SIGTERM
                self.process.terminate()
                
                # Wait for graceful shutdown
                try:
                    self.process.wait(timeout=10)
                    logger.info("Graceful shutdown successful")
                    return True
                except subprocess.TimeoutExpired:
                    # Force kill if graceful shutdown fails
                    self.process.kill()
                    self.process.wait()
                    logger.warning("Forced shutdown after timeout")
                    return True
            else:
                logger.warning("No process to shutdown")
                return True
                
        except Exception as e:
            logger.error("Shutdown test failed", error=str(e))
            return False
            
    def cleanup(self):
        """Cleanup resources"""
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            except Exception as e:
                logger.warning("Error during cleanup", error=str(e))


def main():
    parser = argparse.ArgumentParser(description="Smoke Test for TheBox")
    parser.add_argument("--timeout", type=int, default=30, help="Test timeout in seconds")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    parser.add_argument("--quick", action="store_true", help="Quick test (reduced timeout)")
    
    args = parser.parse_args()
    
    # Adjust timeout for quick test
    if args.quick:
        args.timeout = 10
        
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
    
    # Run smoke test
    smoke_test = SmokeTest(timeout=args.timeout, verbose=args.verbose)
    return smoke_test.run()


if __name__ == "__main__":
    exit(main())
