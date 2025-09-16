from flask import Blueprint


def create_settings_blueprint(event_manager):
    bp = Blueprint("settings", __name__)

    from .routes import register_routes
    register_routes(bp, event_manager)
    return bp


