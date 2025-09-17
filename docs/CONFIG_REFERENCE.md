# TheBox Configuration Reference

## Overview

TheBox uses environment variables for configuration. All configuration is loaded from `env/.thebox.env` at startup and can be overridden by system environment variables.

## Environment Variables by Category

### Core System Configuration

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `SECRET_KEY` | string | `"dev-key-change-in-production"` | No | Flask secret key for sessions |
| `THEBOX_WEB_HOST` | string | `"0.0.0.0"` | No | Web interface bind address |
| `THEBOX_WEB_PORT` | int | `80` | No | Web interface port |
| `THEBOX_TALKER_ID` | string | `"XA"` | No | NMEA talker ID for SeaCross |
| `DB_PATH` | string | `"thebox_mvp.sqlite"` | No | Database file path |

### Bearing and Orientation

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `BOW_ZERO_DEG` | float | `0.0` | No | Global bow zero offset in degrees |
| `DRONESHIELD_BEARING_OFFSET_DEG` | float | `0.0` | No | DroneShield bearing offset |
| `TRAKKA_BEARING_OFFSET_DEG` | float | `0.0` | No | Trakka bearing offset |
| `VISION_BEARING_OFFSET_DEG` | float | `0.0` | No | Vision bearing offset |
| `ACOUSTIC_BEARING_OFFSET_DEG` | float | `0.0` | No | Acoustic bearing offset |

### DroneShield Configuration

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `DRONESHIELD_INPUT_FILE` | string | `"./data/DroneShield_Detections.txt"` | No | Input file for replay |
| `DRONESHIELD_UDP_PORT` | int | `56000` | No | UDP port for DroneShield data |
| `REPLAY_INTERVAL_MS` | int | `400` | No | Replay interval in milliseconds |

### Silvus FASST Configuration

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `SILVUS_UDP_HOST` | string | `"0.0.0.0"` | No | UDP bind address |
| `SILVUS_UDP_PORT` | int | `50051` | No | UDP port for Silvus data |
| `SILVUS_UDP_MODE` | string | `"text"` | No | UDP mode: text or protobuf |
| `SILVUS_REPLAY_PATH` | string | `null` | No | Path to replay file |

### MARA Spotter Configuration

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `MARA_ENABLE` | bool | `true` | No | Enable MARA plugin |
| `MARA_INPUT_MODE` | string | `"udp"` | No | Input mode: udp, tcp, or serial |
| `MARA_UDP_HOST` | string | `"0.0.0.0"` | No | UDP bind address |
| `MARA_UDP_PORT` | int | `8787` | No | UDP port for MARA data |
| `MARA_TCP_HOST` | string | `"127.0.0.1"` | No | TCP server address |
| `MARA_TCP_PORT` | int | `9000` | No | TCP server port |
| `MARA_SERIAL_PORT` | string | `"COM5"` | No | Serial port (Windows: COM5, Linux: /dev/ttyUSB0) |
| `MARA_BAUD` | int | `115200` | No | Serial baud rate |
| `MARA_HEARTBEAT_SEC` | int | `10` | No | Heartbeat interval in seconds |
| `MARA_MAX_QUEUE` | int | `10000` | No | Maximum message queue size |

