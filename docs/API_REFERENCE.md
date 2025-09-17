# API Reference

## Overview

TheBox provides a RESTful API for system monitoring, configuration, and control. The API is built on Flask and provides endpoints for health checks, plugin management, and system status.

## Base URL

```
http://localhost:5000
```

## Authentication

Currently, the API does not require authentication. In production deployments, authentication should be implemented.

## Response Format

All API responses are in JSON format with the following structure:

```json
{
  "status": "success|error",
  "data": {...},
  "message": "Optional message",
  "timestamp": "2024-12-19T10:30:00Z"
}
```

## Error Handling

Errors are returned with appropriate HTTP status codes:

- **200 OK**: Success
- **400 Bad Request**: Invalid request
- **404 Not Found**: Resource not found
- **500 Internal Server Error**: Server error
- **503 Service Unavailable**: Service unavailable

Error response format:

```json
{
  "status": "error",
  "error": {
    "code": "ERROR_CODE",
    "message": "Error description",
    "details": {...}
  },
  "timestamp": "2024-12-19T10:30:00Z"
}
```

## Endpoints

### Health Endpoints

#### GET /health

Get overall system health status.

**Response**:
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

**Status Codes**:
- **200**: System healthy
- **503**: System unhealthy

#### GET /health/plugins

Get plugin health status.

**Response**:
```json
{
  "plugins": {
    "droneshield": {
      "healthy": true,
      "status": "available",
      "last_update": "2024-12-19T10:30:00Z"
    },
    "silvus": {
      "healthy": true,
      "status": "available",
      "last_update": "2024-12-19T10:30:00Z"
    }
  }
}
```

#### GET /health/plugins/{plugin_name}

Get specific plugin health status.

**Parameters**:
- `plugin_name` (string): Name of the plugin

**Response**:
```json
{
  "plugin": "droneshield",
  "healthy": true,
  "status": "available",
  "last_update": "2024-12-19T10:30:00Z",
  "details": {
    "sensor_connected": true,
    "data_flow": true,
    "processing_active": true
  }
}
```

#### GET /health/database

Get database health status.

**Response**:
```json
{
  "healthy": true,
  "status": "available",
  "details": {
    "type": "in_memory",
    "records": 1250,
    "memory_usage": "45.2MB"
  }
}
```

### System Endpoints

#### GET /status

Get system status and information.

**Response**:
```json
{
  "system": {
    "name": "TheBox",
    "version": "1.0.0",
    "uptime": "2d 5h 30m",
    "safety_mode": "NORMAL"
  },
  "plugins": {
    "loaded": 8,
    "active": 8,
    "failed": 0
  },
  "sensors": {
    "connected": 5,
    "total": 5,
    "healthy": 5
  }
}
```

#### GET /metrics

Get system performance metrics.

**Response**:
```json
{
  "performance": {
    "detection_rate": 12.5,
    "processing_latency": 45.2,
    "memory_usage": 1.2,
    "cpu_usage": 35.5
  },
  "detections": {
    "total": 1250,
    "last_hour": 45,
    "last_24h": 1200
  },
  "events": {
    "total": 5000,
    "last_hour": 200,
    "last_24h": 4800
  }
}
```

### Plugin Endpoints

#### GET /plugins

Get list of all plugins.

**Response**:
```json
{
  "plugins": [
    {
      "name": "droneshield",
      "type": "sensor",
      "status": "active",
      "description": "DroneShield RF detection plugin"
    },
    {
      "name": "silvus",
      "type": "sensor",
      "status": "active",
      "description": "Silvus RF spectrum analysis plugin"
    }
  ]
}
```

#### GET /plugins/{plugin_name}

Get specific plugin information.

**Parameters**:
- `plugin_name` (string): Name of the plugin

**Response**:
```json
{
  "plugin": {
    "name": "droneshield",
    "type": "sensor",
    "status": "active",
    "description": "DroneShield RF detection plugin",
    "configuration": {
      "udp_port": 50001,
      "enabled": true,
      "timeout": 5.0
    },
    "statistics": {
      "detections_received": 1250,
      "last_detection": "2024-12-19T10:30:00Z",
      "uptime": "2d 5h 30m"
    }
  }
}
```

