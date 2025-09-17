# Performance Notes for TheBox

This document describes performance characteristics, tuning knobs, and fail-open behavior for TheBox in production environments.

## Performance Characteristics

### System Requirements

#### Minimum Requirements
- **CPU**: 4 cores, 2.0 GHz
- **RAM**: 8GB
- **Storage**: 10GB free space
- **Network**: 1 Gbps Ethernet

#### Recommended Requirements
- **CPU**: 8 cores, 3.0 GHz
- **RAM**: 16GB
- **Storage**: 50GB SSD
- **Network**: 10 Gbps Ethernet
- **GPU**: NVIDIA RTX 3060+ (for vision processing)

#### Jetson Requirements
- **Device**: Xavier NX, Orin Nano, Orin NX, AGX Orin
- **JetPack**: 5.1+ (L4T 35.2+)
- **RAM**: 8GB+ (16GB+ for AGX Orin)
- **Storage**: 32GB+ eMMC/SD

### Performance Metrics

#### Throughput
- **Detection Rate**: 100-1000 detections/second
- **Event Processing**: 500-2000 events/second
- **Web Requests**: 100-500 requests/second
- **UDP Packets**: 1000-10000 packets/second

#### Latency
- **Detection Processing**: 10-100ms
- **Event Propagation**: 1-10ms
- **Web Response**: 50-200ms
- **Vision Processing**: 100-1000ms (GPU), 500-5000ms (CPU)

#### Memory Usage
- **Base Application**: 200-500MB
- **With Vision Processing**: 1-4GB
- **Peak Usage**: 2-8GB
- **Jetson Peak**: 4-6GB

## Tuning Knobs

### Environment Variables

#### Core Performance
```env
# Thread pool size for event processing
EVENT_POOL_SIZE=10

# Database cache size
DB_CACHE_SIZE=1000

# Log level (affects performance)
LOG_LEVEL=INFO

# Enable performance monitoring
PERF_MONITORING=true
```

#### Vision Processing
```env
# Vision backend (affects performance significantly)
VISION_BACKEND=onnxruntime  # or cpu

# Input resolution (affects processing time)
VISION_INPUT_RES=640  # 320, 416, 512, 640, 896, 960

# Frame skipping (reduce processing load)
VISION_FRAME_SKIP=2  # Process every Nth frame

# Consecutive frames for detection
VISION_N_CONSEC_FOR_TRUE=3

# Processing latency
VISION_LATENCY_MS=5000

# Maximum dwell time
VISION_MAX_DWELL_MS=7000
```

#### Sensor Processing
```env
# DroneShield processing
DRONESHIELD_UDP_PORT=8888
REPLAY_INTERVAL_MS=400

# Silvus processing
SILVUS_UDP_PORT=50051
SILVUS_STATUS_BUFFER_MAX=100

# MARA processing
MARA_UDP_PORT=8787
MARA_MAX_QUEUE=10000
MARA_HEARTBEAT_SEC=10

# Dspnor processing
DSPNOR_CAT010_PORT=4010
DSPNOR_BUFFER_BYTES=65536
DSPNOR_MAX_MSG_RATE_HZ=200
```

#### Confidence and Range
```env
# Confidence fusion
CONF_FUSION_METHOD=bayes
CONF_HYSTERESIS=0.05

# Range estimation
RANGE_MODE=FIXED  # or RF, EO, IR, ACOUSTIC, HYBRID
RANGE_EWMA_ALPHA=0.4
```

### Performance Monitoring

#### Metrics Collection
```python
from mvp.performance_monitor import performance_monitor, performance_probe

# Record custom metrics
performance_monitor.increment_counter("detections_processed")
performance_monitor.set_gauge("active_tracks", 5)
performance_monitor.record_timer("processing_time", 0.1)

# Use decorator for automatic timing
@performance_probe("detection_processing")
def process_detection(detection):
    # Processing logic
    pass
```

#### Thresholds
```python
from mvp.performance_monitor import PerformanceThreshold

# Set performance thresholds
performance_monitor.set_threshold(PerformanceThreshold(
    name="response_time",
    warning_threshold=2.0,
    critical_threshold=5.0,
    unit="seconds"
))
```

## Fail-Open Behavior

