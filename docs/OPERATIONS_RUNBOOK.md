# Operations Runbook

## Overview

This runbook provides operational procedures for TheBox system deployment, monitoring, maintenance, and troubleshooting.

## System Architecture

### Core Components

- **Flask Application**: Main web server and API
- **Plugin Manager**: Manages sensor plugins
- **Event Manager**: Handles inter-plugin communication
- **DroneDB**: In-memory database for state management
- **Web UI**: Settings and monitoring interface

### Sensor Plugins

- **DroneShield**: RF detection (UDP)
- **Silvus**: RF spectrum analysis (UDP)
- **Trakka**: EO/IR camera control (TCP)
- **MARA**: Multi-sensor detection (UDP)
- **Dspnor**: LPI/LPD radar (UDP)

### Processing Plugins

- **Confidence**: Detection confidence fusion
- **Range**: Range estimation and tracking
- **Vision**: Computer vision processing

## Deployment Procedures

### Pre-Deployment Checklist

- [ ] **Environment Setup**: Verify Python 3.8+ installed
- [ ] **Dependencies**: Install required packages
- [ ] **Configuration**: Copy and configure `.env` file
- [ ] **Network**: Verify UDP/TCP ports available
- [ ] **Sensors**: Verify sensor connectivity
- [ ] **Testing**: Run smoke test and validation

### Windows Deployment

1. **Set Environment**:
   ```powershell
   .\\scripts\\windows\\SET_ENV.ps1
   ```

2. **Install Dependencies**:
   ```powershell
   pip install -r requirements.txt
   pip install -r requirements-gpu.txt  # For GPU support
   ```

3. **Configure System**:
   ```powershell
   copy docs\\env.sample .env
   # Edit .env with your settings
   ```

4. **Run Smoke Test**:
   ```powershell
   python scripts\\smoke_test.py
   ```

5. **Start Application**:
   ```powershell
   python app.py
   ```

### Jetson Deployment

1. **Set Environment**:
   ```bash
   source scripts/setup_jetson.sh
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-jetson.txt
   ```

3. **Configure System**:
   ```bash
   cp docs/env.sample .env
   # Edit .env with your settings
   ```

4. **Run Smoke Test**:
   ```bash
   python scripts/smoke_test.py
   ```

5. **Start Application**:
   ```bash
   python app.py
   ```

### Docker Deployment

1. **Build Images**:
   ```bash
   # Workstation
   docker build -f Dockerfile.workstation -t thebox:workstation .
   
   # Jetson
   docker build -f Dockerfile.jetson -t thebox:jetson .
   ```

2. **Run Containers**:
   ```bash
   # Workstation
   docker-compose up
   
   # Jetson
   docker-compose -f docker-compose.jetson.yml up
   ```

## Monitoring Procedures

### Health Monitoring

#### Application Health

Check application health endpoint:

```bash
# Local check
curl http://localhost:5000/health

# Remote check
curl http://<server>:5000/health
```

Expected response:
```json
{
  "healthy": true,
  "timestamp": "2024-12-19T10:30:00Z",
  "duration_ms": 15.2,
  "checks": {
    "database": true,
    "plugins_loaded": true,
    "event_manager": true,
    "plugins": {
      "droneshield": "available",
      "silvus": "available",
      "trakka": "available"
    }
  }
}
```

#### Plugin Health

Check individual plugin status:

```bash
# Check all plugins
curl http://localhost:5000/health/plugins

# Check specific plugin
curl http://localhost:5000/health/plugins/droneshield
```

#### Database Health

Check database status:

```bash
curl http://localhost:5000/health/database
```

### Performance Monitoring

#### Ingest Rate

Monitor detection processing rate:

```bash
# Check logs for ingest rate
grep "ingest_rate" logs/thebox.log

# Use performance monitor
python scripts/performance_monitor.py
```

#### Processing Latency

Monitor end-to-end processing time:

```bash
# Check latency logs
grep "processing_latency" logs/thebox.log

# Check performance metrics
curl http://localhost:5000/metrics
```

