# Changelog

All notable changes to the Dspnor plugin will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-01-16

### Added
- Initial release of Dspnor plugin for Dronnur-2D Naval LPI/LPD radar
- Multicast discovery of radar units
- D2D protocol implementation for radar control
- CAT-010 track parsing per ICD specification
- NMEA heading/GPS integration
- Bow-relative bearing conversion
- Service configuration (UDP/TCP)
- Safe mode operation
- Comprehensive metrics collection
- Web interface for status monitoring
- Unit tests for core functionality
- Documentation and troubleshooting guide

### Features
- **Discovery**: Automatic discovery of radar units via multicast
- **Control**: Full D2D protocol implementation for radar control
- **Parsing**: Complete CAT-010 parser supporting all ICD items
- **NMEA**: RMC/VTG/GGA/HDG sentence parsing
- **Normalization**: Conversion to TheBox detection format
- **Safety**: Safe mode and dangerous operation guards
- **Monitoring**: Real-time status and metrics
- **Configuration**: Environment-based configuration

### Technical Details
- Supports CAT-010 items: 140, 161, 040, 041, 042, 200, 202, 220, 245
- MMSI bit-54 detection in I010/245
- Polar and cartesian position handling
- True to bow-relative bearing conversion
- Confidence mapping and unit conversion
- Rate limiting and reconnection logic
- Comprehensive error handling

### Configuration
- 25+ environment variables for full control
- Safe mode for read-only operation
- Dangerous operation guards
- Flexible unit and protocol configuration

### Testing
- Unit tests for all major components
- Discovery and D2D protocol tests
- CAT-010 parser tests
- NMEA parser tests
- Normalizer tests
- Integration test framework

### Documentation
- Comprehensive README with architecture overview
- Configuration reference
- Troubleshooting guide
- API documentation
- Security considerations

## [Unreleased]

### Planned Features
- Integration tests with sample data
- Performance optimization
- Additional NMEA sentence support
- Enhanced error recovery
- Configuration validation
- Logging improvements
- Metrics export
- Health check endpoints

### Known Issues
- None at this time

### Breaking Changes
- None at this time
