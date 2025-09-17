# Troubleshooting Guide

## Overview

This guide provides solutions to common issues encountered when deploying and operating TheBox system.

## Quick Diagnostics

### System Health Check

```bash
# Check overall system health
python scripts/health_check.py

# Check plugin conformance
python scripts/validate_plugin_conformance.py

# Run smoke test
python scripts/smoke_test.py
```

### Log Analysis

```bash
# Check for errors
grep "ERROR" logs/thebox.log

# Check for warnings
grep "WARNING" logs/thebox.log

# Check specific plugin logs
grep "droneshield" logs/thebox.log
```

## Common Issues

### Application Won't Start

#### Symptoms
- Application fails to start
- Error messages during startup
- Port binding errors

#### Causes
1. **Port Already in Use**
2. **Missing Dependencies**
3. **Configuration Errors**
4. **Permission Issues**

#### Solutions

**1. Port Already in Use**
```bash
# Check if port is in use
netstat -tulpn | grep :5000

# Kill process using port
sudo lsof -ti:5000 | xargs kill -9

# Or change port in configuration
export FLASK_PORT=5001
```

**2. Missing Dependencies**
```bash
# Install dependencies
pip install -r requirements.txt

# Check for missing packages
pip check

# Install specific package
pip install <package_name>
```

**3. Configuration Errors**
```bash
# Validate configuration
python scripts/validate_plugin_conformance.py --config

# Check environment variables
python -c "from mvp.env_loader import load_thebox_env; load_thebox_env(); import os; print(os.environ)"

# Reset to default configuration
cp docs/env.sample .env
```

**4. Permission Issues**
```bash
# Check file permissions
ls -la app.py

# Fix permissions
chmod +x app.py

# Check directory permissions
ls -la logs/
chmod 755 logs/
```

### Plugin Loading Issues

#### Symptoms
- Plugins not loading
- Plugin errors in logs
- Missing plugin functionality

#### Causes
1. **Plugin Dependencies Missing**
2. **Plugin Configuration Errors**
3. **Plugin Code Errors**
4. **Import Path Issues**

#### Solutions

**1. Plugin Dependencies Missing**
```bash
# Check plugin dependencies
python scripts/validate_plugin_conformance.py --plugin <plugin_name>

# Install missing dependencies
pip install <missing_package>

# Check plugin requirements
cat plugins/<plugin_name>/requirements.txt
```

**2. Plugin Configuration Errors**
```bash
# Check plugin configuration
grep "<plugin_name>" .env

# Validate plugin configuration
python scripts/validate_plugin_conformance.py --config

# Reset plugin configuration
# Edit .env file with correct values
```

**3. Plugin Code Errors**
```bash
# Check plugin syntax
python -m py_compile plugins/<plugin_name>/plugin.py

# Check plugin imports
python -c "import plugins.<plugin_name>.plugin"

# Check plugin logs
grep "<plugin_name>" logs/thebox.log
```

**4. Import Path Issues**
```bash
# Check Python path
python -c "import sys; print(sys.path)"

# Add project root to path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Check plugin imports
python -c "from plugins.<plugin_name> import plugin"
```

### Sensor Connection Issues

#### Symptoms
- Sensors not connecting
- No data received from sensors
- Connection timeouts

#### Causes
1. **Network Configuration Issues**
2. **Firewall Blocking**
3. **Sensor Configuration Errors**
4. **Hardware Issues**

#### Solutions

**1. Network Configuration Issues**
```bash
# Check network connectivity
ping <sensor_ip>

# Check port availability
telnet <sensor_ip> <port>

# Check network configuration
ip addr show
ip route show
```

**2. Firewall Blocking**
```bash
# Check firewall status
sudo ufw status

# Allow specific ports
sudo ufw allow 50001/udp
sudo ufw allow 50002/udp
sudo ufw allow 8080/tcp

# Check iptables rules
sudo iptables -L
```

**3. Sensor Configuration Errors**
```bash
# Check sensor configuration
grep "UDP_PORT" .env
grep "TCP_HOST" .env

# Validate sensor settings
python scripts/validate_plugin_conformance.py --sensors

# Test sensor connection
python scripts/test_sensor_connection.py
```

**4. Hardware Issues**
```bash
# Check hardware status
lspci | grep -i network
lsusb | grep -i serial

# Check device permissions
ls -la /dev/ttyUSB*
ls -la /dev/ttyACM*

# Fix device permissions
sudo chmod 666 /dev/ttyUSB*
sudo chmod 666 /dev/ttyACM*
```

### Performance Issues

#### Symptoms
- Slow detection processing
- High CPU usage
- Memory leaks
- System instability

#### Causes
1. **Resource Exhaustion**
2. **Configuration Issues**
3. **Memory Leaks**
4. **Processing Bottlenecks**

#### Solutions

**1. Resource Exhaustion**
```bash
# Check system resources
top -p $(pgrep -f "python app.py")
htop

# Check memory usage
free -h
ps aux | grep python

# Check disk usage
df -h
du -sh logs/
```