#### Resource Usage

Monitor system resources:

```bash
# CPU usage
top -p $(pgrep -f "python app.py")

# Memory usage
ps aux | grep "python app.py"

# Network I/O
netstat -i
```

### Log Monitoring

#### Application Logs

Monitor application logs:

```bash
# Follow logs
tail -f logs/thebox.log

# Search for errors
grep "ERROR" logs/thebox.log

# Search for warnings
grep "WARNING" logs/thebox.log
```

#### Plugin Logs

Monitor plugin-specific logs:

```bash
# DroneShield logs
grep "droneshield" logs/thebox.log

# Silvus logs
grep "silvus" logs/thebox.log

# Trakka logs
grep "trakka" logs/thebox.log
```

#### Performance Logs

Monitor performance metrics:

```bash
# Ingest rate
grep "ingest_rate" logs/thebox.log

# Processing latency
grep "processing_latency" logs/thebox.log

# Memory usage
grep "memory_usage" logs/thebox.log
```

## Maintenance Procedures

### Daily Maintenance

#### Health Checks

1. **Application Health**:
   ```bash
   python scripts/health_check.py
   ```

2. **Plugin Validation**:
   ```bash
   python scripts/validate_plugin_conformance.py
   ```

3. **Smoke Test**:
   ```bash
   python scripts/smoke_test.py
   ```

#### Log Review

1. **Error Review**:
   ```bash
   grep "ERROR" logs/thebox.log | tail -20
   ```

2. **Warning Review**:
   ```bash
   grep "WARNING" logs/thebox.log | tail -20
   ```

3. **Performance Review**:
   ```bash
   grep "performance" logs/thebox.log | tail -20
   ```

### Weekly Maintenance

#### System Updates

1. **Dependency Updates**:
   ```bash
   pip list --outdated
   pip install --upgrade <package>
   ```

2. **Security Updates**:
   ```bash
   safety check
   bandit -r .
   ```

3. **Configuration Review**:
   ```bash
   python scripts/validate_plugin_conformance.py --config
   ```

#### Performance Analysis

1. **Resource Usage**:
   ```bash
   python scripts/performance_monitor.py --report
   ```

2. **Detection Analysis**:
   ```bash
   python scripts/analyze_detections.py
   ```

3. **Plugin Performance**:
   ```bash
   python scripts/plugin_performance.py
   ```

### Monthly Maintenance

#### Security Audit

1. **Dependency Scan**:
   ```bash
   safety check --json > security_audit.json
   ```

2. **Secret Scan**:
   ```bash
   bandit -r . -f json > secret_scan.json
   ```

3. **SBOM Update**:
   ```bash
   cyclonedx-py -o sbom.json
   ```

#### Performance Optimization

1. **Configuration Tuning**:
   ```bash
   python scripts/optimize_config.py
   ```

2. **Plugin Optimization**:
   ```bash
   python scripts/optimize_plugins.py
   ```

3. **Database Optimization**:
   ```bash
   python scripts/optimize_database.py
   ```

## Troubleshooting Procedures

### Common Issues

#### Application Won't Start

1. **Check Dependencies**:
   ```bash
   pip list
   pip check
   ```

2. **Check Configuration**:
   ```bash
   python scripts/validate_plugin_conformance.py --config
   ```

3. **Check Logs**:
   ```bash
   tail -f logs/thebox.log
   ```

4. **Check Ports**:
   ```bash
   netstat -tulpn | grep :5000
   ```

#### Plugin Loading Issues

1. **Check Plugin Dependencies**:
   ```bash
   python scripts/validate_plugin_conformance.py --plugin <plugin_name>
   ```

2. **Check Plugin Configuration**:
   ```bash
   grep "<plugin_name>" .env
   ```

3. **Check Plugin Logs**:
   ```bash
   grep "<plugin_name>" logs/thebox.log
   ```

#### Sensor Connection Issues

1. **Check Network Connectivity**:
   ```bash
   ping <sensor_ip>
   telnet <sensor_ip> <port>
   ```

