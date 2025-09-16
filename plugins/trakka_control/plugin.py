from flask import Blueprint, jsonify
import os
from thebox.plugin_interface import PluginInterface


class TrakkaControlPlugin(PluginInterface):
    def __init__(self, event_manager):
        super().__init__(event_manager)
        self._mode = os.getenv("TRAKKA_DETECTION_MODE", "ours").strip().lower()
        self._camera_connected = str(os.getenv("CAMERA_CONNECTED", "false")).lower() in {"1","true","yes","on"}
        self._builtin_alive = False

    # optional callbacks from config reload
    def on_mode_changed(self, mode: str):
        self._mode = mode

    # external control used by Test Console
    def slew_to_bearing(self, bearing_deg: float) -> None:
        # Here you would send TCP to Trakka; we keep a no-op stub
        self.event_manager.db.set("trakka.last_slew_deg", float(bearing_deg))

    def load(self):
        pass

    def unload(self):
        pass

    def get_blueprint(self):
        bp = Blueprint(self.name, __name__, template_folder='templates')

        @bp.get("/status")
        def status():
            return jsonify({
                "mode": self._mode,
                "camera_connected": self._camera_connected,
                "builtin_detector_alive": self._builtin_alive,
            })

        return bp


