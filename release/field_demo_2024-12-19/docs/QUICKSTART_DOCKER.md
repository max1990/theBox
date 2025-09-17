# TheBox Quickstart Guide - Docker

This guide will help you get TheBox running using Docker containers on various platforms.

## Prerequisites

### System Requirements
- Docker 20.10+ with Compose v2
- NVIDIA Container Toolkit (for GPU support)
- 8GB+ RAM
- 10GB+ free disk space
- NVIDIA GPU (for workstation deployment)

### Platform Support
- **Workstation**: Windows 10/11, Linux, macOS (with NVIDIA GPU)
- **Jetson**: NVIDIA Jetson devices with L4T/JetPack 5.1+

## Installation

### 1. Install Docker

#### Windows/macOS
- Download and install [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- Enable NVIDIA Container Toolkit in Docker Desktop settings

#### Linux
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

#### Jetson
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

### 2. Clone Repository
```bash
git clone https://github.com/your-org/thebox.git
cd thebox
```

## Deployment

### Workstation Deployment

1. **Build and run**
   ```bash
   docker-compose up --build
   ```

2. **Access the application**
   - Web interface: `http://localhost:80`
   - Health check: `http://localhost:80/health`

### Jetson Deployment

1. **Build and run**
   ```bash
   docker-compose -f docker-compose.jetson.yml up --build
   ```

2. **Access the application**
   - Web interface: `http://jetson-ip:80`
   - Health check: `http://jetson-ip:80/health`

### Custom Configuration

1. **Create environment file**
   ```bash
   cp docs/env.sample .env
   # Edit .env with your configuration
   ```

2. **Run with custom environment**
   ```bash
   docker-compose --env-file .env up --build
   ```

## Configuration

### Environment Variables

Create `.env` file with your configuration:

```env
# Core Configuration
SECRET_KEY=your-secret-key-here
THEBOX_WEB_HOST=0.0.0.0
THEBOX_WEB_PORT=80

# GPU Configuration
VISION_BACKEND=onnxruntime
VISION_MODEL_PATH=path/to/your/model.onnx
CUDA_VISIBLE_DEVICES=0

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

### Volume Mounts

The Docker configuration mounts the following volumes:
- `./data:/app/data` - Application data
- `./logs:/app/logs` - Log files
- `./env:/app/env` - Environment configuration

### Port Mapping

| Service | Internal Port | External Port | Description |
|---------|---------------|---------------|-------------|
| Web UI | 80 | 80 | Main web interface |
| DroneShield | 8888 | 8888 | RF detection data |
| Silvus | 50051 | 50051 | AoA detection data |
| MARA | 8787 | 8787 | EO/IR/Acoustic data |
| Dspnor CAT010 | 4010 | 4010 | Radar detection data |
| Dspnor NMEA | 60000 | 60000 | GPS/Heading data |
| SeaCross | 62000 | 62000 | Output data |

## Usage

### Basic Operations

#### Start the application
```bash
docker-compose up -d
```

#### Stop the application
```bash
docker-compose down
```

#### View logs
```bash
docker-compose logs -f
```

#### Restart the application
```bash
docker-compose restart
```

### Testing

#### Run smoke test
```bash
docker-compose exec thebox python3 scripts/smoke_test.py --verbose
```

#### Check health status
```bash
docker-compose exec thebox python3 scripts/health_check.py --verbose
```

#### Test with simulated data
```bash
# Start UDP simulator
docker-compose exec thebox python3 scripts/udp_simulator.py --sensor droneshield --port 8888 --rate 1.0

# In another terminal
docker-compose exec thebox python3 scripts/udp_simulator.py --sensor silvus --port 50051 --rate 1.0
```

### Monitoring

#### Container status
```bash
docker-compose ps
```

#### Resource usage
```bash
docker stats thebox
```

#### Health check
```bash
curl http://localhost:80/health | jq
```

## Troubleshooting

### Common Issues

#### 1. GPU Not Available
```bash
# Check NVIDIA Container Toolkit
docker run --rm --gpus all nvidia/cuda:11.8-base-ubuntu22.04 nvidia-smi

# Check Docker GPU support
docker run --rm --gpus all nvidia/cuda:11.8-base-ubuntu22.04 nvidia-smi
```

#### 2. Port Conflicts
```bash
# Check port usage
netstat -tulpn | grep :80
netstat -tulpn | grep :8888

# Kill process using port
sudo kill -9 <PID>
```

#### 3. Permission Issues
```bash
# Fix volume permissions
sudo chown -R $USER:$USER data logs env

# Check Docker permissions
sudo usermod -aG docker $USER
```

#### 4. Memory Issues
```bash
# Check Docker memory limits
docker stats thebox

# Increase memory limit in docker-compose.yml
services:
  thebox:
    deploy:
      resources:
        limits:
          memory: 8G
```

### Debugging

#### View container logs
```bash
docker-compose logs thebox
```

#### Access container shell
```bash
docker-compose exec thebox bash
```

#### Check container health
```bash
docker-compose exec thebox python3 scripts/health_check.py --verbose
```

#### Monitor resource usage
```bash
docker stats thebox
```

## Performance Optimization

### 1. Resource Limits
```yaml
services:
  thebox:
    deploy:
      resources:
        limits:
          memory: 8G
          cpus: '4.0'
        reservations:
          memory: 4G
          cpus: '2.0'
```

### 2. GPU Optimization
```yaml
services:
  thebox:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

### 3. Volume Optimization
```yaml
services:
  thebox:
    volumes:
      - thebox-data:/app/data
      - thebox-logs:/app/logs
      - thebox-env:/app/env

volumes:
  thebox-data:
    driver: local
  thebox-logs:
    driver: local
  thebox-env:
    driver: local
```

## Security Considerations

### 1. Production Deployment
```yaml
services:
  thebox:
    environment:
      - SECRET_KEY=${SECRET_KEY}
      - SETTINGS_PROTECT=true
      - SETTINGS_PASSWORD=${SETTINGS_PASSWORD}
    volumes:
      - ./env/.thebox.env:/app/env/.thebox.env:ro
```

### 2. Network Security
```yaml
services:
  thebox:
    networks:
      - thebox-internal
    ports:
      - "127.0.0.1:80:80"  # Bind to localhost only

networks:
  thebox-internal:
    driver: bridge
    internal: true
```

### 3. Resource Limits
```yaml
services:
  thebox:
    deploy:
      resources:
        limits:
          memory: 8G
          cpus: '4.0'
        reservations:
          memory: 4G
          cpus: '2.0'
```

## Advanced Configuration

### 1. Custom Dockerfile
```dockerfile
FROM nvidia/cuda:11.8-devel-ubuntu22.04

# Add custom dependencies
RUN apt-get update && apt-get install -y \
    your-custom-package

# Copy custom configuration
COPY custom-config/ /app/config/

# Rest of Dockerfile...
```

### 2. Multi-stage Build
```dockerfile
# Build stage
FROM nvidia/cuda:11.8-devel-ubuntu22.04 as builder
# ... build steps ...

# Runtime stage
FROM nvidia/cuda:11.8-runtime-ubuntu22.04
COPY --from=builder /app /app
# ... runtime configuration ...
```

### 3. Health Checks
```yaml
services:
  thebox:
    healthcheck:
      test: ["python3", "scripts/health_check.py", "--host", "127.0.0.1", "--port", "80"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

## Support

### Getting Help
1. **Check container logs** for error messages
2. **Run health check** to identify issues
3. **Review configuration** for incorrect settings
4. **Check system requirements** and dependencies

### Useful Commands
```bash
# Full system check
docker-compose exec thebox python3 scripts/smoke_test.py --verbose

# Plugin conformance check
docker-compose exec thebox python3 scripts/validate_plugin_conformance.py --verbose

# Generate system report
docker-compose exec thebox python3 scripts/health_check.py --json > system_report.json

# Clean up containers
docker-compose down -v
docker system prune -a
```

### Contact Information
- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/your-org/thebox/issues)
- **Support**: support@your-org.com
