"""
Range Plugin
============

Plugin for estimating range to detected objects using multiple sensor cues.
"""

import logging
from flask import Blueprint, jsonify, render_template

from thebox.plugin_interface import PluginInterface
from .range_plugin import RangePlugin

log = logging.getLogger("plugins.range")


class RangePluginWrapper(PluginInterface):
    """Wrapper for RangePlugin to conform to PluginInterface"""
    
    def __init__(self, event_manager):
        super().__init__(event_manager)
        self.range_plugin = RangePlugin()
        self.track_ranges = {}  # track_id -> range_estimate
        
    def load(self):
        """Load the range plugin"""
        log.info("Range plugin loaded")
        
        # Subscribe to detection events
        self.event_manager.subscribe("droneshield_detection", self._handle_detection)
        self.event_manager.subscribe("object.sighting.directional", self._handle_detection)
        self.event_manager.subscribe("mara_detection", self._handle_detection)
        self.event_manager.subscribe("dspnor_detection", self._handle_detection)
        self.event_manager.subscribe("vision_detection", self._handle_detection)
        
    def unload(self):
        """Unload the range plugin"""
        log.info("Range plugin unloaded")
        
    def _handle_detection(self, event_type: str, data: dict):
        """Handle detection events and estimate range"""
        try:
            detection = data.get("detection", {})
            track_id = detection.get("track_id", "default")
            
            # Extract sensor data
            signal_data = self._extract_signal_data(detection, event_type)
            eo_data = self._extract_eo_data(detection, event_type)
            ir_data = self._extract_ir_data(detection, event_type)
            acoustic_data = self._extract_acoustic_data(detection, event_type)
            
            # Estimate range
            range_estimate = self.range_plugin.estimate_km(
                signal=signal_data,
                eo=eo_data,
                ir=ir_data,
                ac=acoustic_data
            )
            
            # Store range estimate
            self.track_ranges[track_id] = range_estimate
            
            # Publish range update
            self.publish("object.range", {
                "track_id": track_id,
                "range_km": range_estimate.range_km,
                "sigma_km": range_estimate.sigma_km,
                "mode": range_estimate.mode,
                "details": range_estimate.details,
                "timestamp": detection.get("timestamp", ""),
                "source": event_type
            })
            
        except Exception as e:
            log.error(f"Error handling detection: {e}")
    
    def _extract_signal_data(self, detection: dict, event_type: str) -> dict | None:
        """Extract RF signal data from detection"""
        if event_type in ["droneshield_detection", "object.sighting.directional"]:
            signal_data = {}
            
            if "rssi" in detection:
                signal_data["RSSI"] = detection["rssi"]
            if "signal_bars" in detection:
                signal_data["SignalBars"] = detection["signal_bars"]
            if "snr_db" in detection:
                signal_data["SNR"] = detection["snr_db"]
            
            return signal_data if signal_data else None
        
        return None
    
    def _extract_eo_data(self, detection: dict, event_type: str) -> dict | None:
        """Extract EO camera data from detection"""
        if event_type == "vision_detection" and detection.get("sensor_type") == "eo":
            eo_data = {}
            
            if "pixel_height" in detection:
                eo_data["pixel_height"] = detection["pixel_height"]
            if "frame_height" in detection:
                eo_data["frame_height"] = detection["frame_height"]
            if "fov_deg" in detection:
                eo_data["fov_deg"] = detection["fov_deg"]
            if "backlit" in detection:
                eo_data["backlit"] = detection["backlit"]
            if "poor_contrast" in detection:
                eo_data["poor_contrast"] = detection["poor_contrast"]
            
            return eo_data if eo_data else None
        
        return None
    
    def _extract_ir_data(self, detection: dict, event_type: str) -> dict | None:
        """Extract IR camera data from detection"""
        if event_type == "vision_detection" and detection.get("sensor_type") == "ir":
            ir_data = {}
            
            if "pixel_height" in detection:
                ir_data["pixel_height"] = detection["pixel_height"]
            if "frame_height" in detection:
                ir_data["frame_height"] = detection["frame_height"]
            if "fov_deg" in detection:
                ir_data["fov_deg"] = detection["fov_deg"]
            if "backlit" in detection:
                ir_data["backlit"] = detection["backlit"]
            if "poor_contrast" in detection:
                ir_data["poor_contrast"] = detection["poor_contrast"]
            
            return ir_data if ir_data else None
        
        return None
    
    def _extract_acoustic_data(self, detection: dict, event_type: str) -> dict | None:
        """Extract acoustic data from detection"""
        if event_type == "mara_detection":
            acoustic_data = {}
            
            if "spl_dba" in detection:
                acoustic_data["spl_dba"] = detection["spl_dba"]
            if "snr_db" in detection:
                acoustic_data["snr_db"] = detection["snr_db"]
            if "sea_state" in detection:
                acoustic_data["sea_state"] = detection["sea_state"]
            
            return acoustic_data if acoustic_data else None
        
        return None
    
    def get_blueprint(self):
        """Get Flask blueprint for web UI"""
        bp = Blueprint(self.name, __name__, template_folder="templates")
        
        @bp.route("/")
        def index():
            return render_template("range_plugin.html")
        
        @bp.route("/status")
        def status():
            return jsonify({
                "track_ranges": {
                    track_id: {
                        "range_km": est.range_km,
                        "sigma_km": est.sigma_km,
                        "mode": est.mode
                    }
                    for track_id, est in self.track_ranges.items()
                },
                "plugin_stats": {
                    "estimates": self.range_plugin.estimates,
                    "mode": self.range_plugin.mode,
                    "fixed_km": self.range_plugin.fixed_km
                }
            })
        
        @bp.route("/reset", methods=["POST"])
        def reset():
            """Reset all track ranges"""
            self.track_ranges.clear()
            return jsonify({"status": "ok", "message": "Ranges reset"})
        
        return bp