### Dspnor Dronnur Configuration

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `DSPNOR_ENABLED` | bool | `false` | No | Enable Dspnor plugin |
| `DSPNOR_SAFE_MODE` | bool | `true` | No | Enable safe mode |
| `DSPNOR_DISCOVERY_MULTICAST` | string | `"227.228.229.230"` | No | Discovery multicast address |
| `DSPNOR_DISCOVERY_PORT` | int | `59368` | No | Discovery multicast port |
| `DSPNOR_INFO_TCP_PORT` | int | `59623` | No | Info TCP port |
| `DSPNOR_CAT010_PROTO` | string | `"udp"` | No | CAT010 protocol |
| `DSPNOR_CAT010_HOST` | string | `"0.0.0.0"` | No | CAT010 host |
| `DSPNOR_CAT010_PORT` | int | `4010` | No | CAT010 port |
| `DSPNOR_STATUS_PROTO` | string | `"tcp"` | No | Status protocol |
| `DSPNOR_STATUS_HOST` | string | `"127.0.0.1"` | No | Status host |
| `DSPNOR_STATUS_PORT` | int | `59623` | No | Status port |
| `DSPNOR_NMEA_UDP_PORT` | int | `60000` | No | NMEA UDP port |
| `DSPNOR_INS_INJECT_ENABLED` | bool | `false` | No | Enable INS injection |
| `DSPNOR_INS_INJECT_RATE_HZ` | int | `25` | No | INS injection rate |
| `DSPNOR_BEARING_IS_RELATIVE` | bool | `false` | No | Bearings are relative to bow |
| `DSPNOR_RANGE_UNITS` | string | `"m"` | No | Range units (m or km) |
| `DSPNOR_SPEED_UNITS` | string | `"mps"` | No | Speed units (mps or kts) |
| `DSPNOR_CONF_MAP` | string | `"snr_db:linear:0:30"` | No | Confidence mapping |
| `DSPNOR_MIN_CONF` | float | `0.05` | No | Minimum confidence |
| `DSPNOR_MAX_CONF` | float | `0.99` | No | Maximum confidence |
| `DSPNOR_BUFFER_BYTES` | int | `65536` | No | Buffer size in bytes |
| `DSPNOR_CONNECT_TIMEOUT_SEC` | int | `5` | No | Connection timeout |
| `DSPNOR_MAX_MSG_RATE_HZ` | int | `200` | No | Maximum message rate |
| `DSPNOR_PUBLISH_TOPIC` | string | `"detections.dspnor"` | No | Publish topic |
| `DSPNOR_REBROADCAST_UDP_PORT` | int | `0` | No | Rebroadcast UDP port |
| `DSPNOR_LOG_LEVEL` | string | `"INFO"` | No | Log level |
| `DSPNOR_METRICS_PORT` | int | `0` | No | Metrics port |
| `DSPNOR_ALLOW_RESET` | bool | `false` | No | Allow reset commands |
| `DSPNOR_ALLOW_REBOOT` | bool | `false` | No | Allow reboot commands |
| `DSPNOR_UNIT_SERIAL` | string | `""` | No | Unit serial number |

### Trakka TC-300 Configuration

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `TRAKKA_DETECTION_MODE` | string | `"ours"` | No | Detection mode: builtin, none, ours |
| `CAMERA_CONNECTED` | bool | `false` | No | Camera connection status |

### Vision Configuration

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `VISION_BACKEND` | string | `"cpu"` | No | Vision backend: onnxruntime, cpu |
| `VISION_MODEL_PATH` | string | `""` | No | Path to vision model file |
| `VISION_INPUT_RES` | int | `640` | No | Vision input resolution |
| `VISION_ROI_HALF_DEG` | float | `15.0` | No | Vision ROI half-width in degrees |
| `VISION_FRAME_SKIP` | int | `2` | No | Frames to skip between analysis |
| `VISION_N_CONSEC_FOR_TRUE` | int | `3` | No | Consecutive frames required for positive detection |
| `VISION_LATENCY_MS` | int | `5000` | No | Vision processing latency in milliseconds |
| `VISION_MAX_DWELL_MS` | int | `7000` | No | Maximum dwell time in milliseconds |
| `VISION_SWEEP_STEP_DEG` | float | `12.0` | No | Sweep step in degrees |
| `VISION_PRIORITY` | string | `"balanced"` | No | Vision priority mode: EOfirst, IRfirst, balanced |
| `VISION_VERDICT_DEFAULT` | bool | `true` | No | Default vision verdict |
| `VISION_LABEL_DEFAULT` | string | `"Object"` | No | Default vision label |

