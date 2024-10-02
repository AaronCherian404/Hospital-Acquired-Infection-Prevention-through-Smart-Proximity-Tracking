import numpy as np

ble_beacons = [(0, 0), (5, 0), (2.5, 4.33)]  # Define BLE beacon positions

def rssi_to_distance(rssi, tx_power=-59):
    if rssi == 0:
        return -1  # No signal
    ratio = rssi * 1.0 / tx_power
    if ratio < 1.0:
        return pow(ratio, 10)
    else:
        return (0.89976) * pow(ratio, 7.7095) + 0.111

def triangulate(distances):
    A = 2 * (ble_beacons[1][0] - ble_beacons[0][0])
    B = 2 * (ble_beacons[1][1] - ble_beacons[0][1])
    C = distances[0]**2 - distances[1]**2 + ble_beacons[1][0]**2 - ble_beacons[0][0]**2 + ble_beacons[1][1]**2 - ble_beacons[0][1]**2
    D = 2 * (ble_beacons[2][0] - ble_beacons[0][0])
    E = 2 * (ble_beacons[2][1] - ble_beacons[0][1])
    F = distances[0]**2 - distances[2]**2 + ble_beacons[2][0]**2 - ble_beacons[0][0]**2 + ble_beacons[2][1]**2 - ble_beacons[0][1]**2

    x = (C - F * E / B) / (A - D * E / B)
    y = (C - A * x) / B
    return (x, y)

def proximity(device1_rssi, device2_rssi):
    distance1 = rssi_to_distance(device1_rssi)
    distance2 = rssi_to_distance(device2_rssi)
    return abs(distance1 - distance2)
