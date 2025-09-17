from datetime import datetime, timezone

from flask import Blueprint, abort, redirect, render_template, request, url_for

from thebox.plugin_interface import PluginInterface


class LabelsUIPlugin(PluginInterface):
    def load(self):
        pass

    def unload(self):
        pass

    def get_blueprint(self):
        bp = Blueprint(self.name, __name__, template_folder="templates")

        def _tracks_dict():
            tracks = self.event_manager.db.get("tracks")
            return tracks if isinstance(tracks, dict) else {}

        @bp.get("/")
        def index():
            tracks = _tracks_dict()
            items = []
            for tid, meta in tracks.items():
                if not isinstance(meta, dict):
                    meta = {}
                items.append(
                    {
                        "tid": tid,
                        "affiliation": meta.get("affiliation") or "UNKNOWN",
                        "last_update": meta.get("last_update"),
                    }
                )
            items.sort(key=lambda x: x.get("last_update") or "", reverse=True)
            return render_template("labels_ui_plugin.html", mode="index", tracks=items)

        @bp.get("/drone/<tid>")
        def view_track(tid):
            meta = _tracks_dict().get(tid) or {}
            if not meta:
                now_iso = datetime.now(timezone.utc).isoformat()
                self.event_manager.db.set(f"tracks.{tid}.affiliation", "UNKNOWN")
                self.event_manager.db.set(f"tracks.{tid}.last_update", now_iso)
                meta = self.event_manager.db.get(f"tracks.{tid}") or {}

            dets = self.event_manager.db.get("droneshield_messages") or []
            dets = list(reversed(dets[-50:]))

            return render_template(
                "labels_ui_plugin.html", mode="view", tid=tid, track=meta, dets=dets
            )

        @bp.post("/api/label/<tid>")
        def set_label(tid):
            label = request.form.get("label")
            if label not in ("FRIENDLY", "ENEMY", "NOT_DRONE"):
                abort(400, description="Invalid label")
            now_iso = datetime.now(timezone.utc).isoformat()
            self.event_manager.db.set(f"tracks.{tid}.affiliation", label)
            self.event_manager.db.set(f"tracks.{tid}.last_update", now_iso)
            # Optional: notify sender to re-emit CLS
            # self.event_manager.publish("track_label_changed", {"uuid": tid, "affiliation": label})
            return redirect(url_for(f"{self.name}.view_track", tid=tid), code=303)

        return bp
