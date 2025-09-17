# Sensors and Plugins Guide

## Overview

TheBox integrates with multiple sensor types through a plugin architecture. Each sensor has a dedicated plugin that handles data ingestion, processing, and event publishing.

## Sensor Types

### 1. DroneShield DS-X Mk2 (RF Detection)

**Purpose**: RF-based drone detection and classification

**Capabilities**:
- Drone detection using RF signatures
- Classification of drone types
- Signal strength measurement
- Frequency analysis

**Integration**:
- **Protocol**: UDP
- **Port**: Configurable (default: 50001)
- **Data Format**: JSON
- **Update Rate**: ~1 Hz

**Plugin**: `plugins/droneshield_listener/`
- **Main File**: `plugin.py`
- **Templates**: `templates/droneshield.html`

**Configuration**:
```bash
UDP_PORT_DRONESHIELD=50001
DRONESHIELD_ENABLED=true
DRONESHIELD_TIMEOUT=5.0
```

**Data Schema**:
```json
{
  "detection": {
    "id": "uuid",
    "timestamp": "ISO8601",
    "sensor": "droneshield",
    "drone_type": "string",
    "signal_strength": "float",
    "frequency": "float",
    "confidence": "float"
  }
}
```

### 2. Silvus FASST (RF Spectrum Analysis)

**Purpose**: RF spectrum analysis and Angle of Arrival (AoA) estimation

**Capabilities**:
- RF spectrum monitoring
- AoA estimation
- Signal direction finding
- Spectrum analysis

**Integration**:
- **Protocol**: UDP
- **Port**: Configurable (default: 50002)
- **Data Format**: JSON
- **Update Rate**: ~10 Hz

**Plugin**: `plugins/silvus_listener/`
- **Main File**: `plugin.py`
- **Bearing Utils**: `bearing.py`
- **Templates**: `templates/silvus.html`

**Configuration**:
```bash
UDP_PORT_SILVUS=50002
SILVUS_ENABLED=true
SILVUS_TIMEOUT=5.0
SILVUS_BEARING_OFFSET=0.0
```

**Data Schema**:
```json
{
  "detection": {
    "id": "uuid",
    "timestamp": "ISO8601",
    "sensor": "silvus",
    "bearing": "float (degrees)",
    "elevation": "float (degrees)",
    "signal_strength": "float",
    "frequency": "float",
    "confidence": "float"
  }
}
```

**Bearing Normalization**:
- All bearings normalized to bow-relative (0°/0 rad)
- Uses `to_true_bearing()` function
- Accounts for vessel heading and bearing offset

### 3. Trakka TC-300 (EO/IR Camera)

**Purpose**: Electro-Optical and Infrared camera control and tracking

**Capabilities**:
- Camera control and positioning
- EO/IR image capture
- Target tracking
- Pan/tilt control

**Integration**:
- **Protocol**: TCP
- **Host**: Configurable (default: 192.168.1.100)
- **Port**: Configurable (default: 8080)
- **Data Format**: JSON
- **Update Rate**: On-demand

**Plugin**: `plugins/trakka_control/`
- **Main File**: `plugin.py`
- **TCP Sender**: `tcp_sender.py`
- **State Machine**: `trakka_rx_statemachine.py`
- **Templates**: `templates/trakka.html`

**Configuration**:
```bash
TCP_HOST_TRAKKA=192.168.1.100
TCP_PORT_TRAKKA=8080
TRAKKA_ENABLED=true
TRAKKA_TIMEOUT=10.0
TRAKKA_DETECTION_MODE=ours
CAMERA_CONNECTED=true
```

**Data Schema**:
```json
{
  "command": {
    "id": "uuid",
    "timestamp": "ISO8601",
    "sensor": "trakka",
    "action": "slew_to_bearing",
    "bearing": "float (degrees)",
    "elevation": "float (degrees)",
    "status": "string"
  }
}
```

**Bearing Normalization**:
- All bearing commands normalized to [0, 360) degrees
- Uses `normalize_bearing_deg()` function
- Ensures consistent bearing format

### 4. MARA Spotter (Multi-Sensor Detection)

**Purpose**: Multi-sensor detection and fusion (EO/IR/Acoustic)

**Capabilities**:
- EO detection and classification
- IR detection and classification
- Acoustic detection and classification
- Multi-sensor fusion
- Target tracking

**Integration**:
- **Protocol**: UDP
- **Port**: Configurable (default: 50003)
- **Data Format**: JSON
- **Update Rate**: ~5 Hz