### Confidence and Fusion

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `CONFIDENCE_BASE` | float | `0.75` | No | Base confidence level |
| `CONFIDENCE_TRUE` | float | `1.0` | No | True detection confidence |
| `CONFIDENCE_FALSE` | float | `0.5` | No | False detection confidence |
| `CONF_FUSION_METHOD` | string | `"bayes"` | No | Confidence fusion method |
| `WEIGHT_RF` | float | `0.6` | No | RF weight for fusion |
| `WEIGHT_VISION` | float | `0.4` | No | Vision weight for fusion |
| `WEIGHT_IR` | float | `0.4` | No | IR weight for fusion |
| `WEIGHT_ACOUSTIC` | float | `0.25` | No | Acoustic weight for fusion |
| `CONF_HYSTERESIS` | float | `0.05` | No | Confidence hysteresis threshold |

### Range Estimation

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `RANGE_MODE` | string | `"FIXED"` | No | Range estimation mode: RF, EO, IR, ACOUSTIC, HYBRID, FIXED |
| `RANGE_FIXED_KM` | float | `2.0` | No | Fixed range in kilometers |
| `RANGE_RSSI_REF_DBM` | float | `-50.0` | No | RSSI reference in dBm |
| `RANGE_RSSI_REF_KM` | float | `2.0` | No | RSSI reference distance in km |
| `RANGE_MIN_KM` | float | `0.1` | No | Minimum range in kilometers |
| `RANGE_MAX_KM` | float | `8.0` | No | Maximum range in kilometers |
| `RANGE_EWMA_ALPHA` | float | `0.4` | No | EWMA smoothing factor |

### Field of View Settings

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `EO_FOV_WIDE_DEG` | float | `54.0` | No | EO wide FOV in degrees |
| `EO_FOV_NARROW_DEG` | float | `2.0` | No | EO narrow FOV in degrees |
| `IR_FOV_WIDE_DEG` | float | `27.0` | No | IR wide FOV in degrees |
| `IR_FOV_NARROW_DEG` | float | `1.3` | No | IR narrow FOV in degrees |

### SeaCross Integration

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `SEACROSS_HOST` | string | `"127.0.0.1"` | No | SeaCross host IP |
| `SEACROSS_PORT` | int | `2000` | No | SeaCross port |
| `THEBOX_BROADCAST_IP` | string | `"192.168.0.255"` | No | Broadcast IP for SeaCross |
| `THEBOX_BROADCAST_PORT` | int | `62000` | No | Broadcast port for SeaCross |

### Synthetic Range Estimation

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `THEBOX_MIN_SYNTH_RANGE_M` | float | `150` | No | Minimum synthetic range in meters |
| `THEBOX_MAX_SYNTH_RANGE_M` | float | `1500` | No | Maximum synthetic range in meters |
| `THEBOX_DEFAULT_SYNTH_RANGE_M` | float | `600` | No | Default synthetic range in meters |
| `THEBOX_SYNTH_SMOOTHING_ALPHA` | float | `0.30` | No | Synthetic range smoothing factor |
| `THEBOX_SYNTH_MIN_DIST_ERR_M` | float | `150` | No | Minimum distance error in meters |
| `THEBOX_SYNTH_DIST_ERR_FRAC` | float | `0.30` | No | Distance error fraction |
| `THEBOX_SYNTH_DEFAULT_BRG_ERR` | float | `5.0` | No | Default bearing error in degrees |
| `THEBOX_SYNTH_DEFAULT_ALT_M` | float | `0.0` | No | Default altitude in meters |
| `THEBOX_SYNTH_DEFAULT_ALT_ERR` | float | `20.0` | No | Default altitude error in meters |

### State Persistence

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `THEBOX_STATE_PATH` | string | `"data/state.json"` | No | State file path |
| `THEBOX_STATE_SAVE_EVERY_SEC` | int | `3` | No | State save interval in seconds |

