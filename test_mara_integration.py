#!/usr/bin/env python3
"""
Simple integration test for MARA plugin with TheBox.
"""
import asyncio
import json
import socket
import time
from unittest.mock import Mock

from plugins.mara.plugin import MARAPlugin


async def test_mara_plugin_integration():
    """Test MARA plugin integration."""
    print("Testing MARA Plugin Integration...")
    
    # Create mock event manager
    event_manager = Mock()
    event_manager.db = Mock()
    event_manager.db.get = Mock(return_value=[])
    event_manager.db.set = Mock()
    
    # Create plugin
    plugin = MARAPlugin(event_manager)
    
    # Set environment variables for testing
    import os
    os.environ["MARA_ENABLE"] = "true"
    os.environ["MARA_INPUT_MODE"] = "udp"
    os.environ["MARA_UDP_PORT"] = "8789"  # Use different port for testing
    os.environ["OUT_REBROADCAST_ENABLE"] = "false"
    
    print("Loading MARA plugin...")
    plugin.load()
    
    # Wait a moment for plugin to start
    await asyncio.sleep(1)
    
    # Test data
    test_messages = [
        '{"timestamp": "2025-01-16T10:30:45.123Z", "sensor_id": "EO_001", "object_id": "obj_123", "confidence": 0.85, "bearing_deg": 45.2, "elevation_deg": 12.5, "range_m": 1500.0, "lat": 40.7128, "lon": -74.0060, "speed_mps": 15.2, "heading_deg": 90.0, "label": "drone", "channel": "EO"}',
        'timestamp=2025-01-16T10:31:00.000Z sensor_id=EO_001 object_id=obj_126 confidence=0.91 bearing_deg=180.3 elevation_deg=15.2 range_m=3000.0 lat=40.7140 lon=-74.0040 speed_mps=25.0 heading_deg=0.0 label=drone channel=EO',
        '2025-01-16T10:31:30.000Z,ACOUSTIC_003,obj_128,0.88,45.0,10.5,1800.0,40.7120,-74.0065,18.7,45.0,drone,ACOUSTIC'
    ]
    
    print("Sending test messages...")
    
    # Send test messages via UDP
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        for i, message in enumerate(test_messages):
            print(f"Sending message {i+1}: {message[:50]}...")
            s.sendto(message.encode('utf-8'), ('127.0.0.1', 8789))
            time.sleep(0.1)  # Small delay between messages
    
    # Wait for processing
    print("Waiting for message processing...")
    await asyncio.sleep(2)
    
    # Check if events were published
    print(f"Event manager publish called {event_manager.publish.call_count} times")
    
    if event_manager.publish.call_count > 0:
        print("✓ Plugin successfully processed messages and published events")
        
        # Show the published events
        for call in event_manager.publish.call_args_list:
            event_type, data, store_in_db = call[0]
            print(f"  Published: {event_type} (store_in_db={store_in_db})")
            if 'detection' in data:
                detection = data['detection']
                print(f"    Source: {detection.get('source')}")
                print(f"    Sensor Channel: {detection.get('sensor_channel')}")
                print(f"    Event Type: {detection.get('event_type')}")
                print(f"    Label: {detection.get('label')}")
                print(f"    Confidence: {detection.get('confidence')}")
    else:
        print("✗ No events were published")
    
    print("Unloading plugin...")
    plugin.unload()
    
    print("Integration test completed!")


if __name__ == "__main__":
    asyncio.run(test_mara_plugin_integration())
