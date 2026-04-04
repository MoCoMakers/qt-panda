
#include <basicMPU6050.h> 


#include <Wire.h>
#include <WiFi.h>.
#include <WiFiUdp.h>


// Create instance
basicMPU6050<> imu;
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

  imu.setup();

  Serial.println("");
  delay(100);
}


//uint8_t buffer[1400];
void loop() {

  /* Get new sensor events with the readings */
  
  //sensors_event_t a, g, temp;
  //mpu.getEvent(&a, &g, &temp);
  udp.beginPacket(destip, sendUdpPort); // Send to the specified IP and port
  //udp.write(buffer, 100);
  
  //udp.print("Hello, UDP!"); // Or any data you want to send
  udp.print(imu.rawAx());
  udp.print(",");// Y: ");
  udp.print(imu.rawAy());
  udp.print(",");// Z: ");
  udp.println(imu.rawAz());  
  
  udp.endPacket();

}
