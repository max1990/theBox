import os, threading
from collections import deque
from flask import Blueprint, render_template, jsonify
from thebox.plugin_interface import PluginInterface
from .config import SilvusConfig
from .parser import parse_lines
from .bearing import to_true_bearing

class SilvusListenerPlugin(PluginInterface):
    def __init__(self,name,event_manager):
        super().__init__(name,event_manager)
        self.cfg=SilvusConfig(replay_path=os.getenv('SILVUS_REPLAY_PATH') or None)
        self._thread=None; self._stop=threading.Event(); self._last_bearings=deque(maxlen=self.cfg.status_buffer_max)
    def load(self):
        if self.cfg.replay_path and os.path.exists(self.cfg.replay_path):
            self._thread=threading.Thread(target=self._run_replay,daemon=True); self._thread.start()
    def unload(self):
        self._stop.set();
        if self._thread: self._thread.join(timeout=2.0)
    def get_blueprint(self):
        bp=Blueprint(self.name,__name__,template_folder='templates')
        @bp.route('/')
        def index(): return render_template('silvus_listener.html')
        @bp.route('/status')
        def status(): return jsonify({'last_bearings':list(self._last_bearings)})
        return bp
    def _emit_bearing(self,rec):
        h=rec.get('heading_deg');
        if h is None: return
        for k in ('aoa1_deg','aoa2_deg'):
            a=rec.get(k)
            if a is None: continue
            brg=to_true_bearing(a,h,self.cfg.zero_axis,self.cfg.positive)
            ev={'time_utc':rec['time_utc'],'freq_mhz':rec['freq_mhz'],'bearing_deg_true':brg,'bearing_error_deg':self.cfg.default_bearing_error_deg,'confidence':self.cfg.default_confidence}
            self.publish('object.sighting.directional',ev,store_in_db=True)
            self._last_bearings.append(ev)
    def _run_replay(self):
        try:
            with open(self.cfg.replay_path,'r',encoding='utf-8') as f:
                for rec in parse_lines(f):
                    if self._stop.is_set(): break
                    self._emit_bearing(rec)
        except Exception: pass