**2. Configuration Issues**
```bash
# Check configuration
python scripts/validate_plugin_conformance.py --config

# Optimize configuration
python scripts/optimize_config.py

# Check performance settings
grep "PERFORMANCE" .env
```

**3. Memory Leaks**
```bash
# Monitor memory usage
python scripts/memory_monitor.py

# Check for memory leaks
python scripts/check_memory_leaks.py

# Restart application
pkill -f "python app.py"
python app.py
```

**4. Processing Bottlenecks**
```bash
# Check processing latency
grep "processing_latency" logs/thebox.log

# Check detection rate
grep "detection_rate" logs/thebox.log

# Optimize processing
python scripts/optimize_processing.py
```

### Database Issues

#### Symptoms
- Database errors
- Data corruption
- Performance issues
- Connection failures

#### Causes
1. **Database Corruption**
2. **Memory Issues**
3. **Concurrency Issues**
4. **Configuration Errors**

#### Solutions

**1. Database Corruption**
```bash
# Check database status
curl http://localhost:5000/health/database

# Backup database
cp thebox_mvp.sqlite thebox_mvp.sqlite.backup

# Recreate database
rm thebox_mvp.sqlite
python app.py
```

**2. Memory Issues**
```bash
# Check memory usage
ps aux | grep python

# Check database memory
python scripts/check_database_memory.py

# Optimize database
python scripts/optimize_database.py
```

**3. Concurrency Issues**
```bash
# Check for deadlocks
grep "deadlock" logs/thebox.log

# Check for race conditions
grep "race" logs/thebox.log

# Restart application
pkill -f "python app.py"
python app.py
```

**4. Configuration Errors**
```bash
# Check database configuration
grep "DATABASE" .env

# Validate database settings
python scripts/validate_database_config.py

# Reset database configuration
# Edit .env file with correct values
```

### Web Interface Issues

#### Symptoms
- Web interface not loading
- API endpoints not responding
- Static files not loading
- JavaScript errors

#### Causes
1. **Web Server Issues**
2. **Static File Issues**
3. **API Endpoint Errors**
4. **Browser Compatibility**

#### Solutions

**1. Web Server Issues**
```bash
# Check web server status
curl http://localhost:5000/health

# Check web server logs
grep "web" logs/thebox.log

# Restart web server
pkill -f "python app.py"
python app.py
```

**2. Static File Issues**
```bash
# Check static files
ls -la static/
ls -la templates/

# Check file permissions
chmod -R 755 static/
chmod -R 755 templates/

# Check file paths
grep "static" app.py
```

**3. API Endpoint Errors**
```bash
# Test API endpoints
curl http://localhost:5000/health
curl http://localhost:5000/status
curl http://localhost:5000/plugins

# Check API logs
grep "api" logs/thebox.log

# Check endpoint configuration
grep "@app.route" app.py
```

**4. Browser Compatibility**
```bash
# Check browser console
# Open browser developer tools
# Check for JavaScript errors

# Check HTML validation
# Use online HTML validator

# Check CSS validation
# Use online CSS validator
```

## Advanced Troubleshooting

### Debug Mode

Enable debug mode for detailed logging:

```bash
# Set debug environment variable
export DEBUG=true
export LOG_LEVEL=DEBUG

# Start application in debug mode
python app.py
```

### Profiling

Profile application performance:

```bash
# Install profiling tools
pip install py-spy

# Profile CPU usage
py-spy top --pid $(pgrep -f "python app.py")

# Profile memory usage
py-spy record --pid $(pgrep -f "python app.py") --output profile.svg
```

### Network Analysis

Analyze network traffic:

```bash
# Install network tools
sudo apt-get install tcpdump wireshark

# Capture network traffic
sudo tcpdump -i any -w thebox.pcap port 50001 or port 50002 or port 8080

# Analyze captured traffic
wireshark thebox.pcap
```

### System Monitoring

Monitor system resources:

```bash
# Install monitoring tools
pip install psutil

# Monitor system resources
python scripts/system_monitor.py

# Monitor specific processes
python scripts/process_monitor.py
```

## Diagnostic Scripts

### Health Check Script

```bash
#!/bin/bash
# Comprehensive health check

echo "=== TheBox Health Check ==="
echo "Date: $(date)"
echo ""

# Check system health
echo "1. System Health:"
python scripts/health_check.py
echo ""

# Check plugin conformance
echo "2. Plugin Conformance:"
python scripts/validate_plugin_conformance.py
echo ""

# Check configuration
echo "3. Configuration:"
python scripts/validate_plugin_conformance.py --config
echo ""

# Check sensors
echo "4. Sensors:"
python scripts/validate_plugin_conformance.py --sensors
echo ""

# Run smoke test
echo "5. Smoke Test:"
python scripts/smoke_test.py
echo ""

echo "=== Health Check Complete ==="
```

### Performance Analysis Script