2. **Check UDP Ports**:
   ```bash
   netstat -ulpn | grep <port>
   ```

3. **Check TCP Connections**:
   ```bash
   netstat -tlpn | grep <port>
   ```

#### Performance Issues

1. **Check Resource Usage**:
   ```bash
   top -p $(pgrep -f "python app.py")
   ```

2. **Check Processing Latency**:
   ```bash
   grep "processing_latency" logs/thebox.log
   ```

3. **Check Memory Usage**:
   ```bash
   ps aux | grep "python app.py"
   ```

### Error Resolution

#### Database Errors

1. **Check Database Status**:
   ```bash
   curl http://localhost:5000/health/database
   ```

2. **Restart Application**:
   ```bash
   pkill -f "python app.py"
   python app.py
   ```

3. **Check Database Logs**:
   ```bash
   grep "database" logs/thebox.log
   ```

#### Event System Errors

1. **Check Event Manager**:
   ```bash
   curl http://localhost:5000/health/event_manager
   ```

2. **Check Event Logs**:
   ```bash
   grep "event" logs/thebox.log
   ```

3. **Restart Event System**:
   ```bash
   pkill -f "python app.py"
   python app.py
   ```

#### Plugin Errors

1. **Check Plugin Status**:
   ```bash
   curl http://localhost:5000/health/plugins
   ```

2. **Check Plugin Logs**:
   ```bash
   grep "<plugin_name>" logs/thebox.log
   ```

3. **Restart Plugin**:
   ```bash
   pkill -f "python app.py"
   python app.py
   ```

### Emergency Procedures

#### System Failure

1. **Immediate Actions**:
   - Check system status
   - Review error logs
   - Restart application
   - Notify stakeholders

2. **Recovery Steps**:
   - Verify configuration
   - Check dependencies
   - Run smoke test
   - Monitor system

3. **Post-Incident**:
   - Document incident
   - Analyze root cause
   - Implement fixes
   - Update procedures

#### Sensor Failure

1. **Immediate Actions**:
   - Check sensor connectivity
   - Verify configuration
   - Check network settings
   - Restart sensor if possible

2. **Recovery Steps**:
   - Test sensor connection
   - Verify data flow
   - Check processing
   - Monitor system

3. **Post-Incident**:
   - Document failure
   - Analyze cause
   - Implement fixes
   - Update procedures

#### Performance Degradation

1. **Immediate Actions**:
   - Check resource usage
   - Review performance logs
   - Identify bottlenecks
   - Optimize configuration

2. **Recovery Steps**:
   - Restart application
   - Optimize settings
   - Monitor performance
   - Verify improvements

3. **Post-Incident**:
   - Document issues
   - Analyze causes
   - Implement optimizations
   - Update procedures

## Backup and Recovery

### Backup Procedures

#### Configuration Backup

1. **Backup Configuration**:
   ```bash
   cp .env config_backup_$(date +%Y%m%d).env
   cp config.json config_backup_$(date +%Y%m%d).json
   ```

2. **Backup Database**:
   ```bash
   cp thebox_mvp.sqlite db_backup_$(date +%Y%m%d).sqlite
   ```

3. **Backup Logs**:
   ```bash
   tar -czf logs_backup_$(date +%Y%m%d).tar.gz logs/
   ```

#### Code Backup

1. **Backup Source Code**:
   ```bash
   tar -czf source_backup_$(date +%Y%m%d).tar.gz --exclude=venv* --exclude=__pycache__ .
   ```

2. **Backup Dependencies**:
   ```bash
   pip freeze > requirements_backup_$(date +%Y%m%d).txt
   ```

### Recovery Procedures

#### Configuration Recovery

1. **Restore Configuration**:
   ```bash
   cp config_backup_<date>.env .env
   cp config_backup_<date>.json config.json
   ```

2. **Restart Application**:
   ```bash
   pkill -f "python app.py"
   python app.py
   ```

#### Database Recovery