#### POST /plugins/{plugin_name}/restart

Restart a specific plugin.

**Parameters**:
- `plugin_name` (string): Name of the plugin

**Response**:
```json
{
  "status": "success",
  "message": "Plugin restarted successfully",
  "plugin": "droneshield"
}
```

### Configuration Endpoints

#### GET /config

Get current system configuration.

**Response**:
```json
{
  "configuration": {
    "network": {
      "udp_port_droneshield": 50001,
      "udp_port_silvus": 50002,
      "tcp_host_trakka": "192.168.1.100",
      "tcp_port_trakka": 8080
    },
    "processing": {
      "confidence_threshold": 0.7,
      "range_estimation_mode": "fusion",
      "bearing_offset": 0.0
    },
    "safety": {
      "safety_mode": "NORMAL",
      "safety_enabled": true,
      "safety_monitoring": true
    }
  }
}
```

#### PUT /config

Update system configuration.

**Request Body**:
```json
{
  "configuration": {
    "processing": {
      "confidence_threshold": 0.8
    }
  }
}
```

**Response**:
```json
{
  "status": "success",
  "message": "Configuration updated successfully"
}
```

### Detection Endpoints

#### GET /detections

Get recent detections.

**Query Parameters**:
- `limit` (integer, optional): Maximum number of detections to return (default: 100)
- `sensor` (string, optional): Filter by sensor type
- `since` (string, optional): ISO 8601 timestamp to filter detections since

**Response**:
```json
{
  "detections": [
    {
      "id": "uuid",
      "timestamp": "2024-12-19T10:30:00Z",
      "sensor": "droneshield",
      "bearing": 45.0,
      "range": 150.0,
      "confidence": 0.85,
      "classification": "drone"
    }
  ],
  "total": 100,
  "limit": 100
}
```

#### GET /detections/{detection_id}

Get specific detection details.

**Parameters**:
- `detection_id` (string): UUID of the detection

**Response**:
```json
{
  "detection": {
    "id": "uuid",
    "timestamp": "2024-12-19T10:30:00Z",
    "sensor": "droneshield",
    "bearing": 45.0,
    "range": 150.0,
    "confidence": 0.85,
    "classification": "drone",
    "raw_data": {...},
    "processing_metadata": {...}
  }
}
```

### Event Endpoints

#### GET /events

Get recent events.

**Query Parameters**:
- `limit` (integer, optional): Maximum number of events to return (default: 100)
- `type` (string, optional): Filter by event type
- `since` (string, optional): ISO 8601 timestamp to filter events since

**Response**:
```json
{
  "events": [
    {
      "id": "uuid",
      "timestamp": "2024-12-19T10:30:00Z",
      "type": "detection",
      "source": "droneshield",
      "data": {...}
    }
  ],
  "total": 100,
  "limit": 100
}
```

#### GET /events/{event_id}

Get specific event details.

**Parameters**:
- `event_id` (string): UUID of the event

**Response**:
```json
{
  "event": {
    "id": "uuid",
    "timestamp": "2024-12-19T10:30:00Z",
    "type": "detection",
    "source": "droneshield",
    "data": {...},
    "metadata": {...}
  }
}
```

### Control Endpoints

#### POST /control/trakka/slew

Send slew command to Trakka camera.

**Request Body**:
```json
{
  "bearing": 45.0,
  "elevation": 10.0
}
```

**Response**:
```json
{
  "status": "success",
  "message": "Slew command sent successfully",
  "command": {
    "bearing": 45.0,
    "elevation": 10.0,
    "timestamp": "2024-12-19T10:30:00Z"
  }
}
```

#### POST /control/trakka/capture

Send capture command to Trakka camera.

**Request Body**:
```json
{
  "mode": "eo",
  "format": "jpeg"
}
```

**Response**:
```json
{
  "status": "success",
  "message": "Capture command sent successfully",
  "command": {
    "mode": "eo",
    "format": "jpeg",
    "timestamp": "2024-12-19T10:30:00Z"
  }
}
```

### Safety Endpoints

#### GET /safety/status

Get safety mode status.

