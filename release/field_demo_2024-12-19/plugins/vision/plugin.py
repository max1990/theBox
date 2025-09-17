"""
Vision Plugin
=============

Plugin for vision-based detection and verification using EO/IR cameras.
"""

import logging
from flask import Blueprint, jsonify, render_template

from thebox.plugin_interface import PluginInterface
from .vision_plugin import VisionPlugin

log = logging.getLogger("plugins.vision")


class VisionPluginWrapper(PluginInterface):
    """Wrapper for VisionPlugin to conform to PluginInterface"""
    
    def __init__(self, event_manager):
        super().__init__(event_manager)
        self.vision_plugin = VisionPlugin()
        self.detection_count = 0
        
    def load(self):
        """Load the vision plugin"""
        log.info("Vision plugin loaded")
        
        # Subscribe to camera commands
        self.event_manager.subscribe("camera_command", self._handle_camera_command)
        
    def unload(self):
        """Unload the vision plugin"""
        log.info("Vision plugin unloaded")
        
    def _handle_camera_command(self, event_type: str, data: dict):
        """Handle camera command events"""
        try:
            command = data.get("command", {})
            action = command.get("action")
            
            if action == "slew":
                bearing_deg = command.get("bearing_deg")
                track_id = command.get("track_id")
                
                if bearing_deg is not None:
                    # Slew camera to bearing
                    result = self.vision_plugin.slew_to_bearing(bearing_deg)
                    
                    # Publish vision detection if verified
                    if result.verified:
                        self.publish("vision_detection", {
                            "track_id": track_id,
                            "bearing_deg": bearing_deg,
                            "verified": result.verified,
                            "label": result.label,
                            "confidence": 0.8,  # High confidence for verified detections
                            "latency_ms": result.latency,
                            "bbox": result.bbox,
                            "timestamp": "",
                            "source": "vision"
                        })
                        
                        self.detection_count += 1
                        
        except Exception as e:
            log.error(f"Error handling camera command: {e}")
    
    def get_blueprint(self):
        """Get Flask blueprint for web UI"""
        bp = Blueprint(self.name, __name__, template_folder="templates")
        
        @bp.route("/")
        def index():
            return render_template("vision_plugin.html")
        
        @bp.route("/status")
        def status():
            return jsonify({
                "detection_count": self.detection_count,
                "plugin_config": {
                    "backend": self.vision_plugin.backend,
                    "input_resolution": self.vision_plugin.input_res,
                    "roi_half_deg": self.vision_plugin.roi_half_deg,
                    "frame_skip": self.vision_plugin.frame_skip,
                    "n_consec_for_true": self.vision_plugin.n_consec_for_true,
                    "latency_ms": self.vision_plugin.latency_ms,
                    "max_dwell_ms": self.vision_plugin.max_dwell_ms,
                    "sweep_step_deg": self.vision_plugin.sweep_step_deg,
                    "priority": self.vision_plugin.priority,
                    "verdict_default": self.vision_plugin.verdict_default,
                    "label_default": self.vision_plugin.label_default
                }
            })
        
        @bp.route("/slew", methods=["POST"])
        def slew():
            """Slew camera to specified bearing"""
            data = request.get_json()
            bearing_deg = data.get("bearing_deg")
            track_id = data.get("track_id", "manual")
            
            if bearing_deg is None:
                return jsonify({"status": "error", "message": "bearing_deg required"}), 400
            
            try:
                result = self.vision_plugin.slew_to_bearing(bearing_deg)
                
                return jsonify({
                    "status": "ok",
                    "result": {
                        "verified": result.verified,
                        "label": result.label,
                        "latency_ms": result.latency,
                        "bbox": result.bbox
                    }
                })
                
            except Exception as e:
                return jsonify({"status": "error", "message": str(e)}), 500
        
        @bp.route("/reset", methods=["POST"])
        def reset():
            """Reset detection count"""
            self.detection_count = 0
            return jsonify({"status": "ok", "message": "Detection count reset"})
        
        return bp
