# Field Demo Preflight Checklist

## Pre-Deployment Verification

### Environment Setup
- [ ] **Environment Variables**: Copy `docs/env.sample` to `.env` and configure
- [ ] **Python Environment**: Verify Python 3.8+ is installed
- [ ] **Dependencies**: Install requirements (`pip install -r requirements.txt`)
- [ ] **Platform Specific**: Install GPU/Jetson requirements if needed
- [ ] **Network Access**: Verify UDP/TCP ports are available
- [ ] **File Permissions**: Ensure write access to data/ and logs/ directories

### System Validation
- [ ] **Smoke Test**: Run `python scripts/smoke_test.py` - should pass
- [ ] **Plugin Validation**: Run `python scripts/validate_plugin_conformance.py`
- [ ] **Health Check**: Run `python scripts/health_check.py` - should return 200
- [ ] **Test Suite**: Run `python scripts/run_tests.py --coverage` - should pass
- [ ] **Docker Images**: Build and test Docker images if using containers

### Sensor Integration
- [ ] **DroneShield**: Verify UDP listener on configured port
- [ ] **Silvus**: Verify UDP listener and bearing normalization
- [ ] **Trakka**: Verify TCP connection and bearing commands
- [ ] **MARA**: Verify UDP listener and detection processing
- [ ] **Dspnor**: Verify UDP listener and radar processing

### Configuration Verification
- [ ] **Bearing Normalization**: All bearings normalized to bow-relative (0°/0 rad)
- [ ] **JSON Schemas**: All plugin inputs/outputs conform to schemas
- [ ] **Environment Variables**: All required variables set with valid values
- [ ] **Logging**: Structured logging configured and working
- [ ] **Performance**: Monitoring probes active and reporting

### Security Checklist
- [ ] **Secrets**: No hardcoded secrets in configuration
- [ ] **Network**: Bind to appropriate interfaces (not 0.0.0.0 in production)
- [ ] **Dependencies**: No known vulnerabilities (check SBOM)
- [ ] **File Access**: Appropriate file permissions set
- [ ] **Logging**: Sensitive data not logged

### Performance Verification
- [ ] **Ingest Rate**: System handles expected detection rate
- [ ] **Latency**: Detection processing latency within acceptable limits
- [ ] **Memory**: Memory usage stable and within limits
- [ ] **CPU**: CPU usage reasonable for platform
- [ ] **Fail-Open**: System continues operating if sensors fail

### Documentation Review
- [ ] **Quickstart Guides**: Review platform-specific quickstart
- [ ] **Configuration Reference**: Verify all settings documented
- [ ] **API Documentation**: Review plugin interfaces and schemas
- [ ] **Troubleshooting**: Review common issues and solutions
- [ ] **Safety Procedures**: Review safety mode and emergency procedures

## Deployment Commands

### Windows Deployment
```powershell
# Set environment
.\\scripts\\windows\\SET_ENV.ps1

# Run smoke test
python scripts/smoke_test.py

# Start application
python app.py
```

### Jetson Deployment
```bash
# Set environment
source scripts/setup_jetson.sh

# Run smoke test
python scripts/smoke_test.py

# Start application
python app.py
```

### Docker Deployment
```bash
# Workstation
docker-compose up

# Jetson
docker-compose -f docker-compose.jetson.yml up
```

## Runtime Monitoring

### Health Checks
- [ ] **Application Health**: Check `/health` endpoint
- [ ] **Plugin Status**: Verify all plugins loaded and healthy
- [ ] **Database**: Verify in-memory database operational
- [ ] **Event Manager**: Verify event system working
- [ ] **Logs**: Check for errors or warnings

### Performance Monitoring
- [ ] **Detection Rate**: Monitor detections per second
- [ ] **Processing Latency**: Monitor end-to-end latency
- [ ] **Memory Usage**: Monitor memory consumption
- [ ] **CPU Usage**: Monitor CPU utilization
- [ ] **Network I/O**: Monitor network traffic

### Sensor Status
- [ ] **DroneShield**: Verify detections being received
- [ ] **Silvus**: Verify AoA data being processed
- [ ] **Trakka**: Verify camera control working
- [ ] **MARA**: Verify vision processing working
- [ ] **Dspnor**: Verify radar data being processed

## Emergency Procedures

### System Failure
1. **Check Logs**: Review application logs for errors
2. **Restart Application**: Stop and restart the application
3. **Check Dependencies**: Verify all required services running
4. **Fallback Mode**: Switch to fail-open mode if available
5. **Contact Support**: Escalate if issues persist

### Sensor Failure
1. **Check Connections**: Verify physical connections
2. **Check Configuration**: Verify sensor settings
3. **Restart Sensor**: Power cycle sensor if possible
4. **Continue Operation**: System should continue with other sensors
5. **Log Incident**: Document failure for analysis

### Performance Issues
1. **Check Resource Usage**: Monitor CPU, memory, network
2. **Reduce Load**: Disable non-essential features
3. **Check Logs**: Look for performance warnings
4. **Restart Services**: Restart if necessary
5. **Optimize Settings**: Adjust configuration if needed

## Post-Demo Cleanup

### Data Collection
- [ ] **Logs**: Collect all application logs
- [ ] **Detections**: Export detection data if needed
- [ ] **Performance**: Collect performance metrics
- [ ] **Configuration**: Document final configuration
- [ ] **Issues**: Document any problems encountered

### System Shutdown
- [ ] **Graceful Shutdown**: Stop application cleanly
- [ ] **Data Backup**: Backup any important data
- [ ] **Cleanup**: Remove temporary files
- [ ] **Reset**: Reset system to initial state
- [ ] **Documentation**: Update documentation with lessons learned

## Success Criteria

### Functional Requirements
- [ ] **Detection Processing**: All sensors providing detections
- [ ] **Bearing Normalization**: All bearings normalized correctly
- [ ] **Event System**: Events flowing between plugins
- [ ] **Web Interface**: Settings and monitoring accessible
- [ ] **Health Monitoring**: Health checks responding

### Performance Requirements
- [ ] **Latency**: < 100ms detection processing
- [ ] **Throughput**: > 10 detections/second
- [ ] **Availability**: > 99% uptime during demo
- [ ] **Memory**: < 2GB memory usage
- [ ] **CPU**: < 50% CPU usage

### Security Requirements
- [ ] **No Vulnerabilities**: No critical security issues
- [ ] **Secure Configuration**: No hardcoded secrets
- [ ] **Network Security**: Appropriate network configuration
- [ ] **Data Protection**: Sensitive data handled securely
- [ ] **Audit Trail**: All actions logged appropriately

## Contact Information

### Technical Support
- **Primary**: [Your Name] - [email/phone]
- **Secondary**: [Backup Contact] - [email/phone]
- **Emergency**: [Emergency Contact] - [email/phone]

### Documentation
- **Quickstart**: `docs/QUICKSTART_*.md`
- **Configuration**: `docs/CONFIG_REFERENCE.md`
- **API**: `docs/API_REFERENCE.md`
- **Troubleshooting**: `docs/TROUBLESHOOTING.md`

### Resources
- **Repository**: [Git Repository URL]
- **Documentation**: [Documentation URL]
- **Support**: [Support URL]
- **Issues**: [Issues URL]
