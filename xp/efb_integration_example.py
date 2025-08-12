#!/usr/bin/env python3
"""
EFB Integration Example
Shows how to integrate the GDL90 receiver with your EFB system
"""

import json
import requests
import time
from gdl90_receiver import GDL90Receiver, AircraftData
from typing import Dict, Any


class EFBIntegration:
    """Example EFB integration class"""
    
    def __init__(self, efb_url: str = "http://localhost:8080"):
        self.efb_url = efb_url
        self.last_update = 0
        self.update_interval = 1.0  # Update EFB every 1 second
        
    def send_to_efb(self, aircraft: AircraftData) -> bool:
        """Send aircraft data to your EFB system"""
        try:
            # Format data for your EFB system
            efb_data = {
                'type': 'traffic_update',
                'aircraft': {
                    'callsign': aircraft.callsign,
                    'latitude': aircraft.latitude,
                    'longitude': aircraft.longitude,
                    'altitude_ft': aircraft.altitude,
                    'heading_deg': aircraft.heading,
                    'speed_kt': aircraft.speed,
                    'on_ground': aircraft.on_ground,
                    'mode_s_id': aircraft.mode_s_id,
                    'timestamp': aircraft.timestamp
                }
            }
            
            # Send HTTP POST to your EFB system
            response = requests.post(
                f"{self.efb_url}/api/traffic",
                json=efb_data,
                timeout=2.0
            )
            
            if response.status_code == 200:
                return True
            else:
                print(f"EFB responded with status {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"Failed to send to EFB: {e}")
            return False
        except Exception as e:
            print(f"Error formatting data for EFB: {e}")
            return False
    
    def batch_update_efb(self, aircraft_list: list) -> bool:
        """Send batch update of all aircraft to EFB"""
        try:
            # Format all aircraft data for batch update
            efb_data = {
                'type': 'traffic_batch_update',
                'aircraft_list': [],
                'timestamp': time.time()
            }
            
            for aircraft in aircraft_list:
                aircraft_data = {
                    'callsign': aircraft.callsign,
                    'latitude': aircraft.latitude,
                    'longitude': aircraft.longitude,
                    'altitude_ft': aircraft.altitude,
                    'heading_deg': aircraft.heading,
                    'speed_kt': aircraft.speed,
                    'on_ground': aircraft.on_ground,
                    'mode_s_id': aircraft.mode_s_id,
                    'timestamp': aircraft.timestamp
                }
                efb_data['aircraft_list'].append(aircraft_data)
            
            # Send batch update
            response = requests.post(
                f"{self.efb_url}/api/traffic/batch",
                json=efb_data,
                timeout=5.0
            )
            
            if response.status_code == 200:
                print(f"Successfully sent {len(aircraft_list)} aircraft to EFB")
                return True
            else:
                print(f"EFB batch update failed with status {response.status_code}")
                return False
                
        except Exception as e:
            print(f"Error in batch update: {e}")
            return False
    
    def handle_aircraft_update(self, aircraft: AircraftData):
        """Callback function to handle individual aircraft updates"""
        current_time = time.time()
        
        print(f"📡 Received: {aircraft.callsign} at "
              f"{aircraft.latitude:.6f}, {aircraft.longitude:.6f}, "
              f"{aircraft.altitude:.0f}ft")
        
        # Send individual update (optional - might be too frequent)
        # self.send_to_efb(aircraft)
        
        # Store for batch processing (you'd implement this storage)
        # self.pending_updates[aircraft.mode_s_id] = aircraft


def file_output_example():
    """Example: Write aircraft data to a file for other processes to read"""
    
    def write_to_file(aircraft: AircraftData):
        """Write aircraft data to JSON file"""
        try:
            # Read existing data
            try:
                with open('aircraft_data.json', 'r') as f:
                    data = json.load(f)
            except FileNotFoundError:
                data = {'aircraft': {}, 'last_update': 0}
            
            # Update with new aircraft data
            data['aircraft'][str(aircraft.mode_s_id)] = {
                'callsign': aircraft.callsign,
                'latitude': aircraft.latitude,
                'longitude': aircraft.longitude,
                'altitude': aircraft.altitude,
                'heading': aircraft.heading,
                'speed': aircraft.speed,
                'on_ground': aircraft.on_ground,
                'timestamp': aircraft.timestamp
            }
            data['last_update'] = time.time()
            
            # Write back to file
            with open('aircraft_data.json', 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            print(f"Error writing to file: {e}")
    
    # Set up receiver with file output
    receiver = GDL90Receiver()
    receiver.set_aircraft_callback(write_to_file)
    
    print("Starting file output mode...")
    print("Aircraft data will be written to 'aircraft_data.json'")
    
    try:
        receiver.start()
    except KeyboardInterrupt:
        print("\nShutting down file output...")
        receiver.stop()


def tcp_server_example():
    """Example: Serve aircraft data over TCP for other applications"""
    import socket
    import threading
    import json
    
    class TCPServer:
        def __init__(self, port=5000):
            self.port = port
            self.aircraft_data = {}
            self.clients = []
            
        def start_server(self):
            """Start TCP server to serve aircraft data"""
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind(('localhost', self.port))
            server_socket.listen(5)
            
            print(f"TCP server started on port {self.port}")
            
            while True:
                try:
                    client_socket, addr = server_socket.accept()
                    print(f"Client connected from {addr}")
                    
                    # Handle client in separate thread
                    client_thread = threading.Thread(
                        target=self.handle_client, 
                        args=(client_socket,)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                    
                except Exception as e:
                    print(f"Server error: {e}")
                    
        def handle_client(self, client_socket):
            """Handle individual client connection"""
            try:
                while True:
                    # Send current aircraft data
                    data = json.dumps(self.aircraft_data, indent=2) + '\n'
                    client_socket.send(data.encode('utf-8'))
                    time.sleep(1)  # Send updates every second
            except:
                pass
            finally:
                client_socket.close()
                
        def update_aircraft(self, aircraft: AircraftData):
            """Update aircraft data"""
            self.aircraft_data[aircraft.mode_s_id] = {
                'callsign': aircraft.callsign,
                'latitude': aircraft.latitude,
                'longitude': aircraft.longitude,
                'altitude': aircraft.altitude,
                'heading': aircraft.heading,
                'speed': aircraft.speed,
                'on_ground': aircraft.on_ground,
                'timestamp': aircraft.timestamp
            }
    
    # Create TCP server
    tcp_server = TCPServer()
    
    # Start server in background thread
    server_thread = threading.Thread(target=tcp_server.start_server)
    server_thread.daemon = True
    server_thread.start()
    
    # Set up GDL90 receiver
    receiver = GDL90Receiver()
    receiver.set_aircraft_callback(tcp_server.update_aircraft)
    
    print("Starting TCP server mode...")
    print("Connect to localhost:5000 to receive aircraft data")
    
    try:
        receiver.start()
    except KeyboardInterrupt:
        print("\nShutting down TCP server...")
        receiver.stop()


def main():
    """Main function with different integration examples"""
    import sys
    
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        
        if mode == 'efb':
            # EFB HTTP integration example
            efb = EFBIntegration("http://localhost:8080")  # Change to your EFB URL
            
            receiver = GDL90Receiver()
            receiver.set_aircraft_callback(efb.handle_aircraft_update)
            
            print("Starting EFB integration mode...")
            print("Make sure your EFB is running on http://localhost:8080")
            
            try:
                receiver.start()
            except KeyboardInterrupt:
                print("\nShutting down EFB integration...")
                receiver.stop()
                
        elif mode == 'file':
            file_output_example()
            
        elif mode == 'tcp':
            tcp_server_example()
            
        else:
            print("Unknown mode. Available modes: efb, file, tcp")
    else:
        print("EFB Integration Examples")
        print("Usage:")
        print("  python efb_integration_example.py efb   # HTTP integration")
        print("  python efb_integration_example.py file  # File output")
        print("  python efb_integration_example.py tcp   # TCP server")


if __name__ == "__main__":
    main()
