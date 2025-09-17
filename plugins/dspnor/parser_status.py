"""
Status parser for Dspnor plugin
"""

import json
from typing import Optional, Dict, Any
from datetime import datetime
import structlog

from .schemas import StatusData

logger = structlog.get_logger(__name__)


class StatusParser:
    """Parser for runtime status JSON messages"""
    
    def __init__(self):
        self.logger = logger.bind(component="status_parser")
    
    def parse(self, data: str) -> Optional[StatusData]:
        """Parse status JSON message"""
        try:
            status_json = json.loads(data)
            
            # Extract internal sources
            internal_sources = {}
            if "dspnor.asterix010_server" in status_json:
                internal_sources["asterix010_server"] = status_json["dspnor.asterix010_server"]
            if "dspnor.dronnur_extractor" in status_json:
                internal_sources["dronnur_extractor"] = status_json["dspnor.dronnur_extractor"]
            if "dspnor.dronnur_tracker" in status_json:
                internal_sources["dronnur_tracker"] = status_json["dspnor.dronnur_tracker"]
            if "dspnor.dronnurclient" in status_json:
                internal_sources["dronnurclient"] = status_json["dspnor.dronnurclient"]
            
            # Extract external sources
            external_sources = {}
            if "Services" in status_json:
                services = status_json["Services"]
                for service_name, service_config in services.items():
                    if service_config.get("Enabled", False):
                        external_sources[service_name] = service_config
            
            # Extract temperatures (if available)
            temperatures = {}
            if "Temperatures" in status_json:
                temperatures = status_json["Temperatures"]
            elif "temperatures" in status_json:
                temperatures = status_json["temperatures"]
            
            # Extract mode information
            mode = "unknown"
            if "Mode" in status_json:
                mode = status_json["Mode"]
            elif "mode" in status_json:
                mode = status_json["mode"]
            
            # Extract sensor information
            sensors = {}
            if "Sensors" in status_json:
                sensors = status_json["Sensors"]
            elif "sensors" in status_json:
                sensors = status_json["sensors"]
            
            # Determine health status
            health_status = self._determine_health_status(status_json, internal_sources, external_sources)
            
            return StatusData(
                timestamp=datetime.now(),
                internal_sources=internal_sources,
                external_sources=external_sources,
                temperatures=temperatures,
                mode=mode,
                sensors=sensors,
                health_status=health_status
            )
            
        except json.JSONDecodeError as e:
            self.logger.error("Failed to parse status JSON", error=str(e))
            return None
        except Exception as e:
            self.logger.error("Failed to parse status data", error=str(e))
            return None
    
    def _determine_health_status(self, status_json: Dict[str, Any], 
                                internal_sources: Dict[str, Any],
                                external_sources: Dict[str, Any]) -> str:
        """Determine overall health status"""
        try:
            # Check if key services are enabled and running
            services = status_json.get("Services", {})
            
            # Check CAT-010 service
            cat010_enabled = services.get("AsterixCat010", {}).get("Enabled", False)
            if not cat010_enabled:
                return "degraded"
            
            # Check external sources
            external_gns_enabled = services.get("ExternalGNS", {}).get("Enabled", False)
            external_ins_enabled = services.get("ExternalINS", {}).get("Enabled", False)
            
            # Check internal components
            if not internal_sources.get("dronnur_extractor"):
                return "degraded"
            
            if not internal_sources.get("dronnur_tracker"):
                return "degraded"
            
            # Check for error indicators
            if "Errors" in status_json or "errors" in status_json:
                return "error"
            
            # Check temperatures if available
            temperatures = status_json.get("Temperatures", {})
            if temperatures:
                for sensor, temp in temperatures.items():
                    if isinstance(temp, (int, float)):
                        if temp > 80:  # High temperature threshold
                            return "warning"
                        elif temp > 90:  # Critical temperature
                            return "error"
            
            # All checks passed
            if external_gns_enabled or external_ins_enabled:
                return "good"
            else:
                return "warning"  # No external positioning
                
        except Exception as e:
            self.logger.error("Error determining health status", error=str(e))
            return "unknown"
    
    def get_last_update_times(self, status: StatusData) -> Dict[str, datetime]:
        """Get last update times for various components"""
        last_updates = {}
        
        # Check internal sources for last update times
        for component, configs in status.internal_sources.items():
            if isinstance(configs, list) and configs:
                config = configs[0]  # Take first config
                if "LastUpdate" in config:
                    try:
                        last_updates[component] = datetime.fromisoformat(config["LastUpdate"])
                    except:
                        pass
                elif "last_update" in config:
                    try:
                        last_updates[component] = datetime.fromisoformat(config["last_update"])
                    except:
                        pass
        
        # Check external sources
        for service, config in status.external_sources.items():
            if "LastUpdate" in config:
                try:
                    last_updates[service] = datetime.fromisoformat(config["LastUpdate"])
                except:
                    pass
            elif "last_update" in config:
                try:
                    last_updates[service] = datetime.fromisoformat(config["last_update"])
                except:
                    pass
        
        return last_updates
    
    def is_status_stale(self, status: StatusData, max_age_seconds: int = 10) -> bool:
        """Check if status data is stale"""
        last_updates = self.get_last_update_times(status)
        
        if not last_updates:
            return True  # No update times available
        
        now = datetime.now()
        for component, last_update in last_updates.items():
            age_seconds = (now - last_update).total_seconds()
            if age_seconds > max_age_seconds:
                self.logger.warning("Stale status detected", 
                                  component=component, age_seconds=age_seconds)
                return True
        
        return False
