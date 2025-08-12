# X-Plane Traffic to GDL90 Converter

This project converts X-Plane traffic data (from xPilot/VATSIM) to GDL90 format and transmits it via UDP for use with Electronic Flight Bags (EFBs) and other aviation applications.

## Overview

The system consists of two parts:
1. **X-Plane Plugin** (C++): Reads traffic data from X-Plane and converts it to GDL90 format
2. **Python Receiver**: Receives GDL90 messages and processes them for your EFB system

## Features

- ✈️ Reads traffic from xPilot (VATSIM) datarefs
- 📡 Fallback to X-Plane TCAS datarefs if xPilot unavailable  
- 🔄 Proper GDL90 encoding with CRC validation
- 📊 Extracts: Callsign, Lat, Long, Altitude, Heading, Speed
- 🌐 UDP transmission for easy integration
- 🐍 Python tools for receiving and processing

## Quick Start

### 1. Build the X-Plane Plugin

```bash
cd /path/to/xptfc2gdl90
mkdir build && cd build
cmake ..
make
```

### 2. Install the Plugin

Copy the built plugin to your X-Plane plugins directory:
- **macOS**: `X-Plane/Resources/plugins/TrafficGDL90/TrafficGDL90.xpl`
- **Windows**: `X-Plane/Resources/plugins/TrafficGDL90/TrafficGDL90.xpl`
- **Linux**: `X-Plane/Resources/plugins/TrafficGDL90/TrafficGDL90.xpl`

### 3. Install Python Dependencies

```bash
pip install requests  # Only needed for HTTP EFB integration
```

### 4. Start the Python Receiver

```bash
# Basic receiver (prints aircraft data)
python3 gdl90_receiver.py

# Debug mode (shows detailed message parsing)
python3 gdl90_receiver.py --debug

# Test the receiver with known working messages
python3 test_gdl90_receiver.py

# EFB integration examples
python3 efb_integration_example.py efb   # HTTP integration
python3 efb_integration_example.py file  # File output
python3 efb_integration_example.py tcp   # TCP server
```

### 5. Start X-Plane

1. Start X-Plane with the plugin installed
2. Connect to VATSIM using xPilot (recommended) or use X-Plane's built-in multiplayer
3. The plugin will automatically detect traffic and send GDL90 messages

## Configuration

### Plugin Configuration

Edit `src/main.cpp` to change the UDP target:

```cpp
// Configure UDP target - change these values as needed
g_trafficReader->SetUDPTarget("192.168.1.100", 4000);  // Your EFB's IP
```

### Python Configuration

The Python receiver listens on `127.0.0.1:4000` by default. To change:

```python
receiver = GDL90Receiver(host="0.0.0.0", port=4000)
```

## Data Format

The plugin extracts and transmits the following aircraft data:

| Field | Type | Description |
|-------|------|-------------|
| Callsign | String | Aircraft callsign (max 8 chars) |
| Latitude | Double | Latitude in decimal degrees |
| Longitude | Double | Longitude in decimal degrees |
| Altitude | Double | Altitude in feet |
| Heading | Float | Heading in degrees (0-360) |
| Speed | Float | Ground speed in knots |
| On Ground | Boolean | Whether aircraft is on ground |
| Mode S ID | Integer | Unique aircraft identifier |

## Integration Examples

### 1. HTTP EFB Integration

```python
from gdl90_receiver import GDL90Receiver

def send_to_efb(aircraft):
    # Send to your EFB via HTTP API
    response = requests.post('http://your-efb/api/traffic', json={
        'callsign': aircraft.callsign,
        'lat': aircraft.latitude,
        'lon': aircraft.longitude,
        'alt': aircraft.altitude
    })

receiver = GDL90Receiver()
receiver.set_aircraft_callback(send_to_efb)
receiver.start()
```

### 2. File Output

```python
def write_to_file(aircraft):
    with open('traffic.json', 'w') as f:
        json.dump({
            'callsign': aircraft.callsign,
            'latitude': aircraft.latitude,
            'longitude': aircraft.longitude,
            'altitude': aircraft.altitude,
            'timestamp': aircraft.timestamp
        }, f)

receiver = GDL90Receiver()
receiver.set_aircraft_callback(write_to_file)
receiver.start()
```

### 3. WebSocket Integration

```python
import asyncio
import websockets
import json

async def websocket_handler(websocket, path):
    async for message in websocket:
        # Handle messages from EFB
        pass

def send_via_websocket(aircraft):
    # Send aircraft data via WebSocket
    # Implementation depends on your WebSocket setup
    pass
```

## Troubleshooting

### Plugin Issues

Check X-Plane's Log.txt for plugin messages:
- `TrafficGDL90: Plugin starting...` - Plugin loaded successfully
- `TrafficGDL90: xPilot plugin not found` - xPilot not installed/enabled
- `TrafficGDL90: UDP initialized successfully` - Network ready

### Python Issues

**Step 1: Test the receiver first**
```bash
# Test with known working messages
python3 test_gdl90_receiver.py
```

**Step 2: Use debug mode**
```bash
# See detailed message parsing
python3 gdl90_receiver.py --debug
```

Common problems:
- **Port already in use**: Change the port number or kill the process using it
- **No data received**: Check that X-Plane plugin is running and configured correctly
- **CRC errors**: Usually indicates network corruption (rare with localhost)
- **Invalid message format**: Use debug mode to see raw hex data

**Debug output example:**
```
📥 Raw UDP data from ('127.0.0.1', 54321): 32 bytes
   Hex: 7e14ab0123456789abcdef012345...
✈️  Parsing traffic report (0x14)
✈️  UAL123   | Lat: 37.621311 | Lon: -122.378968 | Alt: 2500ft | ...
```

### Network Issues

- Make sure firewall allows UDP traffic on your chosen port
- For remote EFBs, use the actual IP address instead of 127.0.0.1
- Test connectivity: `nc -u your_efb_ip 4000` (netcat)

## Technical Details

### GDL90 Protocol

The plugin implements GDL90 v1.4 with the following message types:
- **0x00**: Heartbeat (sent periodically)
- **0x14**: Traffic Report (aircraft position data)

Message format:
```
[Flag 0x7E] [Message Data] [CRC-16] [Flag 0x7E]
```

### Data Sources Priority

1. **xPilot bulk datarefs** (preferred) - `xpilot/bulk/quick`, `xpilot/bulk/expensive`
2. **xPilot individual datarefs** - `xpilot/aircraft/N/lat`, etc.
3. **X-Plane TCAS datarefs** (fallback) - `sim/cockpit2/tcas/targets/position/double/planeN_lat`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with X-Plane and your EFB system
5. Submit a pull request

## License

This project is released under the MIT License. See LICENSE file for details.

## Support

For questions and support:
1. Check the X-Plane Log.txt for plugin messages
2. Verify your EFB can receive UDP data on the configured port
3. Test with the provided Python examples first
4. Open an issue on GitHub with your configuration and log files
