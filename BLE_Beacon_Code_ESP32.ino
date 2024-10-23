#include <Arduino.h>
#include <WiFi.h>
#include <ArduinoJson.h>
#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEScan.h>
#include <BLEAdvertisedDevice.h>
#include <HTTPClient.h>
#include <base64.h>


// Configuration
#define DEVICE_ID "ESP32_1"  // Change for each ESP32
#define WIFI_SSID "Error 404"
#define WIFI_PASSWORD "harmonya101"
#define SERVER_URL "http://172.20.10.3:5000/ble-data"
#define SCAN_TIME 5 // Time in seconds to scan for devices

// Structure to hold device information
struct DeviceInfo {
  String id;
  int rssi;
  unsigned long lastSeen;
};

// Array to store found devices
#define MAX_DEVICES 10
DeviceInfo devices[MAX_DEVICES];
int deviceCount = 0;

// Global BLE scanner pointer
BLEScan* pBLEScan = nullptr;

class MyAdvertisedDeviceCallbacks: public BLEAdvertisedDeviceCallbacks {
    void onResult(BLEAdvertisedDevice advertisedDevice) {
      // Get the address as a string
      String deviceId = advertisedDevice.getAddress().toString().c_str();
      
      // Check if device already exists in our array
      for (int i = 0; i < deviceCount; i++) {
        if (devices[i].id == deviceId) {
          devices[i].rssi = advertisedDevice.getRSSI();
          devices[i].lastSeen = millis();
          return;
        }
      }
      
      // Add new device if space available
      if (deviceCount < MAX_DEVICES) {
        devices[deviceCount].id = deviceId;
        devices[deviceCount].rssi = advertisedDevice.getRSSI();
        devices[deviceCount].lastSeen = millis();
        deviceCount++;
      }
    }
};

void setupWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nConnected to WiFi");
    Serial.print("IP Address: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\nFailed to connect to WiFi");
  }
}

void setupBLE() {
  BLEDevice::init(DEVICE_ID);
  pBLEScan = BLEDevice::getScan();
  if (pBLEScan) {
    pBLEScan->setAdvertisedDeviceCallbacks(new MyAdvertisedDeviceCallbacks(), true);
    pBLEScan->setActiveScan(true);
    pBLEScan->setInterval(100);
    pBLEScan->setWindow(99);
  } else {
    Serial.println("Failed to initialize BLE scan");
  }
}

void setup() {
  Serial.begin(115200);
  while (!Serial) delay(10);  // Wait for serial connection
  
  Serial.println("Starting BLE Scanner...");
  
  setupWiFi();
  setupBLE();
}

void sendDataToServer() {
  if (WiFi.status() != WL_CONNECTED) return;

  StaticJsonDocument<1024> doc;
  doc["beacon"] = DEVICE_ID;
  doc["timestamp"] = millis();
  
  JsonArray deviceArray = doc.createNestedArray("devices");
  
  unsigned long currentTime = millis();
  for (int i = 0; i < deviceCount; i++) {
    if (currentTime - devices[i].lastSeen < 10000) { // Only include recently seen devices
      JsonObject device = deviceArray.createNestedObject();
      device["id"] = devices[i].id;
      device["rssi"] = devices[i].rssi;
    }
  }
  
  String jsonString;
  serializeJson(doc, jsonString);
  
  HTTPClient http;
  http.begin(SERVER_URL);
  http.addHeader("Content-Type", "application/json");
  
  int httpResponseCode = http.POST(jsonString);
  
  if (httpResponseCode > 0) {
    String response = http.getString();
    Serial.println("HTTP Response: " + response);
  } else {
    Serial.println("Error sending HTTP POST: " + String(httpResponseCode));
  }
  
  http.end();
}

void loop() {
  // Check WiFi connection
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi disconnected. Reconnecting...");
    setupWiFi();
    return;
  }

  // Reset device count before new scan
  deviceCount = 0;
  
  Serial.println("Scanning for BLE devices...");
  
  // Perform BLE scan
  if (pBLEScan) {
    pBLEScan->start(SCAN_TIME, false);
    Serial.print("Devices found: ");
    Serial.println(deviceCount);
    pBLEScan->clearResults();
  }

  // Send data to server
  sendDataToServer();
  
  // Small delay before next scan
  delay(1000);
}