**Response**:
```json
{
  "safety_mode": "NORMAL",
  "safety_enabled": true,
  "safety_monitoring": true,
  "health_status": {
    "overall": "healthy",
    "sensors": "healthy",
    "processing": "healthy",
    "plugins": "healthy"
  }
}
```

#### POST /safety/mode

Change safety mode.

**Request Body**:
```json
{
  "mode": "EMERGENCY",
  "reason": "Manual activation"
}
```

**Response**:
```json
{
  "status": "success",
  "message": "Safety mode changed successfully",
  "previous_mode": "NORMAL",
  "current_mode": "EMERGENCY"
}
```

#### GET /safety/events

Get safety events.

**Query Parameters**:
- `limit` (integer, optional): Maximum number of events to return (default: 100)
- `since` (string, optional): ISO 8601 timestamp to filter events since

**Response**:
```json
{
  "events": [
    {
      "id": "uuid",
      "timestamp": "2024-12-19T10:30:00Z",
      "event_type": "MODE_CHANGE",
      "description": "Safety mode changed to EMERGENCY",
      "data": {...}
    }
  ],
  "total": 100,
  "limit": 100
}
```

## WebSocket Endpoints

### /ws/events

WebSocket endpoint for real-time event streaming.

**Connection**:
```javascript
const ws = new WebSocket('ws://localhost:5000/ws/events');
```

**Message Format**:
```json
{
  "type": "detection|event|status",
  "data": {...},
  "timestamp": "2024-12-19T10:30:00Z"
}
```

**Event Types**:
- `detection`: New detection received
- `event`: System event occurred
- `status`: Status update

## Rate Limiting

API endpoints are rate limited to prevent abuse:

- **Health endpoints**: 100 requests per minute
- **Status endpoints**: 60 requests per minute
- **Control endpoints**: 10 requests per minute
- **Other endpoints**: 30 requests per minute

Rate limit headers:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640000000
```

## CORS

Cross-Origin Resource Sharing is enabled for development. In production, CORS should be configured appropriately.

## Examples

### Python Client

```python
import requests

# Get system health
response = requests.get('http://localhost:5000/health')
health = response.json()

# Get recent detections
response = requests.get('http://localhost:5000/detections?limit=10')
detections = response.json()

# Send slew command
response = requests.post('http://localhost:5000/control/trakka/slew', 
                        json={'bearing': 45.0, 'elevation': 10.0})
result = response.json()
```

### JavaScript Client

```javascript
// Get system health
fetch('http://localhost:5000/health')
  .then(response => response.json())
  .then(data => console.log(data));

// Get recent detections
fetch('http://localhost:5000/detections?limit=10')
  .then(response => response.json())
  .then(data => console.log(data));

// Send slew command
fetch('http://localhost:5000/control/trakka/slew', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    bearing: 45.0,
    elevation: 10.0
  })
})
.then(response => response.json())
.then(data => console.log(data));
```

### cURL Examples

```bash
# Get system health
curl http://localhost:5000/health

# Get plugin status
curl http://localhost:5000/health/plugins

# Get recent detections
curl "http://localhost:5000/detections?limit=10&sensor=droneshield"

# Send slew command
curl -X POST http://localhost:5000/control/trakka/slew \
  -H "Content-Type: application/json" \
  -d '{"bearing": 45.0, "elevation": 10.0}'

# Change safety mode
curl -X POST http://localhost:5000/safety/mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "EMERGENCY", "reason": "Manual activation"}'
```

## Error Codes

| Code | Description |
|------|-------------|
| `INVALID_REQUEST` | Invalid request format or parameters |
| `PLUGIN_NOT_FOUND` | Plugin not found |
| `PLUGIN_ERROR` | Plugin error occurred |
| `CONFIGURATION_ERROR` | Configuration error |
| `SAFETY_MODE_ERROR` | Safety mode error |
| `DETECTION_NOT_FOUND` | Detection not found |
| `EVENT_NOT_FOUND` | Event not found |
| `CONTROL_ERROR` | Control command error |
| `SYSTEM_ERROR` | System error occurred |

## Changelog

### Version 1.0.0
- Initial API implementation
- Health endpoints
- Plugin management
- Configuration endpoints
- Detection endpoints
- Event endpoints
- Control endpoints
- Safety endpoints
- WebSocket support
