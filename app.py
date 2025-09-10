from flask import Flask, render_template, jsonify, request
from thebox.database import DroneDB
from thebox.event_manager import EventManager
from thebox.plugin_manager import PluginManager

app = Flask(__name__)
db = DroneDB()
event_manager = EventManager(db)
plugin_manager = PluginManager(event_manager)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/status')
def status():
    plugin_info = []
    for name, plugin in plugin_manager.plugins.items():
        info = {"name": plugin.name}
        if plugin.get_blueprint():
            info["has_web_interface"] = True
            info["web_url"] = f"/plugins/{plugin.name}"
        plugin_info.append(info)

    return jsonify({
        'plugins': plugin_info,
        'database': db._db
    })

@app.route('/event_history')
def event_history():
    return jsonify(event_manager.get_event_history())

@app.route('/plugins/config', methods=['GET'])
def get_plugins_config():
    config = plugin_manager.load_config()
    available_plugins = plugin_manager.get_available_plugins()
    return jsonify({
        "enabled_plugins": config.get("plugins", []),
        "available_plugins": available_plugins
    })

@app.route('/plugins/config', methods=['POST'])
def save_plugins_config():
    data = request.get_json()
    config = {"plugins": data.get("plugins", [])}
    plugin_manager.save_config(config)
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    plugin_manager.load_plugins(app)
    app.run(host='0.0.0.0', port=80, debug=True, use_reloader=False)
