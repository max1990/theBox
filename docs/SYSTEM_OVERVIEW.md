# TheBox System Overview

## Introduction

TheBox is a comprehensive drone detection and tracking system designed for maritime and land-based applications. It integrates multiple sensor types to provide real-time detection, tracking, and threat assessment capabilities.

## Architecture

### Core Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web UI        │    │   Flask App     │    │   Plugin        │
│   (Settings)    │◄──►│   (Main)        │◄──►│   Manager       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                       │
                                ▼                       ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │   Event         │    │   DroneDB       │
                       │   Manager       │◄──►│   (Database)    │
                       └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   Sensor        │
                       │   Plugins       │
                       └─────────────────┘
```

### Plugin System

TheBox uses a modular plugin architecture where each sensor type is implemented as a plugin:

- **DroneShield Plugin**: RF detection and analysis
- **Silvus Plugin**: RF spectrum analysis and AoA
- **Trakka Plugin**: EO/IR camera control and tracking
- **MARA Plugin**: Multi-sensor detection and fusion
- **Dspnor Plugin**: LPI/LPD radar processing
- **Confidence Plugin**: Detection confidence fusion
- **Range Plugin**: Range estimation and tracking
- **Vision Plugin**: Computer vision processing

### Event System

The event system enables loose coupling between plugins:

```
Plugin A ──publish──► Event Manager ──subscribe──► Plugin B
    │                                           │
    └───────────subscribe◄──────────────────────┘
```

Events flow through the system asynchronously, allowing plugins to:
- Publish detection events
- Subscribe to specific event types
- Process events independently
- Maintain system state

## Sensor Integration

### Supported Sensors

1. **DroneShield DS-X Mk2**
   - Type: RF detection
   - Protocol: UDP
   - Capabilities: Drone detection, classification
   - Integration: Direct UDP listener

2. **Silvus FASST**
   - Type: RF spectrum analysis
   - Protocol: UDP
   - Capabilities: AoA estimation, spectrum analysis
   - Integration: UDP listener with bearing normalization

3. **Trakka TC-300**
   - Type: EO/IR camera
   - Protocol: TCP
   - Capabilities: Camera control, tracking
   - Integration: TCP client with control commands

4. **MARA Spotter**
   - Type: Multi-sensor (EO/IR/Acoustic)
   - Protocol: UDP
   - Capabilities: Detection, classification, tracking
   - Integration: UDP listener with data parsing

5. **Dspnor Dronnur 2D**
   - Type: LPI/LPD radar
   - Protocol: UDP
   - Capabilities: Radar detection, tracking
   - Integration: UDP listener with radar processing

### Data Flow

```
Sensor ──UDP/TCP──► Plugin ──Event──► Event Manager ──Event──► Processing Plugins
  │                    │                │                      │
  │                    ▼                ▼                      ▼
  │              ┌─────────────┐ ┌─────────────┐      ┌─────────────┐
  │              │   Raw Data  │ │   Detection │      │   Fusion    │
  │              │   Parser    │ │   Event     │      │   Logic     │
  │              └─────────────┘ └─────────────┘      └─────────────┘
  │                                                           │
  └───────────────────────────────────────────────────────────┘
```

## Detection Processing

### Bearing Normalization

All bearings are normalized to bow-relative coordinates:
- **0° (0 rad)**: Bow direction
- **90° (π/2 rad)**: Starboard
- **180° (π rad)**: Stern
- **270° (3π/2 rad)**: Port

### Confidence Fusion

The system uses Bayesian log-odds fusion for confidence assessment:

```
Confidence = log(P(detection|evidence) / P(no_detection|evidence))
```

Features:
- Hysteresis to prevent oscillation
- Weighted fusion based on sensor reliability
- Temporal smoothing for stability

### Range Estimation

Multiple range estimation methods:

1. **Fixed Range**: Predefined detection range
2. **RF Range**: Log-distance model for RF sensors
3. **EO Range**: Pixel-based estimation for cameras
4. **IR Range**: Temperature-based estimation
5. **Acoustic Range**: Spherical spreading model
6. **Fusion**: Inverse-variance weighted combination

### Data Schemas

Standardized JSON schemas for all data types:

```json
{
  "detection": {
    "id": "uuid",
    "timestamp": "ISO8601",
    "sensor": "string",
    "bearing": "float (degrees)",
    "range": "float (meters)",
    "confidence": "float (0-1)",
    "classification": "string"
  }
}
```

## Configuration

### Environment Variables

The system uses environment variables for configuration:

```bash
# Network settings
UDP_PORT_DRONESHIELD=50001
UDP_PORT_SILVUS=50002
TCP_HOST_TRAKKA=192.168.1.100
TCP_PORT_TRAKKA=8080

