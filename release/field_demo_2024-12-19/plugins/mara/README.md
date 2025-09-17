# MARA Plugin for TheBox

This plugin ingests MARA Spotter/Seeker data (EO/IR/Acoustic), parses it, validates it, and emits normalized detection events that match TheBox project conventions.

## Features

- **Multi-format Support**: Automatically detects and parses JSON, key=value, and CSV formats
- **Multiple I/O Modes**: UDP server, TCP client, and serial communication
- **Robust Parsing**: Handles malformed data gracefully with comprehensive validation
- **Normalized Output**: Converts MARA data to standardized TheBox detection schema
- **Real-time Processing**: Asynchronous processing with configurable queue management
- **Web Interface**: Built-in status monitoring and configuration

## Supported Data Formats

### JSON Lines
```json
{"timestamp": "2025-01-16T10:30:45.123Z", "sensor_id": "EO_001", "object_id": "obj_123", "confidence": 0.85, "bearing_deg": 45.2, "elevation_deg": 12.5, "range_m": 1500.0, "lat": 40.7128, "lon": -74.0060, "speed_mps": 15.2, "heading_deg": 90.0, "label": "drone", "channel": "EO"}
```

### Key=Value Pairs
```
timestamp=2025-01-16T10:30:45.123Z sensor_id=EO_001 object_id=obj_123 confidence=0.85 bearing_deg=45.2 channel=EO
```

### CSV Format
```
timestamp,sensor_id,object_id,confidence,bearing_deg,elevation_deg,range_m,lat,lon,speed_mps,heading_deg,label,channel
2025-01-16T10:30:45.123Z,EO_001,obj_123,0.85,45.2,12.5,1500.0,40.7128,-74.0060,15.2,90.0,drone,EO
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MARA_ENABLE` | `true` | Enable/disable the plugin |
| `MARA_INPUT_MODE` | `udp` | Input mode: `udp`, `tcp`, or `serial` |
| `MARA_UDP_HOST` | `0.0.0.0` | UDP server bind address |
| `MARA_UDP_PORT` | `8787` | UDP server port |
| `MARA_TCP_HOST` | `127.0.0.1` | TCP server address |
| `MARA_TCP_PORT` | `9000` | TCP server port |
| `MARA_SERIAL_PORT` | `COM5` | Serial port (Windows: `COM5`, Linux: `/dev/ttyUSB0`) |
| `MARA_BAUD` | `115200` | Serial baud rate |
| `OUT_REBROADCAST_ENABLE` | `false` | Enable UDP rebroadcast |
| `OUT_UDP_HOST` | `127.0.0.1` | Rebroadcast UDP host |
| `OUT_UDP_PORT` | `7878` | Rebroadcast UDP port |
| `MARA_HEARTBEAT_SEC` | `10` | Heartbeat interval in seconds |
| `MARA_MAX_QUEUE` | `10000` | Maximum message queue size |

### Example Configuration

Create a `.env` file in the project root:

```bash
# Enable MARA plugin
MARA_ENABLE=true

# Use UDP input
MARA_INPUT_MODE=udp
MARA_UDP_HOST=0.0.0.0
MARA_UDP_PORT=8787

# Enable rebroadcast
OUT_REBROADCAST_ENABLE=true
OUT_UDP_HOST=192.168.1.100
OUT_UDP_PORT=7878

# Logging
LOG_LEVEL=INFO
```

## Usage

### Running the Plugin

The plugin integrates automatically with TheBox when enabled. To run standalone for testing:

```bash
# Set environment variables
set -a && source .env && python -m plugins.mara.plugin

# Or on Windows
set -a && .env && python -m plugins.mara.plugin
```

### Testing with Sample Data

```bash
# Run tests
pytest -q tests/mara

# Test with sample data
python -c "
import asyncio
from plugins.mara.io_udp import MARAUDPReceiver
from plugins.mara.parser import MARAParser

async def test():
    parser = MARAParser()
    def handler(msg):
        detection = parser.autodetect_and_parse(msg)
        if detection:
            print(detection.json())
    
    receiver = MARAUDPReceiver('127.0.0.1', 8787, handler)
    await receiver.start()
    print('Listening on UDP 127.0.0.1:8787...')
    await asyncio.sleep(30)
    await receiver.stop()

asyncio.run(test())
"
```

## Normalized Output Schema

The plugin converts MARA data to the following normalized schema:

```json
{
  "source": "mara",
  "sensor_channel": "EO|IR|ACOUSTIC|UNKNOWN",
  "event_type": "DETECTION|TRACK|HEARTBEAT|STATUS",
  "label": "string|null",
  "confidence": 0.0-1.0,
  "bearing_deg": 0.0-359.9,
  "elev_deg": -90.0 to 90.0,
  "range_km": 0.0-1000.0,
  "lat": -90.0 to 90.0,
  "lon": -180.0 to 180.0,
  "speed_mps": 0.0-1000.0,
  "heading_deg": 0.0-359.9,
  "track_id": "string|int|null",
  "timestamp_utc": "ISO 8601 datetime",
  "raw": "original MARA record"
}
```

## Data Processing

### Field Mapping

- **Sensor Channel**: Maps `channel` field to `EO`, `IR`, `ACOUSTIC`, or `UNKNOWN`
- **Confidence**: Converts percentage (0-100) to decimal (0.0-1.0) if needed
- **Angles**: Normalizes bearing and heading to 0-360 degrees
- **Range**: Converts meters to kilometers automatically
- **Coordinates**: Clamps latitude (-90 to 90) and longitude (-180 to 180)
- **Elevation**: Clamps to -90 to +90 degrees

### Event Type Detection

- **HEARTBEAT**: Contains `heartbeat` or `status` keywords
- **TRACK**: Contains `track_id` or `track` keywords
- **DETECTION**: Default for all other messages

### Error Handling

- Invalid values are set to `None` with logged warnings
- Malformed lines are logged and skipped
- Missing required fields use sensible defaults
- Plugin never crashes on bad input data

## Web Interface

Access the plugin status at `/plugins/MARAPlugin/` when running TheBox:

- **Status Overview**: Connection status, queue size, configuration
- **Real-time Monitoring**: Live updates every 5 seconds
- **Configuration Display**: Current settings and environment variables

## Troubleshooting

### Common Issues

1. **Port Already in Use**
   ```bash
   # Check what's using the port
   netstat -an | findstr :8787
   
   # Use a different port
   set MARA_UDP_PORT=8788
   ```

2. **Serial Permission Denied** (Linux)
   ```bash
   # Add user to dialout group
   sudo usermod -a -G dialout $USER
   # Log out and back in
   ```

3. **Missing Dependencies**
   ```bash
   # Install required packages
   pip install pyserial-asyncio structlog tenacity
   ```

4. **No Data Received**
   - Check network connectivity
   - Verify MARA device is sending data
   - Check firewall settings
   - Review logs for parsing errors

### Debug Mode

Enable detailed logging:

```bash
set LOG_LEVEL=DEBUG
set MARA_ENABLE=true
python -m plugins.mara.plugin
```

## Development

### Running Tests

```bash
# Run all MARA tests
pytest tests/mara/ -v

# Run specific test
pytest tests/mara/test_parse_jsonl.py -v

# Run with coverage
pytest tests/mara/ --cov=plugins.mara
```

### Adding New Formats

1. Add format detection logic to `parser.py`
2. Implement parser method (e.g., `_parse_xml`)
3. Add test cases to `tests/mara/`
4. Update documentation

## License

Part of TheBox project. See main project license for details.
