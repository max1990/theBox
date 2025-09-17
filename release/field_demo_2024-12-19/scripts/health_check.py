#!/usr/bin/env python3
"""
Health Check Script for TheBox
==============================

Simple health check script that can be used by load balancers,
monitoring systems, or Docker health checks.

Usage:
    python scripts/health_check.py [--port 80] [--timeout 5]
"""

import argparse
import json
import socket
import sys
import time
from typing import Dict, Any

import structlog

# Configure logging
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


class HealthChecker:
    """Health checker for TheBox application"""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 80, timeout: float = 5.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        
    def check_tcp_connection(self) -> bool:
        """Check if TCP connection can be established"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            result = sock.connect_ex((self.host, self.port))
            sock.close()
            return result == 0
        except Exception as e:
            logger.error("TCP connection check failed", error=str(e))
            return False
            
    def check_http_response(self) -> bool:
        """Check if HTTP response is received"""
        try:
            import urllib.request
            import urllib.error
            
            with urllib.request.urlopen(
                f"http://{self.host}:{self.port}/", 
                timeout=self.timeout
            ) as response:
                return response.status == 200
        except Exception as e:
            logger.error("HTTP response check failed", error=str(e))
            return False
            
    def check_plugin_endpoints(self) -> Dict[str, bool]:
        """Check plugin endpoint health"""
        plugin_endpoints = [
            "/droneshield_listener/status",
            "/silvus_listener/status",
            "/mara/status",
            "/confidence/status",
            "/range/status",
            "/trakka_control/status",
            "/vision/status"
        ]
        
        results = {}
        
        for endpoint in plugin_endpoints:
            try:
                import urllib.request
                import urllib.error
                
                with urllib.request.urlopen(
                    f"http://{self.host}:{self.port}{endpoint}",
                    timeout=self.timeout
                ) as response:
                    results[endpoint] = response.status == 200
            except Exception as e:
                logger.warning("Plugin endpoint check failed", endpoint=endpoint, error=str(e))
                results[endpoint] = False
                
        return results
        
    def check_database(self) -> bool:
        """Check database connectivity"""
        try:
            # Try to import and check database
            from thebox.database import DroneDB
            
            db = DroneDB()
            # Simple read operation
            db.get("health_check")
            return True
        except Exception as e:
            logger.error("Database check failed", error=str(e))
            return False
            
    def run_health_check(self) -> Dict[str, Any]:
        """Run complete health check"""
        start_time = time.time()
        
        # Basic connectivity checks
        tcp_ok = self.check_tcp_connection()
        http_ok = self.check_http_response()
        
        # Plugin checks
        plugin_results = self.check_plugin_endpoints()
        plugin_ok = any(plugin_results.values())
        
        # Database check
        db_ok = self.check_database()
        
        # Overall health
        overall_healthy = tcp_ok and http_ok and plugin_ok and db_ok
        
        duration = time.time() - start_time
        
        health_status = {
            "healthy": overall_healthy,
            "timestamp": time.time(),
            "duration_ms": duration * 1000,
            "checks": {
                "tcp_connection": tcp_ok,
                "http_response": http_ok,
                "plugin_endpoints": plugin_results,
                "database": db_ok
            }
        }
        
        return health_status


def main():
    parser = argparse.ArgumentParser(description="Health Check for TheBox")
    parser.add_argument("--host", default="127.0.0.1", help="Target host")
    parser.add_argument("--port", type=int, default=80, help="Target port")
    parser.add_argument("--timeout", type=float, default=5.0, help="Timeout in seconds")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--json", action="store_true", help="Output JSON format")
    
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
    
    # Run health check
    checker = HealthChecker(host=args.host, port=args.port, timeout=args.timeout)
    health_status = checker.run_health_check()
    
    # Output results
    if args.json:
        print(json.dumps(health_status, indent=2))
    else:
        if health_status["healthy"]:
            print("✓ TheBox is healthy")
        else:
            print("✗ TheBox is unhealthy")
            
        print(f"Duration: {health_status['duration_ms']:.1f}ms")
        
        for check_name, check_result in health_status["checks"].items():
            if isinstance(check_result, dict):
                print(f"{check_name}:")
                for endpoint, result in check_result.items():
                    status = "✓" if result else "✗"
                    print(f"  {status} {endpoint}")
            else:
                status = "✓" if check_result else "✗"
                print(f"{status} {check_name}")
    
    # Exit with appropriate code
    return 0 if health_status["healthy"] else 1


if __name__ == "__main__":
    exit(main())
