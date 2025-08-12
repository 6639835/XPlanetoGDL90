#!/usr/bin/env python3
"""
GDL90 Receiver for X-Plane Traffic Data
Receives GDL90 messages from X-Plane plugin and extracts aircraft information
Based on working GDL90 implementation and standard traffic report format
"""

import socket
import struct
import threading
import time
import json
import binascii
from dataclasses import dataclass
from typing import Optional, List, Dict, Any


@dataclass
class AircraftData:
    """Represents aircraft data extracted from GDL90 messages"""
    callsign: str
    latitude: float
    longitude: float
    altitude: float  # feet
    heading: float  # degrees
    speed: float    # knots
    on_ground: bool
    mode_s_id: int
    timestamp: float


class GDL90Parser:
    """Parse GDL90 messages and extract aircraft data"""
    
    # GDL90 Protocol Constants
    FLAG_BYTE = 0x7E
    MSG_HEARTBEAT = 0x00
    MSG_TRAFFIC_REPORT = 0x14
    MSG_OWNSHIP = 0x0A  # Ownship report is 0x0A, not 0x10
    
    # GDL-90 CRC-16-CCITT lookup table (from working implementation)
    CRC16_TABLE = (
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
    
    def __init__(self):
        self.aircraft: Dict[int, AircraftData] = {}
        self.message_count = 0
        
    def calculate_crc(self, data: bytes) -> int:
        """Calculate GDL90 CRC-16-CCITT (using working implementation method)"""
        mask16bit = 0xffff
        crc = 0
        
        for c in data:
            m = (crc << 8) & mask16bit
            crc = self.CRC16_TABLE[(crc >> 8)] ^ m ^ c
            
        return crc
    
    def unescape_data(self, data: bytes) -> bytes:
        """Unescape GDL90 data (reverse the 0x7E and 0x7D escaping)"""
        result = bytearray()
        i = 0
        
        while i < len(data):
            if data[i] == 0x7D and i + 1 < len(data):
                if data[i + 1] == 0x5E:
                    result.append(0x7E)
                elif data[i + 1] == 0x5D:
                    result.append(0x7D)
                else:
                    result.append(data[i])
                    result.append(data[i + 1])
                i += 2
            else:
                result.append(data[i])
                i += 1
                
        return bytes(result)
    
    def decode_lat_lon(self, lat_bytes: bytes, lon_bytes: bytes) -> tuple:
        """Decode GDL90 latitude and longitude (based on working implementation)"""
        # Convert 3-byte big-endian to integers
        lat_int = struct.unpack('>I', b'\x00' + lat_bytes)[0]
        lon_int = struct.unpack('>I', b'\x00' + lon_bytes)[0]
        
        # Handle 24-bit two's complement signed integers
        if lat_int & 0x800000:  # Check sign bit
            lat_int = lat_int - 0x1000000  # Convert from unsigned to signed
        if lon_int & 0x800000:  # Check sign bit
            lon_int = lon_int - 0x1000000  # Convert from unsigned to signed
        
        # Convert to degrees using the resolution from working implementation
        # Resolution = 180 / 2^23 degrees per LSB
        scale_factor = 180.0 / 8388608.0  # 180.0 / (2^23)
        latitude = lat_int * scale_factor  
        longitude = lon_int * scale_factor
        
        return latitude, longitude
    
    def decode_altitude(self, alt_bytes: bytes) -> float:
        """Decode GDL90 altitude (based on traffic report table)"""
        # Traffic report altitude format: dd dm
        # First byte contains high 8 bits, second byte has low 4 bits in upper nibble
        # ddd = 12-bit altitude value, Altitude (ft) = ("ddd" * 25) - 1,000
        alt_raw = (alt_bytes[0] << 4) | ((alt_bytes[1] & 0xF0) >> 4)
        
        # Convert to feet using standard GDL90 formula
        altitude = (alt_raw * 25) - 1000
        return float(altitude)
    
    def parse_traffic_report(self, message: bytes) -> Optional[AircraftData]:
        """
        Parse GDL90 traffic report message based on exact format table:
        Traffic Report data = st aa aa aa ll ll ll nn nn nn dd dm ia hh hv vv tt ee cc cc cc cc cc cc cc cc px
        """
        if len(message) < 28:  # Minimum traffic report length including message ID
            return None
            
        try:
            # Extract fields from the message
            msg_id = message[0]
            if msg_id != self.MSG_TRAFFIC_REPORT:
                return None
                
            # Byte 1: st (s=Traffic Alert Status bit, t=Address Type 2 bits)
            st_byte = message[1]
            traffic_alert = bool(st_byte & 0x10)  # bit 4 (s)
            addr_type = st_byte & 0x0F  # bits 0-3 (t)
            
            # Bytes 2-4: aa aa aa (Participant Address - 24 bits)
            mode_s_bytes = message[2:5]  
            mode_s_id = struct.unpack('>I', b'\x00' + mode_s_bytes)[0]
            
            # Bytes 5-7: ll ll ll (Latitude - 24 bits signed)
            lat_bytes = message[5:8]
            
            # Bytes 8-10: nn nn nn (Longitude - 24 bits signed)
            lon_bytes = message[8:11]
            latitude, longitude = self.decode_lat_lon(lat_bytes, lon_bytes)
            
            # Bytes 11-12: dd dm (Altitude 12 bits + Misc 4 bits)
            alt_bytes = message[11:13]
            altitude = self.decode_altitude(alt_bytes)
            
            # Extract miscellaneous indicators from low nibble of byte 12
            misc = message[12] & 0x0F
            on_ground = bool(misc & 0x01)  # Bit 0 typically indicates on-ground
            
            # Byte 13: ia (i=NIC 4 bits, a=NACp 4 bits)
            nic_nac_byte = message[13]
            nic = (nic_nac_byte & 0xF0) >> 4  # Navigation Integrity Category
            nac = nic_nac_byte & 0x0F         # Navigation Accuracy Category
            
            # Bytes 14-15: hh h (Horizontal velocity - resolution 1 kt)
            # Note: This spans byte 14 and high nibble of byte 15
            h_vel_raw = (message[14] << 4) | ((message[15] & 0xF0) >> 4)
            velocity = float(h_vel_raw)  # Already in knots
            
            # Bytes 15-16: v vv (Vertical velocity - low nibble of 15 + byte 16)
            # Signed integer in units of 64 fpm
            v_vel_raw = ((message[15] & 0x0F) << 8) | message[16]
            # Handle 12-bit two's complement
            if v_vel_raw & 0x800:  # Check sign bit
                v_vel_raw = v_vel_raw - 0x1000
            vertical_velocity = v_vel_raw * 64  # Convert to fpm
            
            # Byte 17: tt (Track/Heading - 8-bit angular weighted binary)
            # Resolution = 360/256 degrees, 0=North, 128=South
            track_byte = message[17]
            heading = (track_byte / 256.0) * 360.0
            
            # Byte 18: ee (Emitter Category)
            emitter_category = message[18]
            
            # Bytes 19-26: cc cc cc cc cc cc cc cc (Call Sign - 8 ASCII characters)
            callsign_bytes = message[19:27]
            callsign = callsign_bytes.decode('ascii', errors='ignore').rstrip(' \x00')
            
            # Byte 27: px (p=Emergency/Priority Code 4 bits, x=Spare 4 bits)
            emergency_code = (message[27] & 0xF0) >> 4
            
            return AircraftData(
                callsign=callsign,
                latitude=latitude,
                longitude=longitude,
                altitude=altitude,
                heading=heading,
                speed=velocity,
                on_ground=on_ground,
                mode_s_id=mode_s_id,
                timestamp=time.time()
            )
            
        except Exception as e:
            print(f"Error parsing traffic report: {e}")
            print(f"Message hex: {binascii.hexlify(message).decode()}")
            return None
    
    def parse_ownship_report(self, message: bytes) -> Optional[AircraftData]:
        """Parse GDL90 ownship report message (0x0A) - similar format to traffic report"""
        if len(message) < 28:  # Minimum ownship report length 
            return None
            
        try:
            msg_id = message[0]
            if msg_id != self.MSG_OWNSHIP:
                return None
                
            # Ownship reports have similar structure to traffic reports
            # Byte 1: Status and address type
            status_addr = message[1]
            
            # Bytes 2-4: ICAO address (24 bits)
            icao_bytes = message[2:5]
            icao_id = struct.unpack('>I', b'\x00' + icao_bytes)[0]
            
            # Bytes 5-7: Latitude (24 bits signed)
            lat_bytes = message[5:8]
            
            # Bytes 8-10: Longitude (24 bits signed)  
            lon_bytes = message[8:11]
            latitude, longitude = self.decode_lat_lon(lat_bytes, lon_bytes)
            
            # Bytes 11-12: Altitude
            alt_bytes = message[11:13]
            altitude = self.decode_altitude(alt_bytes)
            
            # Extract other fields similar to traffic report
            misc = message[12] & 0x0F
            on_ground = bool(misc & 0x01)
            
            # Navigation categories
            nic_nac_byte = message[13] if len(message) > 13 else 0
            
            # Velocity (if available)
            velocity = 0.0
            if len(message) > 16:
                h_vel_raw = (message[14] << 4) | ((message[15] & 0xF0) >> 4)
                velocity = float(h_vel_raw)
            
            # Heading (if available)
            heading = 0.0
            if len(message) > 17:
                track_byte = message[17]
                heading = (track_byte / 256.0) * 360.0
            
            # Callsign (if available)
            callsign = "OWNSHIP"
            if len(message) >= 26:
                callsign_bytes = message[18:26]
                callsign = callsign_bytes.decode('ascii', errors='ignore').rstrip(' \x00')
                if not callsign:
                    callsign = "OWNSHIP"
            
            return AircraftData(
                callsign=callsign,
                latitude=latitude,
                longitude=longitude,
                altitude=altitude,
                heading=heading,
                speed=velocity,
                on_ground=on_ground,
                mode_s_id=icao_id,
                timestamp=time.time()
            )
            
        except Exception as e:
            print(f"Error parsing ownship report: {e}")
            print(f"Message hex: {binascii.hexlify(message).decode()}")
            return None
    
    def parse_message(self, raw_message: bytes) -> Optional[AircraftData]:
        """Parse a complete GDL90 message"""
        if len(raw_message) < 5:  # Minimum message length
            return None
            
        # Check start and end flags
        if raw_message[0] != self.FLAG_BYTE or raw_message[-1] != self.FLAG_BYTE:
            print(f"Invalid message flags: start={hex(raw_message[0])}, end={hex(raw_message[-1])}")
            return None
        
        # Extract message content (remove start/end flags)
        escaped_content = raw_message[1:-1]
        
        # Unescape the content
        content = self.unescape_data(escaped_content)
        
        if len(content) < 3:  # Need at least message ID + 2 CRC bytes
            return None
            
        # Extract message data and CRC (CRC is stored as little-endian 2 bytes)
        message_data = content[:-2]
        received_crc_bytes = content[-2:]
        received_crc = struct.unpack('<H', received_crc_bytes)[0]  # Little-endian like working implementation
        
        # Verify CRC
        calculated_crc = self.calculate_crc(message_data)
        if calculated_crc != received_crc:
            print(f"CRC mismatch: calculated={hex(calculated_crc)}, received={hex(received_crc)}")
            print(f"Message data hex: {binascii.hexlify(message_data).decode()}")
            print(f"CRC bytes hex: {binascii.hexlify(received_crc_bytes).decode()}")
            return None
            
        self.message_count += 1
        
        # Parse based on message type
        msg_type = message_data[0]
        
        if msg_type == self.MSG_HEARTBEAT:
            print("💓 Received heartbeat message")
            return None
        elif msg_type == self.MSG_TRAFFIC_REPORT:
            print(f"✈️  Parsing traffic report (0x{msg_type:02X})")
            return self.parse_traffic_report(message_data)
        elif msg_type == self.MSG_OWNSHIP:
            print(f"🛩️  Parsing ownship report (0x{msg_type:02X})")  
            return self.parse_ownship_report(message_data)
        else:
            print(f"❓ Unknown message type: 0x{msg_type:02X}")
            print(f"Message hex: {binascii.hexlify(message_data).decode()}")
            return None


class GDL90Receiver:
    """UDP receiver for GDL90 messages"""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 4000, debug: bool = False):
        self.host = host
        self.port = port
        self.parser = GDL90Parser()
        self.running = False
        self.socket = None
        self.aircraft_callback = None
        self.debug = debug
        self.message_count = 0
        self.last_message_time = 0
        
    def set_aircraft_callback(self, callback):
        """Set callback function to be called when aircraft data is received"""
        self.aircraft_callback = callback
        
    def start(self):
        """Start receiving GDL90 messages"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.bind((self.host, self.port))
            self.socket.settimeout(1.0)  # 1 second timeout for graceful shutdown
            self.running = True
            
            print(f"🚀 GDL90 Receiver started on {self.host}:{self.port}")
            print("📡 Waiting for messages from X-Plane plugin...")
            if self.debug:
                print("🔍 Debug mode enabled - showing detailed message info")
            
            buffer = b""  # Buffer to handle partial messages
            
            while self.running:
                try:
                    data, addr = self.socket.recvfrom(4096)
                    
                    if not data:
                        continue
                    
                    self.message_count += 1
                    current_time = time.time()
                    self.last_message_time = current_time
                    
                    if self.debug:
                        print(f"📥 Raw UDP data from {addr}: {len(data)} bytes")
                        print(f"   Hex: {binascii.hexlify(data).decode()}")
                        
                    # Add to buffer
                    buffer += data
                    
                    # Process all complete messages in buffer
                    while self.FLAG_BYTE in buffer:
                        # Find start of message
                        start_idx = buffer.find(self.parser.FLAG_BYTE)
                        if start_idx == -1:
                            break
                            
                        # Find end of message (next flag byte after start)
                        end_idx = buffer.find(self.parser.FLAG_BYTE, start_idx + 1)
                        if end_idx == -1:
                            break  # Incomplete message, wait for more data
                            
                        # Extract complete message
                        message = buffer[start_idx:end_idx + 1]
                        buffer = buffer[end_idx + 1:]  # Remove processed message
                        
                        # Parse the message
                        aircraft = self.parser.parse_message(message)
                        if aircraft:
                            # Update aircraft dictionary
                            self.parser.aircraft[aircraft.mode_s_id] = aircraft
                            
                            # Call callback if set
                            if self.aircraft_callback:
                                self.aircraft_callback(aircraft)
                            else:
                                # Default: print aircraft info with better formatting
                                print(f"✈️  {aircraft.callsign:8} | "
                                      f"Lat: {aircraft.latitude:9.6f} | "
                                      f"Lon: {aircraft.longitude:10.6f} | "
                                      f"Alt: {aircraft.altitude:6.0f}ft | "
                                      f"Hdg: {aircraft.heading:3.0f}° | "
                                      f"Spd: {aircraft.speed:3.0f}kt | "
                                      f"ID: {aircraft.mode_s_id:06X}")
                        
                except socket.timeout:
                    continue  # Continue loop, allows for graceful shutdown
                except Exception as e:
                    print(f"Error receiving data: {e}")
                    continue
                    
        except Exception as e:
            print(f"Error starting receiver: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the receiver"""
        self.running = False
        if self.socket:
            self.socket.close()
            self.socket = None
        print("GDL90 Receiver stopped")
    
    def get_aircraft_list(self) -> List[AircraftData]:
        """Get list of current aircraft"""
        return list(self.parser.aircraft.values())
    
    def get_aircraft_json(self) -> str:
        """Get aircraft data as JSON string"""
        aircraft_list = []
        for aircraft in self.parser.aircraft.values():
            aircraft_dict = {
                'callsign': aircraft.callsign,
                'latitude': aircraft.latitude,
                'longitude': aircraft.longitude,
                'altitude': aircraft.altitude,
                'heading': aircraft.heading,
                'speed': aircraft.speed,
                'on_ground': aircraft.on_ground,
                'mode_s_id': aircraft.mode_s_id,
                'timestamp': aircraft.timestamp
            }
            aircraft_list.append(aircraft_dict)
        
        return json.dumps(aircraft_list, indent=2)


