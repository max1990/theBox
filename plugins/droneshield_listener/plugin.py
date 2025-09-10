import socket
import threading
import json
from collections import deque
from datetime import datetime, timezone

from flask import Blueprint, render_template, request, jsonify
from thebox.plugin_interface import PluginInterface

class DroneShieldListenerPlugin(PluginInterface):
    def __init__(self, event_manager):
        super().__init__(event_manager)
        self.port = 8888
        self.listener_thread = None
        self.stop_event = threading.Event()
        self.received_events = deque(maxlen=100)
        self.listener_status = "stopped"
        self.lock = threading.Lock()

    def load(self):
        print("DroneShield Listener Plugin Loaded")
        self.start_listener()

    def unload(self):
        print("DroneShield Listener Plugin Unloaded")
        self.stop_listener()

    def start_listener(self):
        if self.listener_thread is None or not self.listener_thread.is_alive():
            self.stop_event.clear()
            self.listener_thread = threading.Thread(target=self.udp_listener)
            self.listener_thread.daemon = True
            self.listener_thread.start()
            self.listener_status = "running"
            print(f"DroneShield listener started on port {self.port}")

    def stop_listener(self):
        if self.listener_thread and self.listener_thread.is_alive():
            self.stop_event.set()
            # Sending a dummy packet to unblock the socket
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                    s.sendto(b'stop', ('127.0.0.1', self.port))
            except Exception as e:
                print(f"Could not send stop signal to listener: {e}")
            self.listener_thread.join(timeout=2)
            self.listener_status = "stopped"
            print("DroneShield listener stopped.")

    def udp_listener(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(('0.0.0.0', self.port))
            sock.settimeout(1.0)
        except OSError as e:
            print(f"Error binding to port {self.port}: {e}")
            self.listener_status = f"Error: {e}"
            return

        while not self.stop_event.is_set():
            try:
                data, addr = sock.recvfrom(65507)
                if self.stop_event.is_set():
                    break
                text = data.decode("utf-8", errors="ignore")
                msg = json.loads(text)

                with self.lock:
                    self.received_events.append({
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "source_ip": addr[0],
                        "data": msg
                    })
                
                self.publish("droneshield_detection", {"detection": msg})
                # ALSO keep a rolling list in DB:
                msgs = self.event_manager.db.get("droneshield_messages") or []
                msgs.append(msg)
                self.event_manager.db.set("droneshield_messages", msgs[-100:])  # ring buffer of 100

            except socket.timeout:
                continue
            except json.JSONDecodeError:
                print("Received non-JSON UDP packet.")
            except Exception as e:
                print(f"Error in DroneShield listener: {e}")
        
        sock.close()

    def get_blueprint(self):
        bp = Blueprint(self.name, __name__, template_folder='templates')

        @bp.route('/')
        def index():
            return render_template('droneshield_listener_plugin.html')

        @bp.route('/status')
        def status():
            with self.lock:
                return jsonify({
                    "listener_status": self.listener_status,
                    "port": self.port,
                    "events": list(self.received_events)
                })

        @bp.route('/settings', methods=['POST'])
        def update_settings():
            data = request.get_json()
            new_port = data.get('port')
            if new_port:
                try:
                    self.port = int(new_port)
                    self.stop_listener()
                    self.start_listener()
                    return jsonify({"status": "ok", "message": f"Port updated to {self.port}. Listener restarted."})
                except ValueError:
                    return jsonify({"status": "error", "message": "Invalid port number."}), 400
            return jsonify({"status": "no_change"})

        @bp.route('/create_fake_event', methods=['POST'])
        def create_fake_event():
            fake_event_data = request.get_json()
            if not fake_event_data:
                return jsonify({"status": "error", "message": "No data provided."}), 400
            
            self.publish("droneshield_detection", {"detection": fake_event_data})
            
            with self.lock:
                self.received_events.append({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "source_ip": "FakeEvent",
                    "data": fake_event_data
                })
            
            return jsonify({"status": "ok", "message": "Fake event published successfully."})

        return bp
