"""
Confidence Plugin
================

Plugin for managing detection confidence using Bayesian fusion.
"""

import logging
from flask import Blueprint, jsonify, render_template

from thebox.plugin_interface import PluginInterface
from .confidence_plugin import ConfidencePlugin

log = logging.getLogger("plugins.confidence")


class ConfidencePluginWrapper(PluginInterface):
    """Wrapper for ConfidencePlugin to conform to PluginInterface"""
    
    def __init__(self, event_manager):
        super().__init__(event_manager)
        self.confidence_plugin = ConfidencePlugin()
        self.track_confidences = {}  # track_id -> confidence
        
    def load(self):
        """Load the confidence plugin"""
        log.info("Confidence plugin loaded")
        
        # Subscribe to detection events
        self.event_manager.subscribe("droneshield_detection", self._handle_detection)
        self.event_manager.subscribe("object.sighting.directional", self._handle_detection)
        self.event_manager.subscribe("mara_detection", self._handle_detection)
        self.event_manager.subscribe("dspnor_detection", self._handle_detection)
        self.event_manager.subscribe("vision_detection", self._handle_detection)
        
    def unload(self):
        """Unload the confidence plugin"""
        log.info("Confidence plugin unloaded")
        
    def _handle_detection(self, event_type: str, data: dict):
        """Handle detection events and update confidence"""
        try:
            detection = data.get("detection", {})
            track_id = detection.get("track_id", "default")
            
            # Get current confidence
            current_confidence = self.track_confidences.get(track_id, self.confidence_plugin.initial_score())
            
            # Extract cues from detection
            cues = self._extract_cues(detection, event_type)
            
            # Update confidence
            confidence_update = self.confidence_plugin.update(current_confidence, cues)
            
            # Store updated confidence
            self.track_confidences[track_id] = confidence_update.confidence_0_1
            
            # Publish confidence update
            self.publish("object.confidence", {
                "track_id": track_id,
                "confidence_0_1": confidence_update.confidence_0_1,
                "reason": confidence_update.reason,
                "details": confidence_update.details,
                "timestamp": detection.get("timestamp", ""),
                "source": event_type
            })
            
        except Exception as e:
            log.error(f"Error handling detection: {e}")
    
    def _extract_cues(self, detection: dict, event_type: str) -> dict:
        """Extract confidence cues from detection data"""
        cues = {"track_id": detection.get("track_id", "default")}
        
        # RF cues
        if "rssi" in detection:
            cues["rf"] = detection["rssi"]
        elif "signal_bars" in detection:
            cues["rf"] = detection["signal_bars"]
        
        # Vision cues
        if event_type == "vision_detection":
            cues["vision"] = detection.get("confidence", 0.5)
            if detection.get("verified", False):
                cues["vision_verified"] = 1.0
        
        # Acoustic cues
        if "spl_dba" in detection:
            cues["acoustic"] = detection["spl_dba"]
        
        # IR cues
        if "ir_confidence" in detection:
            cues["ir"] = detection["ir_confidence"]
        
        return cues
    
    def get_blueprint(self):
        """Get Flask blueprint for web UI"""
        bp = Blueprint(self.name, __name__, template_folder="templates")
        
        @bp.route("/")
        def index():
            return render_template("confidence_plugin.html")
        
        @bp.route("/status")
        def status():
            return jsonify({
                "track_confidences": self.track_confidences,
                "plugin_stats": {
                    "updates": self.confidence_plugin.updates,
                    "base_confidence": self.confidence_plugin.base,
                    "fusion_method": self.confidence_plugin.fusion_method
                }
            })
        
        @bp.route("/reset", methods=["POST"])
        def reset():
            """Reset all track confidences"""
            self.track_confidences.clear()
            return jsonify({"status": "ok", "message": "Confidences reset"})
        
        return bp
