# TheBox Release Notes - field_demo_2024-12-19

## Overview

This release contains the complete TheBox system for field deployment.

## Components

- **Core Application**: Main Flask application with plugin architecture
- **Sensor Plugins**: Integration for DroneShield, Silvus, Trakka, MARA, Dspnor
- **MVP Framework**: Modular components for detection processing
- **Web UI**: Settings and monitoring interface
- **Docker Support**: Containerized deployment for Windows and Jetson
- **Test Suite**: Comprehensive validation and smoke tests
- **Documentation**: Complete runbooks and configuration guides

## Quick Start

### Windows
```powershell
# Set environment
.\scripts\windows\SET_ENV.ps1

# Run application
python app.py
```

### Jetson
```bash
# Set environment
source scripts/setup_jetson.sh

# Run application
python app.py
```

### Docker
```bash
# Workstation
docker-compose up

# Jetson
docker-compose -f docker-compose.jetson.yml up
```

## Configuration

1. Copy `config/env.sample` to `.env`
2. Edit `.env` with your specific settings
3. Run smoke test: `python scripts/smoke_test.py`

## Validation

Run the complete test suite:
```bash
python scripts/run_tests.py --coverage
```

## Support

See `docs/` directory for detailed documentation and troubleshooting.

## Security

- SBOM files available in `sbom/` directory
- Security report in `docs/SECURITY_REPORT.md`
- All dependencies pinned to specific versions

## Performance

- Performance notes in `docs/PERF_NOTES.md`
- Monitoring probes available
- Fail-open behavior implemented

## Changelog

- Initial release
- Complete plugin architecture
- Docker support for Windows and Jetson
- Comprehensive test suite
- Security hardening
- Performance monitoring
