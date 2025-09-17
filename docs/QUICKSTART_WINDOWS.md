# TheBox Quickstart Guide - Windows

This guide will help you get TheBox running on Windows with NVIDIA RTX support.

## Prerequisites

### System Requirements
- Windows 10/11 (64-bit)
- NVIDIA RTX GPU with CUDA support
- 8GB+ RAM
- 10GB+ free disk space
- Python 3.11+ (recommended: 3.11.7)

### Software Requirements
- [Python 3.11.7](https://www.python.org/downloads/release/python-3117/)
- [Git for Windows](https://git-scm.com/download/win)
- [NVIDIA CUDA Toolkit 11.8+](https://developer.nvidia.com/cuda-downloads)
- [NVIDIA cuDNN](https://developer.nvidia.com/cudnn)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (optional)

## Installation

### Method 1: Direct Python Installation

1. **Clone the repository**
   ```cmd
   git clone https://github.com/your-org/thebox.git
   cd thebox
   ```

2. **Create virtual environment**
   ```cmd
   python -m venv venv-win
   venv-win\Scripts\activate
   ```

3. **Install dependencies**
   ```cmd
   pip install --upgrade pip setuptools wheel
   pip install -r requirements.txt
   pip install -r requirements-gpu.txt
   pip install -r requirements-dev.txt
   ```

4. **Set up environment**
   ```cmd
   copy docs\env.sample env\.thebox.env
   # Edit env\.thebox.env with your configuration
   ```

5. **Run the application**
   ```cmd
   python app.py
   ```

### Method 2: Docker Installation

1. **Prerequisites**
   - Install Docker Desktop
   - Enable NVIDIA Container Toolkit in Docker Desktop

2. **Build and run**
   ```cmd
   docker-compose up --build
   ```

## Configuration

### Environment Variables

Create `env\.thebox.env` with your configuration:

```env
# Core Configuration
SECRET_KEY=your-secret-key-here
THEBOX_WEB_HOST=0.0.0.0
THEBOX_WEB_PORT=80

# GPU Configuration
VISION_BACKEND=onnxruntime
VISION_MODEL_PATH=path/to/your/model.onnx

# Sensor Configuration
DRONESHIELD_UDP_PORT=8888
SILVUS_UDP_PORT=50051
MARA_UDP_PORT=8787
DSPNOR_CAT010_PORT=4010
DSPNOR_NMEA_UDP_PORT=60000
SEACROSS_PORT=62000

# Bearing Offsets
BOW_ZERO_DEG=0.0
DRONESHIELD_BEARING_OFFSET_DEG=0.0
TRAKKA_BEARING_OFFSET_DEG=0.0
VISION_BEARING_OFFSET_DEG=0.0
ACOUSTIC_BEARING_OFFSET_DEG=0.0
```

### Sensor Configuration

#### DroneShield DS-X Mk2
- **Port**: 8888 (UDP)
- **Format**: JSON
- **Required Fields**: timestamp, bearing, rssi, protocol, device_name

#### Silvus FASST
- **Port**: 50051 (UDP)
- **Format**: Text or Protobuf
- **Required Fields**: time_utc, freq_mhz, aoa1_deg, aoa2_deg, heading_deg

#### MARA Spotter
- **Port**: 8787 (UDP)
- **Format**: JSON
- **Required Fields**: timestamp, bearing_deg, range_m, confidence, sensor_type

#### Dspnor Dronnur 2D
- **CAT010 Port**: 4010 (UDP)
- **NMEA Port**: 60000 (UDP)
- **Format**: Binary (CAT010), Text (NMEA)

## Usage

### Starting the Application

1. **Activate virtual environment**
   ```cmd
   venv-win\Scripts\activate
   ```

2. **Run the application**
   ```cmd
   python app.py
   ```

3. **Access web interface**
   - Open browser to `http://localhost:80`
   - Main dashboard: `http://localhost:80/`
   - Settings: `http://localhost:80/settings`
   - Test console: `http://localhost:80/test`

### Testing with Simulated Data

1. **Start UDP simulator**
   ```cmd
   python scripts\udp_simulator.py --sensor droneshield --port 8888 --rate 1.0
   ```

2. **Run smoke test**
   ```cmd
   python scripts\smoke_test.py --timeout 30 --verbose
   ```

3. **Check health status**
   ```cmd
   python scripts\health_check.py --port 80 --verbose
   ```

### Plugin Management

#### Available Plugins
- **DroneShield Listener**: RF detection from DroneShield DS-X Mk2
- **Silvus Listener**: AoA detection from Silvus FASST
- **MARA**: EO/IR/Acoustic detection from MARA Spotter
- **Dspnor**: Radar detection from Dspnor Dronnur 2D
- **Trakka Control**: Camera control for Trakka TC-300
- **Vision**: Computer vision processing
- **Confidence**: Detection confidence fusion
- **Range**: Range estimation
- **Search Planner**: Search pattern planning

#### Plugin Status
- Check plugin status: `http://localhost:80/status`
- Individual plugin status: `http://localhost:80/plugins/{plugin_name}/status`

## Troubleshooting

### Common Issues

#### 1. CUDA/GPU Issues
```cmd
# Check CUDA installation
nvidia-smi

# Check PyTorch CUDA support
python -c "import torch; print(torch.cuda.is_available())"
```

#### 2. Port Conflicts
```cmd
# Check port usage
netstat -an | findstr :80
netstat -an | findstr :8888

# Kill process using port
taskkill /PID <PID> /F
```

#### 3. Python Environment Issues
```cmd
# Recreate virtual environment
rmdir /s venv-win
python -m venv venv-win
venv-win\Scripts\activate
pip install -r requirements.txt
```

#### 4. Permission Issues
- Run Command Prompt as Administrator
- Check Windows Firewall settings
- Ensure antivirus isn't blocking the application

### Logs and Debugging

#### View Logs
```cmd
# Application logs
type logs\thebox.log

# Real-time logs
Get-Content logs\thebox.log -Wait
```

#### Debug Mode
```cmd
# Enable debug logging
set LOG_LEVEL=DEBUG
python app.py
```

#### Health Check
```cmd
# Check application health
python scripts\health_check.py --verbose

# Check specific plugin
curl http://localhost:80/plugins/droneshield_listener/status
```

## Performance Optimization

### GPU Optimization
1. **Enable GPU acceleration**
   ```env
   VISION_BACKEND=onnxruntime
   CUDA_VISIBLE_DEVICES=0
   ```

2. **Optimize vision processing**
   ```env
   VISION_INPUT_RES=640
   VISION_FRAME_SKIP=2
   VISION_N_CONSEC_FOR_TRUE=3
   ```

### Memory Optimization
1. **Limit detection history**
   ```env
   THEBOX_STATE_SAVE_EVERY_SEC=5
   ```

2. **Optimize plugin settings**
   ```env
   MARA_MAX_QUEUE=5000
   DSPNOR_BUFFER_BYTES=32768
   ```

## Security Considerations

### Production Deployment
1. **Change default secret key**
   ```env
   SECRET_KEY=your-very-secure-secret-key-here
   ```

2. **Enable settings protection**
   ```env
   SETTINGS_PROTECT=true
   SETTINGS_PASSWORD=your-admin-password
   ```

3. **Use HTTPS in production**
   - Configure reverse proxy (nginx/Apache)
   - Use SSL certificates
   - Update `THEBOX_WEB_HOST` and `THEBOX_WEB_PORT`

### Network Security
1. **Firewall configuration**
   - Allow only necessary ports
   - Restrict access to management interfaces
   - Use VPN for remote access

2. **Sensor data security**
   - Encrypt sensor data in transit
   - Use secure protocols where possible
   - Implement access controls

## Support

### Getting Help
1. **Check logs** for error messages
2. **Run health check** to identify issues
3. **Review configuration** for incorrect settings
4. **Check system requirements** and dependencies

### Useful Commands
```cmd
# Full system check
python scripts\smoke_test.py --verbose

# Plugin conformance check
python scripts\validate_plugin_conformance.py --verbose

# Generate system report
python scripts\health_check.py --json > system_report.json
```

### Contact Information
- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/your-org/thebox/issues)
- **Support**: support@your-org.com
