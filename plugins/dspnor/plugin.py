"""
Dspnor Plugin - Main entry point for Dronnur-2D Naval LPI/LPD radar integration
"""

import os
import asyncio
import threading
import socket
import time
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import structlog

from thebox.plugin_interface import PluginInterface
from flask import Blueprint, render_template, jsonify

from .constants import (
    DEFAULT_DISCOVERY_MULTICAST, DEFAULT_DISCOVERY_PORT, DEFAULT_INFO_TCP_PORT,
    DEFAULT_CAT010_PORT, DEFAULT_NMEA_UDP_PORT, DEFAULT_MAX_MSG_RATE_HZ,
    DEFAULT_HEARTBEAT_EXPECTED_SEC, DEFAULT_RECONNECT_BACKOFF
)
from .io_discovery import DiscoveryClient, InfoClient
from .parser_cat010 import CAT010Parser
from .parser_status import StatusParser
from .nmea_ingest import NMEAUDPClient
from .normalizer import DetectionNormalizer
from .control import DspnorController
from .metrics import DspnorMetrics
from .schemas import NormalizedDetection, UnitInfo

logger = structlog.get_logger(__name__)


class DspnorPlugin(PluginInterface):
    """Dspnor Plugin for TheBox - Dronnur-2D Naval LPI/LPD radar integration"""
    
    def __init__(self, event_manager):
        super().__init__(event_manager)
        self.logger = logger.bind(component="dspnor_plugin")
        
        # Load configuration from environment
        self._load_config()
        
        # Initialize components
        self.discovery_client = DiscoveryClient(
            multicast_group=self.discovery_multicast,
            port=self.discovery_port
        )
        self.info_client: Optional[InfoClient] = None
        self.cat010_parser = CAT010Parser()
        self.status_parser = StatusParser()
        self.nmea_client = NMEAUDPClient(
            port=self.nmea_udp_port,
            callback=self._on_nmea_data
        )
        self.normalizer = DetectionNormalizer(
            conf_map=self.conf_map,
            min_conf=self.min_conf,
            max_conf=self.max_conf,
            range_units=self.range_units,
            speed_units=self.speed_units,
            bearing_is_relative=self.bearing_is_relative
        )
        self.controller = DspnorController(
            safe_mode=self.safe_mode,
            unit_serial=self.unit_serial
        )
        self.metrics = DspnorMetrics()
        
        # Runtime state
        self.running = False
        self.discovered_units: Dict[str, UnitInfo] = {}
        self.current_heading: Optional[float] = None
        self.current_position: Optional[tuple] = None
        self.current_velocity: Optional[tuple] = None
        
        # Threading
        self._cat010_thread: Optional[threading.Thread] = None
        self._status_thread: Optional[threading.Thread] = None
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # Rate limiting
        self._last_message_time = 0
        self._message_interval = 1.0 / self.max_msg_rate_hz
    
    def _load_config(self):
        """Load configuration from environment variables"""
        # Enablement & mode
        self.enabled = os.getenv("DSPNOR_ENABLED", "false").lower() == "true"
        self.safe_mode = os.getenv("DSPNOR_SAFE_MODE", "true").lower() == "true"
        
        # Discovery / info
        self.discovery_multicast = os.getenv("DSPNOR_DISCOVERY_MULTICAST", DEFAULT_DISCOVERY_MULTICAST)
        self.discovery_port = int(os.getenv("DSPNOR_DISCOVERY_PORT", str(DEFAULT_DISCOVERY_PORT)))
        self.info_tcp_port = int(os.getenv("DSPNOR_INFO_TCP_PORT", str(DEFAULT_INFO_TCP_PORT)))
        
        # Services
        self.cat010_proto = os.getenv("DSPNOR_CAT010_PROTO", "udp").lower()
        self.cat010_host = os.getenv("DSPNOR_CAT010_HOST", "0.0.0.0")
        self.cat010_port = int(os.getenv("DSPNOR_CAT010_PORT", str(DEFAULT_CAT010_PORT)))
        
        self.status_proto = os.getenv("DSPNOR_STATUS_PROTO", "tcp").lower()
        self.status_host = os.getenv("DSPNOR_STATUS_HOST", "127.0.0.1")
        self.status_port = int(os.getenv("DSPNOR_STATUS_PORT", str(DEFAULT_INFO_TCP_PORT)))
        
        # External heading/GPS
        self.nmea_udp_port = int(os.getenv("DSPNOR_NMEA_UDP_PORT", str(DEFAULT_NMEA_UDP_PORT)))
        
        # Optional INS injection
        self.ins_inject_enabled = os.getenv("DSPNOR_INS_INJECT_ENABLED", "false").lower() == "true"
        self.ins_inject_rate_hz = int(os.getenv("DSPNOR_INS_INJECT_RATE_HZ", "25"))
        
        # Normalization & units
        self.bearing_is_relative = os.getenv("DSPNOR_BEARING_IS_RELATIVE", "false").lower() == "true"
        self.range_units = os.getenv("DSPNOR_RANGE_UNITS", "m").lower()
        self.speed_units = os.getenv("DSPNOR_SPEED_UNITS", "mps").lower()
        self.conf_map = os.getenv("DSPNOR_CONF_MAP", "snr_db:linear:0:30")
        self.min_conf = float(os.getenv("DSPNOR_MIN_CONF", "0.05"))
        self.max_conf = float(os.getenv("DSPNOR_MAX_CONF", "0.99"))
        
        # IO/limits
        self.buffer_bytes = int(os.getenv("DSPNOR_BUFFER_BYTES", "65536"))
        self.connect_timeout_sec = int(os.getenv("DSPNOR_CONNECT_TIMEOUT_SEC", "5"))
        self.reconnect_backoff = [int(x) for x in os.getenv("DSPNOR_RECONNECT_BACKOFF_MS", "500,1000,2000,5000").split(",")]
        self.heartbeat_expected_sec = int(os.getenv("DSPNOR_HEARTBEAT_EXPECTED_SEC", str(DEFAULT_HEARTBEAT_EXPECTED_SEC)))
        self.max_msg_rate_hz = int(os.getenv("DSPNOR_MAX_MSG_RATE_HZ", str(DEFAULT_MAX_MSG_RATE_HZ)))
        
        # Publishing / debug
        self.publish_topic = os.getenv("DSPNOR_PUBLISH_TOPIC", "detections.dspnor")
        self.rebroadcast_udp_port = int(os.getenv("DSPNOR_REBROADCAST_UDP_PORT", "0"))
        
        # Logging / metrics
        self.log_level = os.getenv("DSPNOR_LOG_LEVEL", "INFO")
        self.metrics_port = int(os.getenv("DSPNOR_METRICS_PORT", "0"))
        
        # Dangerous ops
        self.allow_reset = os.getenv("DSPNOR_ALLOW_RESET", "false").lower() == "true"
        self.allow_reboot = os.getenv("DSPNOR_ALLOW_REBOOT", "false").lower() == "true"
        self.unit_serial = os.getenv("DSPNOR_UNIT_SERIAL", "")
        
        self.logger.info("Configuration loaded", 
                        enabled=self.enabled, safe_mode=self.safe_mode,
                        discovery=f"{self.discovery_multicast}:{self.discovery_port}",
                        cat010=f"{self.cat010_proto}://{self.cat010_host}:{self.cat010_port}",
                        nmea_port=self.nmea_udp_port)
    
    def load(self):
        """Load the Dspnor plugin"""
        if not self.enabled:
            self.logger.info("Dspnor plugin disabled via environment")
            return
        
        self.logger.info("Loading Dspnor plugin")
        
        try:
            # Set controller permissions
            self.controller.set_permissions(
                allow_reset=self.allow_reset,
                allow_reboot=self.allow_reboot
            )
            
            # Start discovery
            self.discovery_client.set_callback(self._on_unit_discovered)
            self.discovery_client.start()
            self.metrics.set_connection_status(discovery=True)
            
            # Start NMEA client
            self.nmea_client.start()
            self.metrics.set_connection_status(nmea=True)
            
            # Start background threads
            self.running = True
            self._stop_event.clear()
            
            self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
            self._heartbeat_thread.start()
            
            self.logger.info("Dspnor plugin loaded successfully")
            
        except Exception as e:
            self.logger.error("Failed to load Dspnor plugin", error=str(e))
            self.metrics.record_error(f"Load failed: {str(e)}")
    
    def unload(self):
        """Unload the Dspnor plugin"""
        self.logger.info("Unloading Dspnor plugin")
        
        try:
            self.running = False
            self._stop_event.set()
            
            # Stop discovery
            self.discovery_client.stop()
            self.metrics.set_connection_status(discovery=False)
            
            # Stop NMEA client
            self.nmea_client.stop()
            self.metrics.set_connection_status(nmea=False)
            
            # Disconnect info client
            if self.info_client:
                self.info_client.disconnect()
                self.metrics.set_connection_status(info=False)
            
            # Stop background threads
            if self._heartbeat_thread and self._heartbeat_thread.is_alive():
                self._heartbeat_thread.join(timeout=2.0)
            
            self.logger.info("Dspnor plugin unloaded successfully")
            
        except Exception as e:
            self.logger.error("Error unloading Dspnor plugin", error=str(e))
    
    def _on_unit_discovered(self, unit_info: UnitInfo):
        """Handle discovered unit"""
        self.logger.info("Unit discovered", 
                        unit_name=unit_info.unit_name,
                        serial=unit_info.serial_number,
                        ip=unit_info.ip_address)
        
        self.discovered_units[unit_info.serial_number] = unit_info
        self.metrics.update_discovery_time()
        
        # Connect to info port if not already connected
        if not self.info_client or not self.info_client.socket:
            self._connect_to_unit(unit_info)
    
    def _connect_to_unit(self, unit_info: UnitInfo):
        """Connect to unit info port"""
        try:
            self.info_client = InfoClient(unit_info.ip_address, self.info_tcp_port)
            if self.info_client.connect():
                self.metrics.set_connection_status(info=True)
                self.logger.info("Connected to unit info port", 
                               unit=unit_info.unit_name, ip=unit_info.ip_address)
                
                # Configure services if not in safe mode
                if not self.safe_mode:
                    self._configure_services()
                
                # Start status monitoring
                self._start_status_monitoring()
                
                # Start CAT-010 monitoring
                self._start_cat010_monitoring()
                
            else:
                self.logger.error("Failed to connect to unit info port")
                self.metrics.record_error("Failed to connect to info port")
                
        except Exception as e:
            self.logger.error("Error connecting to unit", error=str(e))
            self.metrics.record_error(f"Connection error: {str(e)}")
    
    def _configure_services(self):
        """Configure unit services"""
        try:
            if not self.info_client:
                return
            
            # Enable CAT-010 UDP
            if self.cat010_proto == "udp":
                self.controller.enable_cat010_udp(self.info_client, self.cat010_host, self.cat010_port)
            
            # Disable CAT-240 video
            self.controller.disable_cat240(self.info_client)
            
            self.logger.info("Services configured")
            
        except Exception as e:
            self.logger.error("Error configuring services", error=str(e))
            self.metrics.record_error(f"Service config error: {str(e)}")
    
    def _start_status_monitoring(self):
        """Start status monitoring thread"""
        if self._status_thread and self._status_thread.is_alive():
            return
        
        self._status_thread = threading.Thread(target=self._status_loop, daemon=True)
        self._status_thread.start()
    
    def _start_cat010_monitoring(self):
        """Start CAT-010 monitoring thread"""
        if self._cat010_thread and self._cat010_thread.is_alive():
            return
        
        self._cat010_thread = threading.Thread(target=self._cat010_loop, daemon=True)
        self._cat010_thread.start()
    
    def _status_loop(self):
        """Status monitoring loop"""
        while self.running and not self._stop_event.is_set():
            try:
                if self.info_client:
                    status_data = self.info_client.get_status()
                    if status_data:
                        self.metrics.update_status_time()
                        self.metrics.increment_messages_ok()
                    else:
                        self.metrics.increment_messages_bad()
                        self.metrics.record_error("No status data received")
                
                time.sleep(self.heartbeat_expected_sec)
                
            except Exception as e:
                self.logger.error("Error in status loop", error=str(e))
                self.metrics.record_error(f"Status loop error: {str(e)}")
                time.sleep(5)
    
    def _cat010_loop(self):
        """CAT-010 monitoring loop"""
        if self.cat010_proto != "udp":
            return
        
        sock = None
        reconnect_delay = 0
        
        while self.running and not self._stop_event.is_set():
            try:
                if not sock:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    sock.bind((self.cat010_host, self.cat010_port))
                    sock.settimeout(1.0)
                    self.metrics.set_connection_status(cat010=True)
                    self.logger.info("CAT-010 UDP listener started", 
                                   host=self.cat010_host, port=self.cat010_port)
                    reconnect_delay = 0
                
                # Receive CAT-010 data
                data, addr = sock.recvfrom(self.buffer_bytes)
                self.metrics.add_cat010_bytes(len(data))
                
                # Rate limiting
                now = time.time()
                if now - self._last_message_time < self._message_interval:
                    self.metrics.increment_overrate_drops()
                    continue
                
                self._last_message_time = now
                
                # Parse CAT-010 track
                start_time = time.time()
                track = self.cat010_parser.parse(data)
                parse_time = (time.time() - start_time) * 1000
                self.metrics.record_parse_time(parse_time)
                
                if track and self.cat010_parser.is_valid_track(track):
                    # Normalize to detection
                    detection = self.normalizer.normalize(
                        track, 
                        current_heading=self.current_heading
                    )
                    
                    if detection:
                        # Publish to TheBox event system
                        self.publish(self.publish_topic, detection.dict(), store_in_db=True)
                        self.metrics.increment_detections_out()
                        self.metrics.increment_messages_ok()
                    else:
                        self.metrics.increment_messages_bad()
                else:
                    self.metrics.increment_messages_bad()
                
            except socket.timeout:
                continue
            except Exception as e:
                self.logger.error("Error in CAT-010 loop", error=str(e))
                self.metrics.record_error(f"CAT-010 loop error: {str(e)}")
                
                # Reconnect with backoff
                if sock:
                    sock.close()
                    sock = None
                    self.metrics.set_connection_status(cat010=False)
                    self.metrics.increment_reconnects()
                
                if reconnect_delay < len(self.reconnect_backoff):
                    delay = self.reconnect_backoff[reconnect_delay]
                    reconnect_delay += 1
                else:
                    delay = self.reconnect_backoff[-1]
                
                time.sleep(delay / 1000.0)
        
        if sock:
            sock.close()
    
    def _on_nmea_data(self, nmea_data):
        """Handle NMEA data"""
        self.metrics.increment_nmea_msgs()
        
        # Update current heading and position
        if nmea_data.heading_deg_true is not None:
            self.current_heading = nmea_data.heading_deg_true
        
        if nmea_data.latitude is not None and nmea_data.longitude is not None:
            self.current_position = (nmea_data.latitude, nmea_data.longitude)
        
        if nmea_data.speed_over_ground is not None and nmea_data.course_over_ground is not None:
            self.current_velocity = (nmea_data.speed_over_ground, nmea_data.course_over_ground)
        
        # Inject to unit if enabled
        if (self.ins_inject_enabled and self.info_client and 
            nmea_data.heading_deg_true is not None and
            nmea_data.latitude is not None and nmea_data.longitude is not None and
            nmea_data.course_over_ground is not None and nmea_data.speed_over_ground is not None):
            
            self.controller.inject_external_ins(
                self.info_client,
                nmea_data.heading_deg_true,
                nmea_data.latitude,
                nmea_data.longitude,
                nmea_data.course_over_ground,
                nmea_data.speed_over_ground
            )
    
    def _heartbeat_loop(self):
        """Heartbeat monitoring loop"""
        while self.running and not self._stop_event.is_set():
            try:
                # Check for stale connections
                if self.metrics.is_discovery_stale():
                    self.logger.warning("Discovery connection stale")
                
                if self.metrics.is_status_stale():
                    self.logger.warning("Status connection stale")
                
                if self.metrics.is_cat010_stale():
                    self.logger.warning("CAT-010 connection stale")
                
                if self.metrics.is_nmea_stale():
                    self.logger.warning("NMEA connection stale")
                
                # Publish heartbeat
                self.publish("dspnor_heartbeat", {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "metrics": self.metrics.get_summary(),
                    "health_status": self.metrics.get_health_status()
                }, store_in_db=False)
                
                time.sleep(10)  # Heartbeat every 10 seconds
                
            except Exception as e:
                self.logger.error("Error in heartbeat loop", error=str(e))
                time.sleep(5)
    
    def get_blueprint(self):
        """Get Flask blueprint for web interface"""
        bp = Blueprint(self.name, __name__, template_folder='templates')
        
        @bp.route('/')
        def index():
            return render_template('dspnor.html')
        
        @bp.route('/status')
        def status():
            return jsonify({
                "enabled": self.enabled,
                "safe_mode": self.safe_mode,
                "running": self.running,
                "discovered_units": {serial: {
                    "unit_name": unit.unit_name,
                    "ip_address": unit.ip_address,
                    "firmware_version": unit.firmware_version,
                    "capabilities": unit.capabilities,
                    "last_seen": unit.last_seen.isoformat()
                } for serial, unit in self.discovered_units.items()},
                "current_heading": self.current_heading,
                "current_position": self.current_position,
                "current_velocity": self.current_velocity,
                "metrics": self.metrics.get_summary(),
                "health_status": self.metrics.get_health_status()
            })
        
        @bp.route('/reset_unit', methods=['POST'])
        def reset_unit():
            from flask import request
            if not self.allow_reset:
                return jsonify({"error": "Reset not allowed"}), 403
            
            unit_ip = request.json.get('unit_ip', '')
            if self.controller.reset_unit(unit_ip):
                return jsonify({"success": True})
            else:
                return jsonify({"error": "Reset failed"}), 500
        
        @bp.route('/reboot_unit', methods=['POST'])
        def reboot_unit():
            from flask import request
            if not self.allow_reboot:
                return jsonify({"error": "Reboot not allowed"}), 403
            
            unit_ip = request.json.get('unit_ip', '')
            if self.controller.reboot_unit(unit_ip):
                return jsonify({"success": True})
            else:
                return jsonify({"error": "Reboot failed"}), 500
        
        return bp
