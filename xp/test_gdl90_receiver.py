#!/usr/bin/env python3
"""
Test script for GDL90 receiver using the exact working implementation from main.py
This will create test GDL90 messages and send them to test the receiver
"""

import socket
import time
import struct
import binascii
from gdl90_receiver import GDL90Receiver

# Import the working GDL90 encoder from main.py structure
GDL90_CRC16_TABLE = (
    0x0000, 0x1021, 0x2042, 0x3063, 0x4084, 0x50a5, 0x60c6, 0x70e7,
    0x8108, 0x9129, 0xa14a, 0xb16b, 0xc18c, 0xd1ad, 0xe1ce, 0xf1ef,
    0x1231, 0x0210, 0x3273, 0x2252, 0x52b5, 0x4294, 0x72f7, 0x62d6,
    0x9339, 0x8318, 0xb37b, 0xa35a, 0xd3bd, 0xc39c, 0xf3ff, 0xe3de,
    0x2462, 0x3443, 0x0420, 0x1401, 0x64e6, 0x74c7, 0x44a4, 0x5485,
    0xa56a, 0xb54b, 0x8528, 0x9509, 0xe5ee, 0xf5cf, 0xc5ac, 0xd58d,
    0x3653, 0x2672, 0x1611, 0x0630, 0x76d7, 0x66f6, 0x5695, 0x46b4,
    0xb75b, 0xa77a, 0x9719, 0x8738, 0xf7df, 0xe7fe, 0xd79d, 0xc7bc,
    0x48c4, 0x58e5, 0x6886, 0x78a7, 0x0840, 0x1861, 0x2802, 0x3823,
    0xc9cc, 0xd9ed, 0xe98e, 0xf9af, 0x8948, 0x9969, 0xa90a, 0xb92b,
    0x5af5, 0x4ad4, 0x7ab7, 0x6a96, 0x1a71, 0x0a50, 0x3a33, 0x2a12,
    0xdbfd, 0xcbdc, 0xfbbf, 0xeb9e, 0x9b79, 0x8b58, 0xbb3b, 0xab1a,
    0x6ca6, 0x7c87, 0x4ce4, 0x5cc5, 0x2c22, 0x3c03, 0x0c60, 0x1c41,
    0xedae, 0xfd8f, 0xcdec, 0xddcd, 0xad2a, 0xbd0b, 0x8d68, 0x9d49,
    0x7e97, 0x6eb6, 0x5ed5, 0x4ef4, 0x3e13, 0x2e32, 0x1e51, 0x0e70,
    0xff9f, 0xefbe, 0xdfdd, 0xcffc, 0xbf1b, 0xaf3a, 0x9f59, 0x8f78,
    0x9188, 0x81a9, 0xb1ca, 0xa1eb, 0xd10c, 0xc12d, 0xf14e, 0xe16f,
    0x1080, 0x00a1, 0x30c2, 0x20e3, 0x5004, 0x4025, 0x7046, 0x6067,
    0x83b9, 0x9398, 0xa3fb, 0xb3da, 0xc33d, 0xd31c, 0xe37f, 0xf35e,
    0x02b1, 0x1290, 0x22f3, 0x32d2, 0x4235, 0x5214, 0x6277, 0x7256,
    0xb5ea, 0xa5cb, 0x95a8, 0x8589, 0xf56e, 0xe54f, 0xd52c, 0xc50d,
    0x34e2, 0x24c3, 0x14a0, 0x0481, 0x7466, 0x6447, 0x5424, 0x4405,
    0xa7db, 0xb7fa, 0x8799, 0x97b8, 0xe75f, 0xf77e, 0xc71d, 0xd73c,
    0x26d3, 0x36f2, 0x0691, 0x16b0, 0x6657, 0x7676, 0x4615, 0x5634,
    0xd94c, 0xc96d, 0xf90e, 0xe92f, 0x99c8, 0x89e9, 0xb98a, 0xa9ab,
    0x5844, 0x4865, 0x7806, 0x6827, 0x18c0, 0x08e1, 0x3882, 0x28a3,
    0xcb7d, 0xdb5c, 0xeb3f, 0xfb1e, 0x8bf9, 0x9bd8, 0xabbb, 0xbb9a,
    0x4a75, 0x5a54, 0x6a37, 0x7a16, 0x0af1, 0x1ad0, 0x2ab3, 0x3a92,
    0xfd2e, 0xed0f, 0xdd6c, 0xcd4d, 0xbdaa, 0xad8b, 0x9de8, 0x8dc9,
    0x7c26, 0x6c07, 0x5c64, 0x4c45, 0x3ca2, 0x2c83, 0x1ce0, 0x0cc1,
    0xef1f, 0xff3e, 0xcf5d, 0xdf7c, 0xaf9b, 0xbfba, 0x8fd9, 0x9ff8,
    0x6e17, 0x7e36, 0x4e55, 0x5e74, 0x2e93, 0x3eb2, 0x0ed1, 0x1ef0,
)

