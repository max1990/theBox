# Changelog

All notable changes to TheBox will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-12-19

### Added
- **Core Application**: Flask-based main application with plugin architecture
- **Plugin System**: Modular plugin interface for sensor integration
- **Event Manager**: Centralized event system for inter-plugin communication
- **Database**: In-memory DroneDB for state management and event persistence
- **Web UI**: Settings and monitoring interface with modern design
- **Sensor Plugins**: Complete integration for all supported sensors
  - DroneShield DS-X Mk2 (RF detection)
  - Silvus FASST (RF spectrum analysis)
  - Trakka TC-300 (EO/IR camera control)
  - MARA Spotter (EO/IR/Acoustic detection)
  - Dspnor Dronnur 2D (LPI/LPD radar)
- **MVP Framework**: Modular components for detection processing
  - Confidence fusion with Bayesian log-odds
  - Range estimation with multiple algorithms
  - Vision processing with computer vision
  - Bearing normalization utilities
  - Environment configuration management
- **Docker Support**: Containerized deployment for multiple platforms
  - Windows + NVIDIA RTX workstation
  - Jetson L4T/JetPack
  - Docker Compose orchestration
- **Testing Framework**: Comprehensive test suite with validation
  - Unit tests for all components
  - Integration tests for plugin interactions
  - Smoke tests for end-to-end validation
  - Plugin conformance validation
  - Performance and security tests
- **Documentation**: Complete documentation set
  - Quickstart guides for all platforms
  - Configuration reference with examples
  - API documentation with schemas
  - Troubleshooting and operations guides
  - System architecture diagrams
- **Security**: Security hardening and compliance
  - Dependency vulnerability scanning
  - Secret detection and prevention
  - SBOM generation for supply chain security
  - Security configuration guidelines
- **Performance**: Performance monitoring and optimization
  - Ingest rate monitoring
  - Latency measurement
  - Memory and CPU usage tracking
  - Fail-open behavior for reliability
- **Reliability**: Robust error handling and recovery
  - Structured logging with JSON output
  - Graceful shutdown and restart
  - Exponential backoff for retries
  - Health monitoring endpoints
- **Configuration**: Flexible environment-based configuration
  - Environment variable management
  - JSON Schema validation
  - Platform-specific settings
  - Runtime configuration updates

### Changed
- **Bearing Normalization**: All bearings now normalized to bow-relative (0°/0 rad)
- **JSON Schemas**: Standardized payload formats across all plugins
- **Plugin Interfaces**: Unified plugin interface with consistent error handling
- **Event System**: Improved event routing and filtering
- **Database Schema**: Optimized for detection and track storage
- **Web UI**: Modernized interface with better usability
- **Logging**: Switched to structured logging for better observability
- **Configuration**: Centralized configuration management
- **Testing**: Enhanced test coverage and validation

### Fixed
- **Plugin Loading**: Fixed plugin discovery and loading issues
- **Bearing Calculations**: Corrected bearing normalization across all plugins
- **Event Routing**: Fixed event subscription and publication
- **Database Locking**: Resolved race conditions in database access
- **Memory Leaks**: Fixed memory leaks in long-running processes
- **Error Handling**: Improved error handling and recovery
- **Configuration**: Fixed environment variable parsing and validation
- **Docker**: Resolved Docker build and runtime issues
- **Tests**: Fixed flaky tests and improved reliability

### Security
- **Dependency Scanning**: Regular vulnerability scanning with Safety
- **Secret Detection**: Automated secret detection with Bandit
- **SBOM Generation**: Software Bill of Materials for supply chain security
- **Configuration Security**: Secure default configurations
- **Network Security**: Proper network binding and access controls
- **Data Protection**: Sensitive data handling and logging controls

### Performance
- **Detection Processing**: Optimized detection processing pipeline
- **Memory Usage**: Reduced memory footprint and improved garbage collection
- **CPU Usage**: Optimized CPU usage for better performance
- **Network I/O**: Improved network efficiency and error handling
- **Database Operations**: Optimized database queries and operations
- **Plugin Loading**: Faster plugin discovery and loading

### Documentation
- **API Documentation**: Complete API reference with examples
- **Configuration Guide**: Comprehensive configuration reference
- **Quickstart Guides**: Platform-specific quickstart instructions
- **Architecture Diagrams**: Visual system architecture documentation
- **Troubleshooting**: Common issues and solutions guide
- **Operations Guide**: Production deployment and operations guide