def example_aircraft_callback(aircraft: AircraftData):
    """Example callback function for processing aircraft data"""
    print(f"✈️  {aircraft.callsign:8} | "
          f"Lat: {aircraft.latitude:9.6f} | "
          f"Lon: {aircraft.longitude:10.6f} | "
          f"Alt: {aircraft.altitude:6.0f}ft | "
          f"Hdg: {aircraft.heading:3.0f}° | "
          f"Spd: {aircraft.speed:3.0f}kt | "
          f"ID: {aircraft.mode_s_id:06X}")
    
    # Here you can add your EFB integration code
    # For example, send to your EFB system:
    # send_to_efb(aircraft)


def main():
    """Main function - example usage"""
    import sys
    
    # Check for debug flag
    debug_mode = "--debug" in sys.argv or "-d" in sys.argv
    
    print("=" * 60)
    print("🛩️  GDL90 Receiver for X-Plane Traffic Data")
    print("=" * 60)
    print("This receiver will parse GDL90 messages from your X-Plane plugin.")
    print("Make sure your X-Plane plugin is configured to send to:")
    print("  📍 IP: 127.0.0.1 (localhost)")
    print("  🔌 Port: 4000")
    print()
    if debug_mode:
        print("🔍 DEBUG MODE: Detailed message information will be shown")
        print()
    
    receiver = GDL90Receiver(debug=debug_mode)
    
    # Set up a callback function to handle aircraft data
    receiver.set_aircraft_callback(example_aircraft_callback)
    
    try:
        # Start the receiver (this will block)
        receiver.start()
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
        receiver.stop()
        
        # Show statistics
        print(f"📊 Received {receiver.message_count} UDP messages")
        if receiver.parser.aircraft:
            print(f"✈️  Tracked {len(receiver.parser.aircraft)} aircraft")


if __name__ == "__main__":
    main()