def gdl90_crc_compute(data):
    """Calculate GDL90 CRC-16-CCITT (from working implementation)"""
    mask16bit = 0xffff
    crc_array = bytearray()
    
    crc = 0
    for c in data:
        m = (crc << 8) & mask16bit
        crc = GDL90_CRC16_TABLE[(crc >> 8)] ^ m ^ c
    
    crc_array.append(crc & 0x00ff)
    crc_array.append((crc & 0xff00) >> 8)
    return crc_array

class TestGDL90Encoder:
    """Test GDL90 encoder using the exact working method from main.py"""
    
    def __init__(self):
        self.icao_address = 0xABCDEF
        
    def _add_crc(self, msg):
        """Calculate CRC and add to message"""
        crc_bytes = gdl90_crc_compute(msg)
        msg.extend(crc_bytes)
    
    def _escape(self, msg):
        """Escape 0x7d and 0x7e characters"""
        msg_new = bytearray()
        escape_char = 0x7d
        chars_to_escape = [0x7d, 0x7e]
        
        for c in msg:
            if c in chars_to_escape:
                msg_new.append(escape_char)  # Insert escape character
                msg_new.append(c ^ 0x20)     # Modify original byte
            else:
                msg_new.append(c)
        
        return msg_new
    
    def _prepared_message(self, msg):
        """Prepare message: add CRC, escape, add start/end markers"""
        self._add_crc(msg)
        new_msg = self._escape(msg)
        new_msg.insert(0, 0x7e)
        new_msg.append(0x7e)
        return new_msg
    
    def _pack24bit(self, num):
        """Pack 24-bit number as byte array (big-endian)"""
        if ((num & 0xFFFFFF) != num) or num < 0:
            raise ValueError("Input is not a 24-bit unsigned value")
        a = bytearray()
        a.append((num & 0xff0000) >> 16)
        a.append((num & 0x00ff00) >> 8)
        a.append(num & 0xff)
        return a
    
    def _make_latitude(self, latitude):
        """Convert latitude to two's complement for 24-bit packing"""
        if latitude > 90.0: latitude = 90.0
        if latitude < -90.0: latitude = -90.0
        latitude = int(latitude * (0x800000 / 180.0))
        if latitude < 0:
            latitude = (0x1000000 + latitude) & 0xffffff  # Two's complement
        return latitude
    
    def _make_longitude(self, longitude):
        """Convert longitude to two's complement for 24-bit packing"""
        if longitude > 180.0: longitude = 180.0
        if longitude < -180.0: longitude = -180.0
        longitude = int(longitude * (0x800000 / 180.0))
        if longitude < 0:
            longitude = (0x1000000 + longitude) & 0xffffff  # Two's complement
        return longitude
    
    def create_heartbeat(self):
        """Create heartbeat message (ID 0x00)"""
        msg = bytearray([0x00])  # Message ID
        msg.extend([0x81, 0x01])  # Status bytes
        msg.extend(struct.pack('<H', 0x0000))  # Timestamp (little-endian)
        msg.extend([0x00, 0x00])  # Message count
        
        return self._prepared_message(msg)
    
    def create_traffic_report(self, callsign, lat, lon, alt_ft, heading=0, speed=0):
        """
        Create a traffic report message (0x14) based on the traffic report table format
        Traffic Report data = st aa aa aa ll ll ll nn nn nn dd dm ia hh hv vv tt ee cc cc cc cc cc cc cc cc px
        """
        msg = bytearray([0x14])  # Message ID: Traffic Report
        
        # Byte 1: st (s=Traffic Alert, t=Address Type)
        traffic_alert = 0  # No traffic alert
        addr_type = 0      # ADS-B with ICAO address
        st_byte = (traffic_alert << 4) | addr_type
        msg.append(st_byte)
        
        # Bytes 2-4: aa aa aa (Participant Address - 24 bits)
        msg.extend(self._pack24bit(self.icao_address))
        
        # Bytes 5-7: ll ll ll (Latitude - 24 bits signed)
        msg.extend(self._pack24bit(self._make_latitude(lat)))
        
        # Bytes 8-10: nn nn nn (Longitude - 24 bits signed)
        msg.extend(self._pack24bit(self._make_longitude(lon)))
        
        # Bytes 11-12: dd dm (Altitude 12 bits + Misc 4 bits)
        altitude = int((alt_ft + 1000) / 25.0)
        if altitude < 0: altitude = 0
        if altitude > 0xffe: altitude = 0xffe
        
        misc = 0  # Airborne
        msg.append((altitude & 0x0ff0) >> 4)  # High 8 bits of altitude
        msg.append(((altitude & 0x0f) << 4) | (misc & 0xf))  # Low 4 bits + misc
        
        # Byte 13: ia (i=NIC 4 bits, a=NACp 4 bits)
        nic = 9   # Navigation Integrity Category
        nac = 9   # Navigation Accuracy Category
        msg.append((nic << 4) | nac)
        
        # Bytes 14-15: hh h (Horizontal velocity spans byte 14 + high nibble of 15)
        h_velocity = int(speed) if speed < 0xfff else 0xfff
        msg.append((h_velocity & 0xff0) >> 4)  # High 8 bits
        
        # Bytes 15-16: h vvv (Low nibble of h_vel + 12-bit v_velocity)
        v_velocity = 0  # No vertical velocity data
        msg.append(((h_velocity & 0xf) << 4) | ((v_velocity & 0xf00) >> 8))
        msg.append(v_velocity & 0xff)
        
        # Byte 17: tt (Track/Heading)
        track_heading = int(heading / (360.0 / 256))
        msg.append(track_heading & 0xff)
        
        # Byte 18: ee (Emitter Category)
        emitter_cat = 1  # Light aircraft
        msg.append(emitter_cat)
        
        # Bytes 19-26: cc cc cc cc cc cc cc cc (Call Sign - 8 ASCII characters)
        call_sign = bytearray(str(callsign + " " * 8)[:8], 'ascii')
        msg.extend(call_sign)
        
        # Byte 27: px (p=Emergency/Priority Code 4 bits, x=Spare 4 bits)
        emergency_code = 0
        msg.append((emergency_code & 0xf) << 4)
        
        return self._prepared_message(msg)

