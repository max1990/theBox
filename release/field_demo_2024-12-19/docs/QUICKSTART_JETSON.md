# TheBox Quickstart Guide - Jetson

This guide will help you get TheBox running on NVIDIA Jetson devices with L4T/JetPack support.

## Prerequisites

### System Requirements
- NVIDIA Jetson device (Xavier NX, Orin Nano, Orin NX, AGX Orin)
- JetPack 5.1+ (L4T 35.2+)
- 8GB+ RAM (16GB+ recommended for AGX Orin)
- 32GB+ eMMC/SD storage
- Active cooling (recommended for sustained operation)

### Software Requirements
- JetPack 5.1+ with L4T 35.2+
- Python 3.8+ (included with JetPack)
- Docker (optional, for containerized deployment)
- Git

## Installation

### Method 1: Direct Python Installation

1. **Update system packages**
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

2. **Install additional dependencies**
   ```bash
   sudo apt install -y \
     python3-pip \
     python3-venv \
     python3-dev \
     build-essential \
     cmake \
     pkg-config \
     libjpeg-dev \
     libtiff5-dev \
     libpng-dev \
     libavcodec-dev \
     libavformat-dev \
     libswscale-dev \
     libv4l-dev \
     libxvidcore-dev \
     libx264-dev \
     libgtk-3-dev \
     libatlas-base-dev \
     gfortran \
     wget \
     curl \
     git
   ```

3. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/thebox.git
   cd thebox
   ```

4. **Create virtual environment**
   ```bash
   python3 -m venv venv-jetson
   source venv-jetson/bin/activate
   ```

5. **Install dependencies**
   ```bash
   pip install --upgrade pip setuptools wheel
   pip install -r requirements.txt
   pip install -r requirements-jetson.txt
   pip install -r requirements-dev.txt
   ```

6. **Set up environment**
   ```bash
   cp docs/env.sample env/.thebox.env
   # Edit env/.thebox.env with your configuration
   ```

### Method 2: Docker Installation

1. **Install Docker (if not already installed)**
   ```bash
   # Install Docker
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh
   sudo usermod -aG docker $USER
   
   # Install NVIDIA Container Toolkit
   distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
   curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
   curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
   
   sudo apt-get update && sudo apt-get install -y nvidia-docker2
   sudo systemctl restart docker
   ```

2. **Build and run**
   ```bash
   docker-compose -f docker-compose.jetson.yml up --build
   ```

## Configuration

### Environment Variables

Create `env/.thebox.env` with your configuration:

```env
# Core Configuration
SECRET_KEY=your-secret-key-here
THEBOX_WEB_HOST=0.0.0.0
THEBOX_WEB_PORT=80

# Jetson-specific Configuration
VISION_BACKEND=onnxruntime
VISION_INPUT_RES=640
VISION_MODEL_PATH=path/to/your/model.onnx
CUDA_VISIBLE_DEVICES=0
CUDA_DEVICE_ORDER=PCI_BUS_ID

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

# Performance Tuning
VISION_FRAME_SKIP=2
VISION_N_CONSEC_FOR_TRUE=3
VISION_LATENCY_MS=5000
VISION_MAX_DWELL_MS=7000
```

### Jetson-Specific Optimizations

#### 1. Power Management
```bash
# Set maximum performance mode
sudo nvpmodel -m 0
sudo jetson_clocks

# Check power mode
sudo nvpmodel -q
```

#### 2. Memory Management
```bash
# Increase swap space (if needed)
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

#### 3. GPU Memory
```bash
# Check GPU memory usage
sudo tegrastats

# Monitor GPU utilization
watch -n 1 nvidia-smi
```

## Usage

### Starting the Application

1. **Activate virtual environment**
   ```bash
   source venv-jetson/bin/activate
   ```

2. **Run the application**
   ```bash
   python3 app.py
   ```

3. **Access web interface**
   - Main dashboard: `http://jetson-ip:80`
   - Settings: `http://jetson-ip:80/settings`
   - Test console: `http://jetson-ip:80/test`

### Testing with Simulated Data

1. **Start UDP simulator**
   ```bash
   python3 scripts/udp_simulator.py --sensor droneshield --port 8888 --rate 1.0
   ```

2. **Run smoke test**
   ```bash
   python3 scripts/smoke_test.py --timeout 30 --verbose
   ```