# Processing settings
CONFIDENCE_THRESHOLD=0.7
RANGE_ESTIMATION_MODE=fusion
BEARING_OFFSET=0.0

# Logging settings
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### Configuration Files

- **config.json**: Main configuration
- **.env**: Environment variables
- **docs/env.sample**: Template configuration
- **docs/env.schema.json**: JSON Schema validation

## Deployment

### Platforms

1. **Windows + NVIDIA RTX**
   - CUDA support for GPU processing
   - DirectX for graphics acceleration
   - PowerShell scripts for automation

2. **Jetson L4T/JetPack**
   - ARM64 architecture
   - CUDA support for GPU processing
   - Optimized for embedded deployment

3. **Docker Containers**
   - Multi-platform support
   - Isolated environments
   - Easy deployment and scaling

### Quickstart

#### Windows
```powershell
# Set environment
.\\scripts\\windows\\SET_ENV.ps1

# Run application
python app.py
```

#### Jetson
```bash
# Set environment
source scripts/setup_jetson.sh

# Run application
python app.py
```

#### Docker
```bash
# Workstation
docker-compose up

# Jetson
docker-compose -f docker-compose.jetson.yml up
```

## Monitoring and Health

### Health Endpoints

- **GET /health**: Application health status
- **GET /health/plugins**: Plugin health status
- **GET /health/database**: Database health status

### Performance Monitoring

- **Ingest Rate**: Detections per second
- **Processing Latency**: End-to-end processing time
- **Memory Usage**: RAM consumption
- **CPU Usage**: CPU utilization
- **Network I/O**: Network traffic

### Logging

Structured logging with JSON output:

```json
{
  "timestamp": "2024-12-19T10:30:00Z",
  "level": "INFO",
  "logger": "droneshield_plugin",
  "message": "Detection received",
  "detection_id": "uuid",
  "bearing": 45.0,
  "confidence": 0.85
}
```

## Security

### Security Measures

1. **Dependency Scanning**: Regular vulnerability scanning
2. **Secret Detection**: Automated secret detection
3. **SBOM Generation**: Software Bill of Materials
4. **Configuration Security**: Secure default settings
5. **Network Security**: Proper network configuration

### Security Reports

- **SECURITY_REPORT.md**: Security analysis results
- **sbom.json**: Software Bill of Materials
- **Dependency audit**: Vulnerability assessment

## Testing

### Test Types

1. **Unit Tests**: Individual component testing
2. **Integration Tests**: Component interaction testing
3. **Plugin Tests**: Plugin-specific testing
4. **Smoke Tests**: End-to-end validation
5. **Performance Tests**: Load and stress testing

### Test Execution

```bash
# Run all tests
python scripts/run_tests.py

# Run with coverage
python scripts/run_tests.py --coverage

# Run specific suite
python scripts/run_tests.py --suite confidence
```

## Troubleshooting

### Common Issues

1. **Plugin Loading**: Check plugin dependencies
2. **Sensor Connection**: Verify network configuration
3. **Bearing Normalization**: Check bearing offset settings
4. **Performance**: Monitor resource usage
5. **Configuration**: Validate environment variables

### Debug Commands

```bash
# Check health
python scripts/health_check.py

# Validate configuration
python scripts/validate_plugin_conformance.py

# Run smoke test
python scripts/smoke_test.py
```

## Support

### Documentation

- **API Reference**: Complete API documentation
- **Configuration Guide**: Detailed configuration reference
- **Quickstart Guides**: Platform-specific instructions
- **Troubleshooting**: Common issues and solutions

### Resources

- **Repository**: Source code and documentation
- **Issues**: Bug reports and feature requests
- **Support**: Technical support and assistance
- **Community**: User community and discussions

## Future Development

### Planned Features

1. **Machine Learning**: AI-powered detection and classification
2. **Advanced Fusion**: More sophisticated sensor fusion algorithms
3. **Real-time Analytics**: Live data analysis and visualization
4. **Cloud Integration**: Cloud-based data storage and processing
5. **Mobile App**: Mobile interface for monitoring and control

### Roadmap

- **Q1 2025**: Machine learning integration
- **Q2 2025**: Advanced analytics
- **Q3 2025**: Cloud integration
- **Q4 2025**: Mobile application
