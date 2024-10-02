import asyncio
from bleak import BleakScanner
from flask import Flask, jsonify
import numpy as np
import sqlite3
import json

app = Flask(__name__)

# Database setup
conn = sqlite3.connect('positions.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS positions
             (device_id TEXT, x REAL, y REAL, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
conn.commit()

# Beacon positions (x, y) in meters
BEACON_POSITIONS = {
    "BLE_Beacon_1": (0, 0),
    "BLE_Beacon_2": (5, 0),
    "BLE_Beacon_3": (2.5, 4.3)
}

def trilaterate(distances):
    A = np.array([
        [2*(BEACON_POSITIONS["BLE_Beacon_2"][0] - BEACON_POSITIONS["BLE_Beacon_1"][0]),
         2*(BEACON_POSITIONS["BLE_Beacon_2"][1] - BEACON_POSITIONS["BLE_Beacon_1"][1])],
        [2*(BEACON_POSITIONS["BLE_Beacon_3"][0] - BEACON_POSITIONS["BLE_Beacon_1"][0]),
         2*(BEACON_POSITIONS["BLE_Beacon_3"][1] - BEACON_POSITIONS["BLE_Beacon_1"][1])]
    ])
    
    b = np.array([
        [distances["BLE_Beacon_1"]**2 - distances["BLE_Beacon_2"]**2 + 
         BEACON_POSITIONS["BLE_Beacon_2"][0]**2 + BEACON_POSITIONS["BLE_Beacon_2"][1]**2 - 
         BEACON_POSITIONS["BLE_Beacon_1"][0]**2 - BEACON_POSITIONS["BLE_Beacon_1"][1]**2],
        [distances["BLE_Beacon_1"]**2 - distances["BLE_Beacon_3"]**2 + 
         BEACON_POSITIONS["BLE_Beacon_3"][0]**2 + BEACON_POSITIONS["BLE_Beacon_3"][1]**2 - 
         BEACON_POSITIONS["BLE_Beacon_1"][0]**2 - BEACON_POSITIONS["BLE_Beacon_1"][1]**2]
    ])
    
    position = np.linalg.solve(A, b)
    return position.flatten()

async def scan_ble():
    while True:
        devices = await BleakScanner.discover()
        for d in devices:
            if d.name and d.name.startswith("BLE_Beacon"):
                # Convert RSSI to distance (simplified)
                distance = 10 ** (((-59 - d.rssi) / (10 * 2)))
                yield (d.name, distance)
        await asyncio.sleep(1)

async def position_calculator():
    distances = {}
    async for beacon, distance in scan_ble():
        distances[beacon] = distance
        if len(distances) == 3:
            position = trilaterate(distances)
            # Store position in database
            c.execute("INSERT INTO positions (device_id, x, y) VALUES (?, ?, ?)",
                      ("user_device", position[0], position[1]))
            conn.commit()
            distances.clear()

@app.route('/get_position')
def get_position():
    c.execute("SELECT x, y, timestamp FROM positions ORDER BY timestamp DESC LIMIT 1")
    result = c.fetchone()
    if result:
        return jsonify({"x": result[0], "y": result[1], "timestamp": result[2]})
    else:
        return jsonify({"error": "No position data available"})

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(position_calculator())
    app.run(debug=True, use_reloader=False)