3. **Check health status**
   ```bash
   python3 scripts/health_check.py --port 80 --verbose
   ```

### Performance Monitoring

#### 1. System Monitoring
```bash
# Monitor system resources
sudo tegrastats

# Monitor GPU usage
watch -n 1 nvidia-smi

# Monitor network traffic
sudo netstat -tulpn | grep :80
```

#### 2. Application Monitoring
```bash
# Check application logs
tail -f logs/thebox.log

# Monitor plugin status
curl http://localhost:80/status | jq

# Check health endpoint
curl http://localhost:80/health | jq
```

## Troubleshooting

### Common Issues

#### 1. CUDA/GPU Issues
```bash
# Check CUDA installation
nvcc --version
nvidia-smi

# Check PyTorch CUDA support
python3 -c "import torch; print(torch.cuda.is_available())"

# Check ONNX Runtime GPU support
python3 -c "import onnxruntime; print(onnxruntime.get_available_providers())"
```

#### 2. Memory Issues
```bash
# Check memory usage
free -h
sudo tegrastats

# Check swap usage
swapon --show
```

#### 3. Thermal Issues
```bash
# Check temperature
sudo tegrastats

# Check thermal zones
cat /sys/class/thermal/thermal_zone*/temp
```

#### 4. Network Issues
```bash
# Check network interfaces
ip addr show

# Check port usage
sudo netstat -tulpn | grep :80

# Test network connectivity
ping -c 4 8.8.8.8
```

### Performance Issues

#### 1. Slow Vision Processing
- Reduce `VISION_INPUT_RES` to 320 or 416
- Increase `VISION_FRAME_SKIP` to 3 or 4
- Check GPU memory usage with `nvidia-smi`

#### 2. High CPU Usage
- Enable `VISION_FRAME_SKIP`
- Reduce `VISION_N_CONSEC_FOR_TRUE`
- Check for thermal throttling

#### 3. Memory Leaks
- Monitor memory usage with `tegrastats`
- Restart application periodically
- Check for plugin memory leaks

### Logs and Debugging

#### View Logs
```bash
# Application logs
tail -f logs/thebox.log

# System logs
sudo journalctl -u thebox -f

# Kernel logs
sudo dmesg | tail -20
```

#### Debug Mode
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python3 app.py

# Enable verbose output
python3 scripts/smoke_test.py --verbose
```

## Performance Optimization

### 1. Power Management
```bash
# Set maximum performance mode
sudo nvpmodel -m 0
sudo jetson_clocks

# For battery operation, use balanced mode
sudo nvpmodel -m 2
```

### 2. Memory Optimization
```env
# Reduce memory usage
VISION_INPUT_RES=320
VISION_FRAME_SKIP=3
MARA_MAX_QUEUE=1000
DSPNOR_BUFFER_BYTES=16384
```

### 3. GPU Optimization
```env
# Optimize for Jetson
VISION_BACKEND=onnxruntime
VISION_INPUT_RES=640
CUDA_VISIBLE_DEVICES=0
```

### 4. Network Optimization
```env
# Optimize network settings
DRONESHIELD_UDP_PORT=8888
SILVUS_UDP_PORT=50051
MARA_UDP_PORT=8787
```

## Security Considerations

### 1. Production Deployment
```env
# Change default secret key
SECRET_KEY=your-very-secure-secret-key-here

# Enable settings protection
SETTINGS_PROTECT=true
SETTINGS_PASSWORD=your-admin-password
```

### 2. Network Security
- Configure firewall rules
- Use VPN for remote access
- Encrypt sensor data in transit

### 3. System Security
```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Configure automatic security updates
sudo apt install unattended-upgrades
sudo dpkg-reconfigure unattended-upgrades
```

## Support

### Getting Help
1. **Check logs** for error messages
2. **Run health check** to identify issues
3. **Review configuration** for incorrect settings
4. **Check system requirements** and dependencies

### Useful Commands
```bash
# Full system check
python3 scripts/smoke_test.py --verbose

# Plugin conformance check
python3 scripts/validate_plugin_conformance.py --verbose

# Generate system report
python3 scripts/health_check.py --json > system_report.json

# Check Jetson status
sudo tegrastats
nvidia-smi
```

### Contact Information
- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/your-org/thebox/issues)
- **Support**: support@your-org.com
