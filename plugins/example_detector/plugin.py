from thebox.plugin_interface import PluginInterface
from flask import Blueprint, render_template, jsonify, g
import datetime
import random
from collections import deque

class ExampleDetectorPlugin(PluginInterface):
    def __init__(self, event_manager):
        super().__init__(event_manager)
        self.received_events = deque(maxlen=100)

    def load(self):
        print("Example Detector Plugin Loaded")
        self.event_manager.subscribe("detection", "drones", self.on_detection, 10)

    def on_detection(self, event_type, path, value):
        print(f"Listener plugin got event: {event_type} for path {path} with value: {value}")
        self.received_events.append({
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "event_type": event_type,
            "path": path,
            "value": value
        })
        # Return True to terminate the event
        return False

    def unload(self):
        print("Example Detector Plugin Unloaded")

    def get_blueprint(self):
        bp = Blueprint(self.name, __name__, template_folder='templates', static_folder='static')
        
        @bp.route('/')
        def index():
            return render_template('example_detector_plugin.html')

        @bp.route('/events')
        def events():
            return jsonify(list(self.received_events))
        
        @bp.route('/add_drone', methods=['POST'])
        def add_drone():
            now = datetime.datetime.utcnow().isoformat() + "Z"
            drone_id = f"droneid{random.randint(100, 999)}"
            detection_data = {
                f"drones.{drone_id}.detections.{now}": {
                    "direction": random.randint(0, 359),
                    "distance": random.randint(100, 500),
                    "detector": self.name
                },
                f"drones.{drone_id}.state": "detected"
            }
            self.publish("detection", detection_data, store_in_db=True)
            return jsonify({"status": "ok", "drone_id": drone_id})

        @bp.route('/add_drone_no_store', methods=['POST'])
        def add_drone_no_store():
            now = datetime.datetime.utcnow().isoformat() + "Z"
            drone_id = f"droneid{random.randint(100, 999)}"
            detection_data = {
                f"drones.{drone_id}.detections.{now}": {
                    "direction": random.randint(0, 359),
                    "distance": random.randint(100, 500),
                    "detector": self.name
                },
                f"drones.{drone_id}.state": "detected"
            }
            self.publish("detection", detection_data, store_in_db=False)
            return jsonify({"status": "ok", "drone_id": drone_id})
            
        return bp
