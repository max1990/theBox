from thebox.plugin_interface import PluginInterface
from flask import Blueprint, render_template, request, jsonify

class ExampleModifierPlugin(PluginInterface):
    def __init__(self, event_manager):
        super().__init__(event_manager)
        self.modifier_key = "example_modifier_plugin_was_here"
        self.modifier_value = True

    def load(self):
        print("Example Modifier Plugin Loaded")
        self.event_manager.subscribe("detection", "drones", self.on_detection, 5)

    def on_detection(self, event_type, path, value):
        print(f"Input plugin got event: {event_type} for path {path} with value: {value}")
        
        # Only act on the 'state' field to avoid loops on our own modifications.
        if path.endswith(".state"):
            # Construct the path to the detection this state belongs to.
            detection_path = ".".join(path.split('.')[:-1])
            self.publish("detection with modification", {
                f"{detection_path}.{self.modifier_key}": self.modifier_value
            })

    def unload(self):
        print("Example Modifier Plugin Unloaded")

    def get_blueprint(self):
        bp = Blueprint(self.name, __name__, template_folder='templates')
        
        @bp.route('/')
        def index():
            return render_template('example_modifier_plugin.html')

        @bp.route('/update', methods=['POST'])
        def update():
            data = request.get_json()
            self.modifier_key = data.get('key', self.modifier_key)
            raw_value = data.get('value', str(self.modifier_value))
            
            # Attempt to convert to boolean or integer if possible
            if raw_value.lower() == 'true':
                self.modifier_value = True
            elif raw_value.lower() == 'false':
                self.modifier_value = False
            else:
                try:
                    self.modifier_value = int(raw_value)
                except (ValueError, TypeError):
                    self.modifier_value = raw_value # Keep as string if conversion fails

            return jsonify({"status": "ok"})
            
        return bp
