from flask import Blueprint


def create_testconsole_blueprint(event_manager, plugin_manager):
    bp = Blueprint("testconsole", __name__, url_prefix="/test")

    from .routes import register_routes

    register_routes(bp, event_manager, plugin_manager)
    return bp
