# Testing Guide for TheBox

## Overview

TheBox uses a comprehensive testing strategy with deterministic seeds, clear reporting, and multiple test types.

## Test Structure

```
tests/
├── unit/                    # Unit tests for individual components
│   ├── test_confidence_fusion.py
│   ├── test_range_estimation.py
│   └── ...
├── integration/             # Integration tests for plugin interactions
│   ├── test_plugin_communication.py
│   └── ...
├── plugins/                 # Plugin-specific tests
│   ├── test_droneshield.py
│   ├── test_silvus.py
│   └── ...
└── test_*.py               # Top-level test files
```

## Running Tests

### Basic Test Execution

```bash
# Run all tests
python scripts/run_tests.py

# Run with verbose output
python scripts/run_tests.py --verbose

# Run with coverage
python scripts/run_tests.py --coverage

# Run specific test suite
python scripts/run_tests.py --suite confidence
python scripts/run_tests.py --suite range
python scripts/run_tests.py --suite plugins

# Run specific test file
python scripts/run_tests.py --path tests/test_confidence_fusion.py

# Run tests in parallel
python scripts/run_tests.py --parallel
```

### Using pytest directly

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_confidence_fusion.py

# Run with markers
pytest -m "confidence"
pytest -m "unit"
pytest -m "integration"

# Run with coverage
pytest --cov=mvp --cov=plugins --cov-report=html

# Run in parallel
pytest -n auto
```

## Test Types

### Unit Tests

Test individual components in isolation:

```python
def test_confidence_fusion_basic():
    """Test basic confidence fusion logic"""
    # Test implementation
    pass
```

### Integration Tests

Test component interactions:

```python
def test_plugin_communication():
    """Test plugin event communication"""
    # Test implementation
    pass
```

### Plugin Tests

Test specific plugin functionality:

```python
def test_droneshield_detection():
    """Test DroneShield detection processing"""
    # Test implementation
    pass
```

## Deterministic Testing

All tests use deterministic seeds for reproducible results:

- `PYTHONHASHSEED=0`
- `RANDOM_SEED=42`
- Fixed test data and timestamps

## Test Data

Test data is stored in `tests/data/` and includes:

- Sample sensor data
- Mock detection events
- Expected output files
- Test configuration files

## Coverage

Coverage reports are generated in HTML format:

```bash
# Generate coverage report
python scripts/run_tests.py --coverage

# View coverage report
open htmlcov/index.html
```

## Continuous Integration

Tests run automatically on:

- Pull requests
- Main branch pushes
- Release tags

## Test Environment

Tests use a clean environment with:

- Mock external dependencies
- In-memory database
- Test-specific configuration
- Isolated plugin instances

## Debugging Tests

### Verbose Output

```bash
python scripts/run_tests.py --verbose
```

### Specific Test

```bash
pytest tests/test_confidence_fusion.py::test_confidence_fusion_basic -v
```

### Debug Mode

```bash
pytest --pdb tests/test_confidence_fusion.py
```

## Test Markers

- `unit`: Unit tests
- `integration`: Integration tests
- `slow`: Slow tests
- `gpu`: GPU-required tests
- `jetson`: Jetson-specific tests
- `confidence`: Confidence fusion tests
- `range`: Range estimation tests
- `plugins`: Plugin tests
- `deterministic`: Deterministic tests

## Best Practices

1. **Use descriptive test names** that explain what is being tested
2. **Test both success and failure cases**
3. **Use deterministic data** for reproducible results
4. **Mock external dependencies** to isolate components
5. **Test edge cases** and boundary conditions
6. **Keep tests fast** and focused
7. **Use fixtures** for common test setup
8. **Document test assumptions** and expected behavior

## Troubleshooting

### Common Issues

1. **Import errors**: Ensure project root is in Python path
2. **Environment issues**: Check `.env` file and environment variables
3. **Plugin loading**: Verify plugin dependencies are available
4. **Database issues**: Ensure test database is properly initialized

### Debug Commands

```bash
# Check Python path
python -c "import sys; print(sys.path)"

# Check environment
python -c "from mvp.env_loader import load_thebox_env; load_thebox_env(); import os; print(os.environ)"

# Check plugin loading
python -c "from thebox.plugin_manager import PluginManager; pm = PluginManager(); print(pm.plugins)"
```

## Performance Testing

Performance tests measure:

- Detection processing latency
- Event throughput
- Memory usage
- CPU utilization

Run performance tests:

```bash
python scripts/run_tests.py --suite performance
```

## Security Testing

Security tests check for:

- Input validation
- Authentication
- Authorization
- Data sanitization

Run security tests:

```bash
python scripts/run_tests.py --suite security
```

## Test Maintenance

- Update tests when changing functionality
- Remove obsolete tests
- Refactor common test code
- Keep test data current
- Monitor test performance