**Plugin**: `plugins/mara/`
- **Main File**: `plugin.py`
- **Parser**: `parser.py`
- **Models**: `models.py`
- **Templates**: `templates/mara.html`

**Configuration**:
```bash
UDP_PORT_MARA=50003
MARA_ENABLED=true
MARA_TIMEOUT=5.0
MARA_FUSION_MODE=weighted
```

**Data Schema**:
```json
{
  "detection": {
    "id": "uuid",
    "timestamp": "ISO8601",
    "sensor": "mara",
    "detection_type": "eo|ir|acoustic",
    "bearing": "float (degrees)",
    "elevation": "float (degrees)",
    "classification": "string",
    "confidence": "float"
  }
}
```

### 5. Dspnor Dronnur 2D (LPI/LPD Radar)

**Purpose**: Low Probability of Intercept/Low Probability of Detection radar

**Capabilities**:
- Radar detection and tracking
- LPI/LPD operation
- Range and bearing estimation
- Target classification

**Integration**:
- **Protocol**: UDP
- **Port**: Configurable (default: 50004)
- **Data Format**: JSON
- **Update Rate**: ~2 Hz

**Plugin**: `plugins/dspnor/`
- **Main File**: `plugin.py`
- **Parser**: `parser_cat010.py`
- **Normalizer**: `normalizer.py`
- **Templates**: `templates/dspnor.html`

**Configuration**:
```bash
UDP_PORT_DSPNOR=50004
DSPNOR_ENABLED=true
DSPNOR_TIMEOUT=5.0
DSPNOR_RANGE_MODE=radar
```

**Data Schema**:
```json
{
  "detection": {
    "id": "uuid",
    "timestamp": "ISO8601",
    "sensor": "dspnor",
    "bearing": "float (degrees)",
    "range": "float (meters)",
    "velocity": "float (m/s)",
    "classification": "string",
    "confidence": "float"
  }
}
```

## Processing Plugins

### 1. Confidence Plugin

**Purpose**: Detection confidence fusion and assessment

**Capabilities**:
- Bayesian log-odds fusion
- Hysteresis to prevent oscillation
- Weighted fusion based on sensor reliability
- Temporal smoothing

**Plugin**: `plugins/confidence/`
- **Main File**: `plugin.py`
- **Logic**: `confidence_plugin.py`

**Configuration**:
```bash
CONFIDENCE_ENABLED=true
CONFIDENCE_THRESHOLD=0.7
CONFIDENCE_HYSTERESIS=0.1
CONFIDENCE_FUSION_MODE=bayesian
```

**Data Schema**:
```json
{
  "confidence_update": {
    "id": "uuid",
    "timestamp": "ISO8601",
    "detection_id": "uuid",
    "confidence": "float (0-1)",
    "sources": ["sensor1", "sensor2"],
    "fusion_method": "bayesian"
  }
}
```

### 2. Range Plugin

**Purpose**: Range estimation and tracking

**Capabilities**:
- Multiple range estimation methods
- Inverse-variance fusion
- EWMA smoothing
- Range validation

**Plugin**: `plugins/range/`
- **Main File**: `plugin.py`
- **Logic**: `range_plugin.py`

**Configuration**:
```bash
RANGE_ENABLED=true
RANGE_ESTIMATION_MODE=fusion
RANGE_FUSION_WEIGHTS=auto
RANGE_SMOOTHING_FACTOR=0.1
```

**Data Schema**:
```json
{
  "range_estimate": {
    "id": "uuid",
    "timestamp": "ISO8601",
    "detection_id": "uuid",
    "range": "float (meters)",
    "method": "fixed|rf|eo|ir|acoustic|fusion",
    "confidence": "float (0-1)"
  }
}
```

### 3. Vision Plugin

**Purpose**: Computer vision processing and analysis

**Capabilities**:
- Image processing and analysis
- Object detection and classification
- Feature extraction
- Image enhancement

**Plugin**: `plugins/vision/`
- **Main File**: `plugin.py`
- **Logic**: `vision_plugin.py`

**Configuration**:
```bash
VISION_ENABLED=true
VISION_PROCESSING_MODE=gpu
VISION_MODEL_PATH=models/
VISION_CONFIDENCE_THRESHOLD=0.5
```

**Data Schema**:
```json
{
  "vision_result": {
    "id": "uuid",
    "timestamp": "ISO8601",
    "image_id": "uuid",
    "detections": [
      {
        "class": "string",
        "confidence": "float (0-1)",
        "bbox": [x1, y1, x2, y2],
        "center": [x, y]
      }
    ]
  }
}
```