1. **Restore Database**:
   ```bash
   cp db_backup_<date>.sqlite thebox_mvp.sqlite
   ```

2. **Restart Application**:
   ```bash
   pkill -f "python app.py"
   python app.py
   ```

#### Code Recovery

1. **Restore Source Code**:
   ```bash
   tar -xzf source_backup_<date>.tar.gz
   ```

2. **Restore Dependencies**:
   ```bash
   pip install -r requirements_backup_<date>.txt
   ```

3. **Restart Application**:
   ```bash
   pkill -f "python app.py"
   python app.py
   ```

## Security Procedures

### Security Monitoring

#### Vulnerability Scanning

1. **Dependency Scan**:
   ```bash
   safety check
   ```

2. **Secret Scan**:
   ```bash
   bandit -r .
   ```

3. **SBOM Generation**:
   ```bash
   cyclonedx-py -o sbom.json
   ```

#### Access Control

1. **User Access**:
   - Review user accounts
   - Check permissions
   - Verify access logs

2. **Network Access**:
   - Review firewall rules
   - Check network logs
   - Verify port access

### Security Updates

#### Dependency Updates

1. **Check for Updates**:
   ```bash
   pip list --outdated
   ```

2. **Update Dependencies**:
   ```bash
   pip install --upgrade <package>
   ```

3. **Verify Updates**:
   ```bash
   pip check
   safety check
   ```

#### Configuration Updates

1. **Review Configuration**:
   ```bash
   python scripts/validate_plugin_conformance.py --config
   ```

2. **Update Configuration**:
   ```bash
   # Edit configuration files
   # Restart application
   ```

3. **Verify Updates**:
   ```bash
   python scripts/smoke_test.py
   ```

## Performance Tuning

### Configuration Tuning

#### Network Configuration

1. **UDP Buffer Sizes**:
   ```bash
   # Increase UDP buffer sizes
   echo 'net.core.rmem_max = 134217728' >> /etc/sysctl.conf
   echo 'net.core.rmem_default = 134217728' >> /etc/sysctl.conf
   sysctl -p
   ```

2. **TCP Buffer Sizes**:
   ```bash
   # Increase TCP buffer sizes
   echo 'net.core.wmem_max = 134217728' >> /etc/sysctl.conf
   echo 'net.core.wmem_default = 134217728' >> /etc/sysctl.conf
   sysctl -p
   ```

#### Application Configuration

1. **Worker Processes**:
   ```bash
   # Set number of worker processes
   export WORKER_PROCESSES=4
   ```

2. **Memory Limits**:
   ```bash
   # Set memory limits
   export MAX_MEMORY=2G
   ```

### Plugin Tuning

#### Processing Optimization

1. **Batch Processing**:
   ```bash
   # Enable batch processing
   export BATCH_PROCESSING=true
   export BATCH_SIZE=100
   ```

2. **Async Processing**:
   ```bash
   # Enable async processing
   export ASYNC_PROCESSING=true
   export ASYNC_WORKERS=4
   ```

#### Memory Optimization

1. **Cache Settings**:
   ```bash
   # Set cache size
   export CACHE_SIZE=1000
   export CACHE_TTL=3600
   ```

2. **Garbage Collection**:
   ```bash
   # Set garbage collection
   export GC_THRESHOLD=1000
   export GC_INTERVAL=60
   ```

## Contact Information

### Support Contacts

- **Primary Support**: [Your Name] - [email/phone]
- **Secondary Support**: [Backup Contact] - [email/phone]
- **Emergency Support**: [Emergency Contact] - [email/phone]

### Escalation Procedures

1. **Level 1**: Local troubleshooting
2. **Level 2**: Remote support
3. **Level 3**: Vendor support
4. **Level 4**: Emergency escalation

### Documentation

- **System Documentation**: `docs/`
- **API Documentation**: `docs/API_REFERENCE.md`
- **Configuration Guide**: `docs/CONFIG_REFERENCE.md`
- **Troubleshooting Guide**: `docs/TROUBLESHOOTING.md`