```bash
#!/bin/bash
# Performance analysis

echo "=== TheBox Performance Analysis ==="
echo "Date: $(date)"
echo ""

# Check CPU usage
echo "1. CPU Usage:"
top -bn1 | grep "python app.py"
echo ""

# Check memory usage
echo "2. Memory Usage:"
ps aux | grep "python app.py"
echo ""

# Check disk usage
echo "3. Disk Usage:"
df -h
echo ""

# Check network usage
echo "4. Network Usage:"
netstat -i
echo ""

# Check log sizes
echo "5. Log Sizes:"
du -sh logs/
echo ""

echo "=== Performance Analysis Complete ==="
```

### Sensor Test Script

```bash
#!/bin/bash
# Sensor connectivity test

echo "=== Sensor Connectivity Test ==="
echo "Date: $(date)"
echo ""

# Test DroneShield
echo "1. DroneShield:"
ping -c 1 $(grep "UDP_HOST_DRONESHIELD" .env | cut -d'=' -f2) 2>/dev/null && echo "✓ Reachable" || echo "✗ Unreachable"
echo ""

# Test Silvus
echo "2. Silvus:"
ping -c 1 $(grep "UDP_HOST_SILVUS" .env | cut -d'=' -f2) 2>/dev/null && echo "✓ Reachable" || echo "✗ Unreachable"
echo ""

# Test Trakka
echo "3. Trakka:"
ping -c 1 $(grep "TCP_HOST_TRAKKA" .env | cut -d'=' -f2) 2>/dev/null && echo "✓ Reachable" || echo "✗ Unreachable"
echo ""

# Test MARA
echo "4. MARA:"
ping -c 1 $(grep "UDP_HOST_MARA" .env | cut -d'=' -f2) 2>/dev/null && echo "✓ Reachable" || echo "✗ Unreachable"
echo ""

# Test Dspnor
echo "5. Dspnor:"
ping -c 1 $(grep "UDP_HOST_DSPNOR" .env | cut -d'=' -f2) 2>/dev/null && echo "✓ Reachable" || echo "✗ Unreachable"
echo ""

echo "=== Sensor Test Complete ==="
```

## Recovery Procedures

### System Recovery

1. **Stop Application**:
   ```bash
   pkill -f "python app.py"
   ```

2. **Backup Data**:
   ```bash
   cp thebox_mvp.sqlite thebox_mvp.sqlite.backup
   cp -r logs/ logs_backup/
   ```

3. **Reset Configuration**:
   ```bash
   cp docs/env.sample .env
   ```

4. **Restart Application**:
   ```bash
   python app.py
   ```

### Plugin Recovery

1. **Stop Application**:
   ```bash
   pkill -f "python app.py"
   ```

2. **Check Plugin Dependencies**:
   ```bash
   python scripts/validate_plugin_conformance.py --plugin <plugin_name>
   ```

3. **Fix Plugin Issues**:
   ```bash
   # Fix configuration
   # Install dependencies
   # Fix code issues
   ```

4. **Restart Application**:
   ```bash
   python app.py
   ```

### Database Recovery

1. **Stop Application**:
   ```bash
   pkill -f "python app.py"
   ```

2. **Backup Database**:
   ```bash
   cp thebox_mvp.sqlite thebox_mvp.sqlite.backup
   ```

3. **Recreate Database**:
   ```bash
   rm thebox_mvp.sqlite
   python app.py
   ```

4. **Verify Database**:
   ```bash
   curl http://localhost:5000/health/database
   ```

## Prevention

### Regular Maintenance

1. **Daily Health Checks**:
   ```bash
   python scripts/health_check.py
   ```

2. **Weekly Performance Analysis**:
   ```bash
   python scripts/performance_analysis.py
   ```

3. **Monthly Security Audit**:
   ```bash
   safety check
   bandit -r .
   ```

### Monitoring

1. **System Monitoring**:
   ```bash
   python scripts/system_monitor.py
   ```

2. **Performance Monitoring**:
   ```bash
   python scripts/performance_monitor.py
   ```

3. **Log Monitoring**:
   ```bash
   tail -f logs/thebox.log
   ```

### Backup

1. **Configuration Backup**:
   ```bash
   cp .env config_backup_$(date +%Y%m%d).env
   ```

2. **Database Backup**:
   ```bash
   cp thebox_mvp.sqlite db_backup_$(date +%Y%m%d).sqlite
   ```

3. **Log Backup**:
   ```bash
   tar -czf logs_backup_$(date +%Y%m%d).tar.gz logs/
   ```

## Contact Information

### Support Contacts

- **Technical Support**: [Name] - [email/phone]
- **Emergency Support**: [Name] - [email/phone]
- **Documentation**: [Documentation URL]

### Escalation Procedures

1. **Level 1**: Local troubleshooting
2. **Level 2**: Remote support
3. **Level 3**: Vendor support
4. **Level 4**: Emergency escalation

### Resources

- **Documentation**: `docs/`
- **API Reference**: `docs/API_REFERENCE.md`
- **Configuration Guide**: `docs/CONFIG_REFERENCE.md`
- **Operations Guide**: `docs/OPERATIONS_RUNBOOK.md`