### Overview
TheBox implements fail-open behavior to ensure system availability even when individual components fail. This is critical for field deployment where system downtime is not acceptable.

### Fail-Open Components

#### Critical Components (Fail-Open Enabled)
- **Database**: In-memory database with automatic recovery
- **Event Manager**: Core event processing system
- **Plugin Manager**: Plugin lifecycle management
- **Web Interface**: User interface and API

#### Non-Critical Components (Fail-Open Disabled)
- **Sensor Listeners**: Individual sensor plugins
- **Vision Processing**: Computer vision analysis
- **Confidence Fusion**: Detection confidence calculation
- **Range Estimation**: Range calculation

### Fail-Open Triggers

#### Error Rate Thresholds
- **Warning**: 5% error rate
- **Critical**: 10% error rate
- **Fail-Open**: 15% error rate

#### Response Time Thresholds
- **Warning**: 2 seconds
- **Critical**: 5 seconds
- **Fail-Open**: 10 seconds

#### Resource Usage Thresholds
- **Memory Usage**: 90% (fail-open)
- **CPU Usage**: 90% (fail-open)
- **Disk Usage**: 95% (fail-open)

### Fail-Open Behavior

#### Database Fail-Open
- **Trigger**: Database connection failures, corruption
- **Behavior**: Switch to read-only mode, disable writes
- **Recovery**: Automatic restart, data reconstruction

#### Event Manager Fail-Open
- **Trigger**: Event processing failures, queue overflow
- **Behavior**: Drop non-critical events, process critical events only
- **Recovery**: Queue cleanup, restart processing

#### Plugin Manager Fail-Open
- **Trigger**: Plugin loading failures, plugin crashes
- **Behavior**: Disable failed plugins, continue with working plugins
- **Recovery**: Plugin restart, reinitialization

#### Web Interface Fail-Open
- **Trigger**: HTTP server failures, request timeouts
- **Behavior**: Return cached responses, disable non-essential endpoints
- **Recovery**: Server restart, cache refresh

### Monitoring Fail-Open State

#### Health Check Endpoint
```bash
# Check overall health
curl http://localhost:80/health

# Check specific component
curl http://localhost:80/plugins/droneshield_listener/status
```

#### Performance Monitoring
```python
from mvp.performance_monitor import fail_open_manager

# Check fail-open status
status = fail_open_manager.get_status()
print(status)

# Check specific component
if fail_open_manager.is_fail_open("database"):
    print("Database is in fail-open state")
```

## Performance Optimization

### 1. Vision Processing Optimization

#### GPU Acceleration
```env
# Enable GPU acceleration
VISION_BACKEND=onnxruntime
CUDA_VISIBLE_DEVICES=0

# Optimize for specific GPU
VISION_INPUT_RES=640  # RTX 3060+
VISION_INPUT_RES=320  # Jetson Xavier NX
```

#### Frame Rate Optimization
```env
# Reduce processing load
VISION_FRAME_SKIP=3  # Process every 3rd frame
VISION_N_CONSEC_FOR_TRUE=2  # Reduce confirmation requirement
```

#### Memory Optimization
```env
# Reduce memory usage
VISION_INPUT_RES=320
VISION_ROI_HALF_DEG=10.0  # Reduce region of interest
```

### 2. Sensor Processing Optimization

#### UDP Buffer Sizes
```env
# Optimize UDP buffers
DRONESHIELD_UDP_PORT=8888
SILVUS_UDP_PORT=50051
MARA_UDP_PORT=8787
DSPNOR_BUFFER_BYTES=32768  # Reduce from 65536
```

#### Queue Management
```env
# Optimize queue sizes
MARA_MAX_QUEUE=5000  # Reduce from 10000
DSPNOR_MAX_MSG_RATE_HZ=100  # Reduce from 200
```

### 3. Database Optimization

#### Cache Management
```env
# Optimize database cache
DB_CACHE_SIZE=500  # Reduce from 1000
THEBOX_STATE_SAVE_EVERY_SEC=5  # Increase from 3
```

#### Memory Usage
```env
# Limit detection history
DRONESHIELD_MESSAGE_LIMIT=100  # Limit message history
SILVUS_STATUS_BUFFER_MAX=50  # Reduce from 100
```

### 4. Network Optimization

