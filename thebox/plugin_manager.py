import importlib
import os
import json

class PluginManager:
    def __init__(self, event_manager):
        self.event_manager = event_manager
        self.plugins = {}

    def load_plugins(self, app, plugin_dir="plugins"):
        config = self.load_config()
        loaded_plugins = config.get("plugins", [])

        for plugin_name in loaded_plugins:
            plugin_path = os.path.join(plugin_dir, plugin_name)
            if os.path.isdir(plugin_path) and not plugin_name.startswith("__"):
                module_name = f"{plugin_dir}.{plugin_name}.plugin"
                try:
                    module = importlib.import_module(module_name)
                    for item in dir(module):
                        if item.endswith("Plugin"):
                            plugin_class = getattr(module, item)
                            plugin_instance = plugin_class(self.event_manager)
                            plugin_instance.load()
                            self.plugins[plugin_name] = plugin_instance

                            blueprint = plugin_instance.get_blueprint()
                            if blueprint:
                                app.register_blueprint(blueprint, url_prefix=f"/plugins/{plugin_instance.name}")
                except ImportError as e:
                    print(f"Could not import plugin {plugin_name}: {e}")

    def unload_plugins(self):
        for name, plugin in self.plugins.items():
            plugin.unload()
        self.plugins = {}

    def load_config(self):
        try:
            with open("config.json", "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {"plugins": []}

    def save_config(self, config):
        with open("config.json", "w") as f:
            json.dump(config, f, indent=4)

    def get_available_plugins(self, plugin_dir="plugins"):
        available = []
        for plugin_name in os.listdir(plugin_dir):
            plugin_path = os.path.join(plugin_dir, plugin_name)
            if os.path.isdir(plugin_path) and not plugin_name.startswith("__"):
                available.append(plugin_name)
        return available
