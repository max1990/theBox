# Load environment early
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from mvp.env_loader import load_thebox_env

load_thebox_env()

from flask import Flask, jsonify, render_template, request

from thebox.database import DroneDB
from thebox.event_manager import EventManager
from thebox.plugin_manager import PluginManager
from webui.settings import create_settings_blueprint
from webui.testconsole import create_testconsole_blueprint

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-key-change-in-production")
db = DroneDB()
event_manager = EventManager(db)
plugin_manager = PluginManager(event_manager)

# Register Settings blueprint
app.register_blueprint(create_settings_blueprint(event_manager), url_prefix="")
app.register_blueprint(
    create_testconsole_blueprint(event_manager, plugin_manager), url_prefix="/test"
)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/status")
def status():
    plugin_info = []
    for name, plugin in plugin_manager.plugins.items():
        info = {"name": plugin.name}
        if plugin.get_blueprint():
            info["has_web_interface"] = True
            info["web_url"] = f"/plugins/{plugin.name}"
        plugin_info.append(info)

    return jsonify({"plugins": plugin_info, "database": db._db})


@app.route("/health")
def health():
    """Health check endpoint for load balancers and monitoring"""
    import time
    from datetime import datetime, timezone
    
    start_time = time.time()
    
    # Basic health checks
    checks = {
        "database": True,  # Database is in-memory, always available
        "plugins_loaded": len(plugin_manager.plugins) > 0,
        "event_manager": event_manager is not None,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    # Check plugin health
    plugin_health = {}
    for name, plugin in plugin_manager.plugins.items():
        try:
            # Try to get plugin status if it has a blueprint
            if plugin.get_blueprint():
                plugin_health[name] = "available"
            else:
                plugin_health[name] = "no_web_interface"
        except Exception as e:
            plugin_health[name] = f"error: {str(e)}"
    
    checks["plugins"] = plugin_health
    
    # Overall health
    overall_healthy = all([
        checks["database"],
        checks["plugins_loaded"],
        checks["event_manager"]
    ])
    
    duration = time.time() - start_time
    
    health_status = {
        "healthy": overall_healthy,
        "timestamp": checks["timestamp"],
        "duration_ms": duration * 1000,
        "checks": checks
    }
    
    status_code = 200 if overall_healthy else 503
    return jsonify(health_status), status_code


@app.route("/event_history")
def event_history():
    return jsonify(event_manager.get_event_history())


@app.route("/plugins/config", methods=["GET"])
def get_plugins_config():
    config = plugin_manager.load_config()
    available_plugins = plugin_manager.get_available_plugins()
    return jsonify(
        {
            "enabled_plugins": config.get("plugins", []),
            "available_plugins": available_plugins,
        }
    )


@app.route("/plugins/config", methods=["POST"])
def save_plugins_config():
    data = request.get_json()
    config = {"plugins": data.get("plugins", [])}
    plugin_manager.save_config(config)
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    plugin_manager.load_plugins(app)
    app.run(host="0.0.0.0", port=80, debug=True, use_reloader=False)