#### Port Configuration
```env
# Use high-performance ports
THEBOX_WEB_PORT=80
DRONESHIELD_UDP_PORT=8888
SILVUS_UDP_PORT=50051
```

#### Buffer Sizes
```env
# Optimize network buffers
UDP_RECV_BUFFER=65536
UDP_SEND_BUFFER=65536
TCP_RECV_BUFFER=65536
TCP_SEND_BUFFER=65536
```

## Monitoring and Alerting

### Performance Metrics

#### Key Metrics
- **Detection Rate**: Detections per second
- **Processing Latency**: Time to process detection
- **Memory Usage**: Current memory consumption
- **CPU Usage**: Current CPU utilization
- **Error Rate**: Errors per second
- **Queue Depth**: Pending events in queue

#### Thresholds
- **Detection Rate**: < 10/sec (warning), < 5/sec (critical)
- **Processing Latency**: > 2s (warning), > 5s (critical)
- **Memory Usage**: > 80% (warning), > 90% (critical)
- **CPU Usage**: > 80% (warning), > 90% (critical)
- **Error Rate**: > 5% (warning), > 10% (critical)
- **Queue Depth**: > 1000 (warning), > 5000 (critical)

### Alerting

#### Health Check Alerts
```bash
# Check application health
python3 scripts/health_check.py --verbose

# Check specific components
curl http://localhost:80/health | jq '.checks'
```

#### Performance Alerts
```python
from mvp.performance_monitor import performance_monitor

# Get performance summary
summary = performance_monitor.get_summary()
print(summary)

# Check fail-open state
if performance_monitor.fail_open:
    print(f"System in fail-open mode: {performance_monitor.fail_open_reason}")
```

### Logging

#### Performance Logs
```bash
# View performance logs
tail -f logs/performance.log

# View application logs
tail -f logs/thebox.log

# View error logs
tail -f logs/error.log
```

#### Structured Logging
```python
import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()
logger.info("Performance metric", metric="detection_rate", value=100.5)
```

## Troubleshooting

### Common Performance Issues

#### 1. High CPU Usage
- **Cause**: Vision processing, excessive logging, inefficient algorithms
- **Solution**: Enable frame skipping, reduce log level, optimize algorithms
- **Monitoring**: `top`, `htop`, `nvidia-smi`

#### 2. High Memory Usage
- **Cause**: Memory leaks, large data structures, excessive caching
- **Solution**: Restart application, reduce cache sizes, fix memory leaks
- **Monitoring**: `free -h`, `ps aux`, `nvidia-smi`

#### 3. Slow Response Times
- **Cause**: Network latency, database issues, plugin failures
- **Solution**: Check network, optimize database, restart plugins
- **Monitoring**: `curl`, `ping`, `netstat`

#### 4. Detection Drops
- **Cause**: UDP buffer overflow, processing bottlenecks, network issues
- **Solution**: Increase buffer sizes, optimize processing, check network
- **Monitoring**: `netstat -i`, `ss -u`, application logs

### Performance Debugging

#### Enable Debug Mode
```env
# Enable debug logging
LOG_LEVEL=DEBUG
PERF_MONITORING=true
DEBUG_MODE=true
```

#### Profile Application
```python
# Use performance profiler
import cProfile
import pstats

cProfile.run('app.main()', 'profile.stats')
p = pstats.Stats('profile.stats')
p.sort_stats('cumulative').print_stats(10)
```

#### Monitor Resources
```bash
# Monitor system resources
htop
nvidia-smi -l 1
iotop
netstat -i
```

## Best Practices

### 1. Production Deployment
- Use production-grade hardware
- Enable all monitoring and alerting
- Set up automated failover
- Implement backup and recovery procedures

### 2. Performance Tuning
- Start with conservative settings
- Monitor performance metrics
- Gradually optimize based on data
- Test changes in staging environment

### 3. Fail-Open Configuration
- Enable fail-open for critical components
- Set appropriate thresholds
- Monitor fail-open state
- Implement recovery procedures

### 4. Monitoring and Alerting
- Set up comprehensive monitoring
- Configure appropriate alerts
- Use structured logging
- Implement automated responses

### 5. Maintenance
- Regular performance reviews
- Proactive monitoring
- Capacity planning
- Continuous optimization
