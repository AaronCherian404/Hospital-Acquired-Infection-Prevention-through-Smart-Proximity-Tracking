from flask import Flask, request, jsonify, render_template
from datetime import datetime
import time
import logging
from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple
import numpy as np

# Enhanced logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@dataclass
class BeaconData:
    position: Tuple[int, int]
    battery: float
    last_seen: float

@dataclass
class DeviceContact:
    device_id: str
    start_time: float
    duration: float

@dataclass
class DeviceData:
    rssi_readings: Dict[str, List[float]]  # Changed to store list of readings for averaging
    last_seen: float
    position: Tuple[float, float]  # Changed to float for more precise positioning
    contacts: List[DeviceContact]
    device_type: str

# Global state
beacons: Dict[str, BeaconData] = {
    'ESP32_1': BeaconData((0, 0), 100, time.time()),
    'ESP32_2': BeaconData((3, 0), 100, time.time()),
    'ESP32_3': BeaconData((1, 2), 100, time.time())
}

class ProximityTracker:
    def __init__(self):
        self.devices: Dict[str, DeviceData] = {}
        self.close_contacts: Dict[Tuple[str, str], float] = {}
        self.rssi_window = 5  # Number of RSSI readings to average
    
    def update_device(self, device_id: str, rssi_reading: float, beacon_id: str, device_type: str = 'unknown'):
        logger.debug(f"Updating device: {device_id} from beacon: {beacon_id} with RSSI: {rssi_reading}")
        current_time = time.time()
        
        # Initialize new device if not seen before
        if device_id not in self.devices:
            logger.info(f"New device detected: {device_id}")
            self.devices[device_id] = DeviceData(
                rssi_readings={beacon_id: []},
                last_seen=current_time,
                position=(0.0, 0.0),
                contacts=[],
                device_type=device_type
            )
        
        device = self.devices[device_id]
        
        # Initialize RSSI readings list for new beacon
        if beacon_id not in device.rssi_readings:
            device.rssi_readings[beacon_id] = []
        
        # Add new RSSI reading and maintain window size
        device.rssi_readings[beacon_id].append(rssi_reading)
        if len(device.rssi_readings[beacon_id]) > self.rssi_window:
            device.rssi_readings[beacon_id].pop(0)
        
        device.last_seen = current_time
        device.device_type = device_type
        
        # Update position if we have enough readings
        if len(device.rssi_readings) >= 2:
            # Calculate average RSSI for each beacon
            avg_rssi = {
                b_id: sum(readings) / len(readings)
                for b_id, readings in device.rssi_readings.items()
                if readings  # Only use beacons with readings
            }
            
            # Convert to distances
            distances = {
                b_id: rssi_to_distance(avg_rssi[b_id])
                for b_id in avg_rssi
            }
            
            # Update position
            device.position = estimate_position(distances)
            logger.debug(f"Updated position for {device_id}: {device.position}")
        
        self._cleanup_old_data()

    def _cleanup_old_data(self):
        current_time = time.time()
        threshold = current_time - 10  # Reduced to 10 seconds for more responsive cleanup
        
        old_devices = [
            device_id for device_id, device in self.devices.items()
            if device.last_seen < threshold
        ]
        
        for device_id in old_devices:
            logger.info(f"Removing inactive device: {device_id}")
            del self.devices[device_id]

def rssi_to_distance(rssi: float) -> float:
    """Convert RSSI to distance using improved path loss model"""
    N = 2.0  # Path loss exponent (2.0 for free space)
    A = -60  # RSSI value at 1 meter distance (calibration value)
    
    # Add environmental factor
    env_factor = 0.5
    
    distance = 10 ** ((A - rssi) / (10 * N)) * (1 + env_factor)
    return min(max(distance, 0.1), 10.0)

def estimate_position(distances: Dict[str, float]) -> Tuple[float, float]:
    """Estimate position using weighted trilateration"""
    total_weight = 0
    x, y = 0.0, 0.0
    
    # Calculate confidence weights based on distance
    weights = {
        beacon_id: 1 / (distance ** 2)
        for beacon_id, distance in distances.items()
    }
    
    # Normalize weights
    weight_sum = sum(weights.values())
    if weight_sum > 0:
        weights = {k: v/weight_sum for k, v in weights.items()}
    
    # Calculate weighted position
    for beacon_id, distance in distances.items():
        weight = weights[beacon_id]
        beacon_pos = beacons[beacon_id].position
        x += beacon_pos[0] * weight
        y += beacon_pos[1] * weight
        total_weight += weight
    
    if total_weight > 0:
        return (x / total_weight, y / total_weight)
    return (0.0, 0.0)

# Initialize global tracker
proximity_tracker = ProximityTracker()

@app.route('/')
def index():
    logger.debug("Loading index page")
    return render_template('index.html')

@app.route('/ble-data', methods=['POST'])
def ble_data():
    try:
        data = request.get_json()
        logger.debug(f"Received BLE data: {data}")
        
        beacon_id = data['beacon']
        beacon_battery = data.get('battery', 100)
        received_devices = data.get('devices', [])
        
        if beacon_id in beacons:
            beacons[beacon_id].battery = beacon_battery
            beacons[beacon_id].last_seen = time.time()
            logger.debug(f"Updated beacon {beacon_id} battery: {beacon_battery}")
        
        for device in received_devices:
            device_id = device['id']
            rssi = device['rssi']
            # Filtering out obviously invalid RSSI values
            if -100 <= rssi <= 0:
                proximity_tracker.update_device(device_id, rssi, beacon_id)
        
        logger.debug(f"Currently tracking {len(proximity_tracker.devices)} devices")
        return jsonify({'status': 'success', 'device_count': len(proximity_tracker.devices)})
    
    except Exception as e:
        logger.error(f"Error processing BLE data: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/get-proximity-data')
def get_proximity_data():
    logger.debug("Fetching proximity data")
    current_time = time.time()
    
    response_data = {
        'beacons': {
            id: {
                'position': beacon.position,
                'battery': beacon.battery,
                'last_seen': beacon.last_seen
            } for id, beacon in beacons.items()
        },
        'devices': {
            device_id: {
                'position': device.position,
                'last_seen': device.last_seen,
                'device_type': device.device_type,
                'rssi_readings': {
                    beacon_id: sum(readings)/len(readings) if readings else None
                    for beacon_id, readings in device.rssi_readings.items()
                },
                'contacts': [asdict(contact) for contact in device.contacts]
            } for device_id, device in proximity_tracker.devices.items()
        }
    }
    
    logger.debug(f"Returning data for {len(proximity_tracker.devices)} devices")
    return jsonify(response_data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
