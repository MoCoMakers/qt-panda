#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <Wire.h>
#include <WiFi.h>.
#include <WiFiUdp.h>

Adafruit_MPU6050 mpu;
const char* ssid = "ESP32C3_Vibration";
const char* password = "Vibrate";
const char* destip = "192.168.4.2";

WiFiUDP udp;
unsigned int sendUdpPort = 4210;  //  port to send data on


void setup(void) 
{
  WiFi.mode(WIFI_STA); // connect to existing wifi access point
  WiFi.mode(WIFI_AP); // set up as AP
  
  Serial.begin(115200); // start serial conenction

  Serial.println("Adafruit MPU6050 test!");
 // WiFi.begin(ssid, password);
  WiFi.softAP(ssid, password);
  
  Serial.print("Setting up access point as : ");
  Serial.println(ssid);

   Serial.print("Access point IP: ");
  Serial.println(WiFi.softAPIP());

  Serial.print("Sending data on UDP port : ");
  Serial.println(sendUdpPort);
  Serial.print("to IP address  : ");
  Serial.println(destip);

 
  // Try to initialize!
  if (!mpu.begin()) 
  {
    Serial.println("Failed to find MPU6050 chip");
    while (1) 
    {
      delay(10);
    }
  }
  Serial.println("MPU6050 Found!");

  mpu.setAccelerometerRange(MPU6050_RANGE_2_G); // set to max sensistivity
  mpu.setGyroRange(MPU6050_RANGE_250_DEG); // set to max sensistivity
  mpu.setFilterBandwidth(MPU6050_BAND_260_HZ);
  Serial.print("Filter bandwidth set to: ");
  switch (mpu.getFilterBandwidth()) {
  case MPU6050_BAND_260_HZ:
    Serial.println("260 Hz");
    break;
  case MPU6050_BAND_184_HZ:
    Serial.println("184 Hz");
    break;
  case MPU6050_BAND_94_HZ:
    Serial.println("94 Hz");
    break;
  case MPU6050_BAND_44_HZ:
    Serial.println("44 Hz");
    break;
  case MPU6050_BAND_21_HZ:
    Serial.println("21 Hz");
    break;
  case MPU6050_BAND_10_HZ:
    Serial.println("10 Hz");
    break;
  case MPU6050_BAND_5_HZ:
    Serial.println("5 Hz");
    break;
  }

  Serial.println("");
  delay(100);
}


//uint8_t buffer[1400];
void loop() {

  /* Get new sensor events with the readings */
  
  sensors_event_t a, g, temp;
  mpu.getEvent(&a, &g, &temp);

  udp.beginPacket(destip, sendUdpPort); // Send to the specified IP and port
  //udp.write(buffer, 100);
  
  //udp.print("Hello, UDP!"); // Or any data you want to send
  udp.print(a.acceleration.x);
  udp.print(",");// Y: ");
  udp.print(a.acceleration.y);
  udp.print(",");// Z: ");
  udp.println(a.acceleration.z);  
  
  udp.endPacket();

}