def test_receiver():
    """Test the GDL90 receiver with known working messages"""
    print("🧪 Testing GDL90 Receiver with Working Implementation")
    print("=" * 60)
    
    # Create test encoder
    encoder = TestGDL90Encoder()
    
    # Create UDP socket for sending test messages
    send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # Test aircraft data
    test_aircraft = [
        {
            'callsign': 'UAL123',
            'lat': 37.621311,
            'lon': -122.378968,
            'alt': 2500.0,
            'heading': 270,
            'speed': 180
        },
        {
            'callsign': 'DAL456', 
            'lat': 40.641766,
            'lon': -73.780968,
            'alt': 3000.0,
            'heading': 90,
            'speed': 200
        },
        {
            'callsign': 'SWA789',
            'lat': 33.942791,
            'lon': -118.410042,
            'alt': 1500.0,
            'heading': 180,
            'speed': 150
        }
    ]
    
    def test_callback(aircraft):
        """Test callback to verify parsed data"""
        print(f"✅ Successfully parsed: {aircraft.callsign}")
        print(f"   📍 Position: {aircraft.latitude:.6f}, {aircraft.longitude:.6f}")
        print(f"   🏔️  Altitude: {aircraft.altitude:.0f} ft")
        print(f"   🧭 Heading: {aircraft.heading:.0f}°") 
        print(f"   🚀 Speed: {aircraft.speed:.0f} kt")
        print(f"   🆔 Mode S ID: 0x{aircraft.mode_s_id:06X}")
        print()
    
    # Start receiver
    print("🚀 Starting GDL90 receiver...")
    receiver = GDL90Receiver(host="127.0.0.1", port=4000, debug=True)
    receiver.set_aircraft_callback(test_callback)
    
    # Start receiver in background
    import threading
    receiver_thread = threading.Thread(target=receiver.start, daemon=True)
    receiver_thread.start()
    
    # Give receiver time to start
    time.sleep(1)
    
    try:
        # Send heartbeat
        print("💓 Sending heartbeat message...")
        heartbeat = encoder.create_heartbeat()
        print(f"   Hex: {binascii.hexlify(heartbeat).decode()}")
        send_socket.sendto(heartbeat, ("127.0.0.1", 4000))
        time.sleep(0.5)
        
        # Send test aircraft
        for i, aircraft in enumerate(test_aircraft):
            print(f"✈️  Sending traffic report {i+1}/3: {aircraft['callsign']}")
            
            traffic_msg = encoder.create_traffic_report(
                callsign=aircraft['callsign'],
                lat=aircraft['lat'],
                lon=aircraft['lon'],
                alt_ft=aircraft['alt'],
                heading=aircraft['heading'],
                speed=aircraft['speed']
            )
            
            print(f"   Hex: {binascii.hexlify(traffic_msg).decode()}")
            send_socket.sendto(traffic_msg, ("127.0.0.1", 4000))
            time.sleep(1)  # Wait between messages
        
        # Keep running for a bit to see results
        print("⏳ Waiting 5 seconds to see results...")
        time.sleep(5)
        
    except KeyboardInterrupt:
        pass
    finally:
        print("🛑 Stopping test...")
        receiver.stop()
        send_socket.close()
        
        # Show final statistics
        print()
        print("📊 Test Results:")
        print(f"   📥 UDP messages received: {receiver.message_count}")
        print(f"   ✈️  Aircraft parsed: {len(receiver.parser.aircraft)}")
        
        if receiver.parser.aircraft:
            print("\n🛩️  Final aircraft list:")
            for aircraft in receiver.parser.aircraft.values():
                print(f"   • {aircraft.callsign}: {aircraft.latitude:.6f}, {aircraft.longitude:.6f}, {aircraft.altitude:.0f}ft")

if __name__ == "__main__":
    test_receiver()