## Plugin Architecture

### Plugin Interface

All plugins inherit from `PluginInterface`:

```python
class PluginInterface:
    def __init__(self, event_manager):
        self.event_manager = event_manager
    
    def load(self):
        """Load plugin resources"""
        pass
    
    def unload(self):
        """Unload plugin resources"""
        pass
    
    def get_blueprint(self):
        """Return Flask blueprint for web interface"""
        return None
```

### Event System

Plugins communicate through events:

```python
# Publish event
self.event_manager.publish("detection", {
    "id": "uuid",
    "sensor": "droneshield",
    "data": {...}
})

# Subscribe to event
self.event_manager.subscribe("detection", self.handle_detection)
```

### Configuration

Plugins use environment variables for configuration:

```python
import os

class MyPlugin(PluginInterface):
    def __init__(self, event_manager):
        super().__init__(event_manager)
        self.port = int(os.getenv("UDP_PORT_MY_SENSOR", "50000"))
        self.enabled = os.getenv("MY_SENSOR_ENABLED", "true").lower() == "true"
```

## Data Flow

### Detection Processing Pipeline

```
Sensor ──Raw Data──► Plugin ──Parse──► Normalize ──Event──► Event Manager
  │                    │         │                    │
  │                    ▼         ▼                    ▼
  │              ┌─────────┐ ┌─────────┐      ┌─────────────┐
  │              │  Parse  │ │ Bearing │      │   Event     │
  │              │  Data   │ │ Normalize│     │  Publisher  │
  │              └─────────┘ └─────────┘      └─────────────┘
  │                                                      │
  └──────────────────────────────────────────────────────┘
```

### Event Processing

```
Event Manager ──Event──► Processing Plugins ──Process──► Fusion ──Result
     │                    │                    │           │
     │                    ▼                    ▼           ▼
     │              ┌─────────────┐      ┌─────────┐ ┌─────────┐
     │              │ Confidence  │      │ Range   │ │ Vision  │
     │              │ Plugin      │      │ Plugin  │ │ Plugin  │
     │              └─────────────┘      └─────────┘ └─────────┘
     │                                                      │
     └──────────────────────────────────────────────────────┘
```

## Testing

### Plugin Testing

Each plugin has dedicated tests:

```bash
# Test specific plugin
python scripts/run_tests.py --suite plugins --path tests/plugins/test_droneshield.py

# Test all plugins
python scripts/run_tests.py --suite plugins
```

### Integration Testing

Test plugin interactions:

```bash
# Test plugin communication
python scripts/run_tests.py --suite integration
```

### Validation

Validate plugin conformance:

```bash
# Validate all plugins
python scripts/validate_plugin_conformance.py

# Validate specific plugin
python scripts/validate_plugin_conformance.py --plugin droneshield
```

## Troubleshooting

### Common Issues

1. **Plugin Not Loading**
   - Check plugin dependencies
   - Verify configuration
   - Check logs for errors

2. **Sensor Connection Issues**
   - Verify network configuration
   - Check firewall settings
   - Test network connectivity

3. **Data Processing Issues**
   - Check data format
   - Verify schema validation
   - Check processing logic

4. **Performance Issues**
   - Monitor resource usage
   - Check processing latency
   - Optimize configuration

### Debug Commands

```bash
# Check plugin status
python scripts/health_check.py

# Validate configuration
python scripts/validate_plugin_conformance.py

# Run smoke test
python scripts/smoke_test.py

# Check logs
tail -f logs/thebox.log
```

## Best Practices

### Plugin Development

1. **Use Standard Interfaces**: Inherit from `PluginInterface`
2. **Handle Errors Gracefully**: Implement proper error handling
3. **Use Structured Logging**: Log important events and errors
4. **Validate Input Data**: Check data format and ranges
5. **Normalize Bearings**: Use bearing normalization utilities
6. **Publish Events**: Use event system for communication
7. **Handle Configuration**: Use environment variables
8. **Test Thoroughly**: Write comprehensive tests

### Configuration

1. **Use Environment Variables**: For all configuration
2. **Provide Defaults**: Set reasonable default values
3. **Validate Input**: Check configuration values
4. **Document Settings**: Document all configuration options
5. **Use Schemas**: Use JSON Schema for validation

### Performance

1. **Optimize Processing**: Minimize processing time
2. **Use Async I/O**: For network operations
3. **Cache Data**: Cache frequently used data
4. **Monitor Resources**: Track resource usage
5. **Handle Load**: Implement proper load handling