### Testing
- **Unit Tests**: Comprehensive unit test coverage
- **Integration Tests**: End-to-end integration testing
- **Performance Tests**: Performance and load testing
- **Security Tests**: Security vulnerability testing
- **Smoke Tests**: Automated smoke testing for deployment validation
- **Plugin Tests**: Plugin-specific testing and validation

### Infrastructure
- **CI/CD**: GitHub Actions workflow for automated testing
- **Docker**: Multi-platform Docker support
- **Monitoring**: Health checks and performance monitoring
- **Logging**: Centralized logging with structured output
- **Configuration**: Environment-based configuration management
- **Deployment**: Automated deployment scripts and procedures

## [0.9.0] - 2024-12-18

### Added
- Initial plugin architecture
- Basic sensor integration
- Event system foundation
- Database implementation
- Web interface prototype

### Changed
- Refactored plugin system
- Improved event handling
- Enhanced database schema
- Updated web interface

### Fixed
- Plugin loading issues
- Event routing problems
- Database concurrency issues
- Web interface bugs

## [0.8.0] - 2024-12-17

### Added
- Core application structure
- Basic plugin interface
- Event manager implementation
- Database abstraction layer
- Web UI framework

### Changed
- Restructured project layout
- Improved code organization
- Enhanced error handling
- Updated dependencies

### Fixed
- Import path issues
- Configuration problems
- Database connection issues
- Web interface errors

## [0.7.0] - 2024-12-16

### Added
- Project initialization
- Basic Flask application
- Plugin system foundation
- Event system prototype
- Database implementation

### Changed
- Project structure
- Code organization
- Dependencies
- Configuration

### Fixed
- Initial setup issues
- Import problems
- Configuration errors
- Database issues

## [0.6.0] - 2024-12-15

### Added
- Repository setup
- Basic project structure
- Initial documentation
- Development environment
- Testing framework

### Changed
- Project organization
- Documentation structure
- Development workflow
- Testing approach

### Fixed
- Setup issues
- Documentation problems
- Development environment
- Testing configuration

## [0.5.0] - 2024-12-14

### Added
- Project conception
- Requirements analysis
- Architecture design
- Technology selection
- Initial planning

### Changed
- Project scope
- Architecture decisions
- Technology choices
- Implementation approach

### Fixed
- Planning issues
- Architecture problems
- Technology conflicts
- Implementation challenges

## [0.4.0] - 2024-12-13

### Added
- Initial research
- Technology evaluation
- Architecture planning
- Requirements gathering
- Project setup

### Changed
- Research direction
- Technology choices
- Architecture decisions
- Requirements scope

### Fixed
- Research gaps
- Technology issues
- Architecture problems
- Requirements conflicts

## [0.3.0] - 2024-12-12

### Added
- Project initiation
- Initial research
- Technology exploration
- Architecture planning
- Requirements analysis

### Changed
- Project direction
- Research focus
- Technology approach
- Architecture design

### Fixed
- Initial setup issues
- Research problems
- Technology conflicts
- Architecture challenges

## [0.2.0] - 2024-12-11

### Added
- Project concept
- Initial planning
- Technology research
- Architecture exploration
- Requirements gathering

### Changed
- Project scope
- Planning approach
- Research direction
- Architecture decisions

### Fixed
- Planning issues
- Research gaps
- Architecture problems
- Requirements conflicts

## [0.1.0] - 2024-12-10

### Added
- Project initialization
- Basic planning
- Initial research
- Technology exploration
- Architecture planning

### Changed
- Project direction
- Planning approach
- Research focus
- Technology choices

### Fixed
- Initial setup issues
- Planning problems
- Research gaps
- Technology conflicts

## [0.0.1] - 2024-12-09

### Added
- Initial project setup
- Basic repository structure
- Initial documentation
- Development environment
- Basic testing

### Changed
- Project organization
- Documentation structure
- Development workflow
- Testing approach

### Fixed
- Setup issues
- Documentation problems
- Development environment
- Testing configuration

## [0.0.0] - 2024-12-08

### Added
- Project conception
- Initial planning
- Repository setup
- Basic structure
- Initial documentation

### Changed
- Project scope
- Planning approach
- Repository organization
- Documentation structure

### Fixed
- Initial setup issues
- Planning problems
- Repository organization
- Documentation structure