### Test and Development

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `TEST_DRY_RUN` | bool | `true` | No | Enable dry run mode for testing |
| `TEST_DEFAULT_BEARING_DEG` | float | `45.0` | No | Default test bearing |
| `TEST_DEFAULT_RSSI_DBM` | float | `-72` | No | Default test RSSI |
| `TEST_DEFAULT_NAME` | string | `"DJI AUT XIA"` | No | Default test drone name |
| `TEST_DEFAULT_PROTOCOL` | string | `"FHSS"` | No | Default test protocol |

### Settings Protection

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `SETTINGS_PROTECT` | bool | `false` | No | Enable settings protection |
| `SETTINGS_PASSWORD` | string | `""` | No | Settings password |

## Configuration Loading

### Environment File Location
- Primary: `env/.thebox.env`
- Fallback: `env/.thebox.env.example`

### Loading Order
1. Load from `env/.thebox.env` if it exists
2. Fall back to `env/.thebox.env.example` if primary doesn't exist
3. Override with system environment variables
4. Apply default values for missing variables

### Hot Reload
Configuration can be reloaded at runtime through the web interface:
- Navigate to `/settings`
- Modify values
- Click "Save" to apply changes
- Changes are applied immediately without restart

## Validation

### Type Validation
- **Boolean**: `"true"`, `"1"`, `"yes"`, `"on"` → `True`; `"false"`, `"0"`, `"no"`, `"off"` → `False`
- **Integer**: Parsed as `int()`, falls back to default on error
- **Float**: Parsed as `float()`, falls back to default on error
- **String**: Used as-is, no validation

### Range Validation
- **Ports**: 1-65535
- **Angles**: 0-360 degrees (normalized automatically)
- **Confidence**: 0.0-1.0
- **Ranges**: Positive values only

### Required Variables
Currently, no environment variables are strictly required. All have defaults.

## Security Considerations

### Sensitive Variables
- `SECRET_KEY`: Should be changed in production
- `SETTINGS_PASSWORD`: Required if `SETTINGS_PROTECT=true`
- `DSPNOR_UNIT_SERIAL`: May contain sensitive hardware information

### Best Practices
1. **Never commit** `.thebox.env` to version control
2. **Use strong passwords** for settings protection
3. **Rotate secrets** regularly in production
4. **Use environment-specific** configuration files
5. **Validate all inputs** before saving

## Troubleshooting

### Common Issues
1. **Configuration not loading**: Check file permissions and path
2. **Type errors**: Verify numeric values are valid
3. **Hot reload not working**: Check web interface access
4. **Settings protection**: Ensure password is set if enabled

### Debug Mode
Set `THEBOX_LOG_LEVEL=DEBUG` for detailed configuration loading logs.

## Examples

### Minimal Configuration
```bash
# Core settings
SECRET_KEY=your-secret-key-here
THEBOX_WEB_HOST=0.0.0.0
THEBOX_WEB_PORT=80

# Sensor enablement
MARA_ENABLE=true
DSPNOR_ENABLED=true
CAMERA_CONNECTED=true

# Bearing offsets
BOW_ZERO_DEG=0.0
DRONESHIELD_BEARING_OFFSET_DEG=0.0
TRAKKA_BEARING_OFFSET_DEG=0.0
```

### Production Configuration
```bash
# Security
SECRET_KEY=your-very-secure-secret-key
SETTINGS_PROTECT=true
SETTINGS_PASSWORD=your-secure-password

# Network
THEBOX_WEB_HOST=0.0.0.0
THEBOX_WEB_PORT=80
SEACROSS_HOST=192.168.1.100
SEACROSS_PORT=2000

# Sensors
MARA_ENABLE=true
DSPNOR_ENABLED=true
CAMERA_CONNECTED=true

# Performance
VISION_FRAME_SKIP=1
VISION_N_CONSEC_FOR_TRUE=3
RANGE_EWMA_ALPHA=0.4
```
