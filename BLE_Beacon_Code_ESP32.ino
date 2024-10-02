#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEServer.h>
#include <BLEBeacon.h>

#define DEVICE_NAME "BLE_Beacon_1"  // Change for each beacon
#define BEACON_UUID "8ec76ea3-6668-48da-9866-75be8bc86f4d"  // Use a unique UUID for your project

BLEAdvertising *pAdvertising;
BLEBeacon myBeacon;

void setup() {
  Serial.begin(115200);
  
  BLEDevice::init(DEVICE_NAME);
  BLEServer *pServer = BLEDevice::createServer();
  
  pAdvertising = pServer->getAdvertising();

  BLEUuid uuid = BLEUUID(BEACON_UUID);
  myBeacon.setManufacturerId(0x4C00);
  myBeacon.setProximityUUID(uuid);
  myBeacon.setMajor(1);
  myBeacon.setMinor(100);
  myBeacon.setSignalPower(-59);
  
  BLEAdvertisementData advertisementData;
  advertisementData.setFlags(0x04);
  advertisementData.setManufacturerData(myBeacon.getData());
  pAdvertising->setAdvertisementData(advertisementData);
}

void loop() {
  pAdvertising->start();
  delay(100);
  pAdvertising->stop();
  delay(100);
}