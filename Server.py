from flask import Flask, request, jsonify
from triangulation import triangulate, rssi_to_distance, proximity

app = Flask(__name__)

@app.route('/ble-data', methods=['POST'])
def ble_data():
    data = request.get_json()
    devices = data.get("devices", [])
    
    # Assume we receive RSSI for each device from multiple beacons
    distances = []
    for device in devices:
        rssi = device['rssi']
        distance = rssi_to_distance(rssi)
        distances.append(distance)
    
    if len(distances) >= 3:
        position = triangulate(distances)
        return jsonify({"position": position})
    
    return jsonify({"message": "Not enough data"}), 400

@app.route('/proximity', methods=['POST'])
def calculate_proximity():
    data = request.get_json()
    device1_rssi = data.get("device1_rssi")
    device2_rssi = data.get("device2_rssi")
    
    if device1_rssi is not None and device2_rssi is not None:
        prox = proximity(device1_rssi, device2_rssi)
        return jsonify({"proximity": prox})
    
    return jsonify({"message": "Invalid data"}), 400

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
