/*
 * ==============================================================================
 * M.I.N.E.R.S. Rover - Wemos D1 ESP8266 High-Speed Wi-Fi Bridge
 * Board: LOLIN(WEMOS) D1 R2 & mini (or Wemos D1 R1)
 * ==============================================================================
 * WIRING TO ARDUINO MEGA 2560:
 * Mega TX1 (Pin 18)  ----->  Wemos D1 RX (GPIO 3)  [TX goes to RX!]
 * Mega RX1 (Pin 19)  <-----  Wemos D1 TX (GPIO 1)  [RX goes to TX!]
 * Mega GND           <-----> Wemos D1 GND          [Common Ground!]
 * ==============================================================================
 */

#include <ESP8266WiFi.h>
#include <WebSocketsServer.h>

const char *ssid = "MINERS_ROVER_AP";
const char *password = "123456789";

WebSocketsServer webSocket = WebSocketsServer(8888);

// Explicit Static IP for reliability
IPAddress local_ip(192, 168, 4, 1);
IPAddress gateway(192, 168, 4, 1);
IPAddress subnet(255, 255, 255, 0);

void webSocketEvent(uint8_t num, WStype_t type, uint8_t * payload, size_t length) {
  if (type == WStype_CONNECTED) {
    // New laptop client connected
    webSocket.sendTXT(num, "{\"status\":\"WEMOS_BRIDGE_CONNECTED\"}");
  } else if (type == WStype_TEXT) {
    // Forward command from laptop directly to Mega Serial1
    String msg = String((char*)payload);
    Serial.println(msg);
  }
}

void setup() {
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, HIGH); // OFF (Active LOW)

  // Serial to Arduino Mega Serial1
  Serial.begin(115200);
  Serial.setTimeout(20); // Non-blocking fast timeout!

  // Configure Wi-Fi Access Point
  WiFi.mode(WIFI_AP);
  WiFi.softAPConfig(local_ip, gateway, subnet);
  WiFi.softAP(ssid, password);

  // Start WebSocket Server on Port 8888
  webSocket.begin();
  webSocket.onEvent(webSocketEvent);
}

void loop() {
  webSocket.loop();

  // Fast non-blocking read from Arduino Mega
  if (Serial.available() > 0) {
    String telemetryLine = Serial.readStringUntil('\n');
    telemetryLine.trim();
    if (telemetryLine.length() > 0 && telemetryLine.startsWith("{")) {
      digitalWrite(LED_BUILTIN, LOW); // Flash LED ON when packet forwarded
      webSocket.broadcastTXT(telemetryLine);
      digitalWrite(LED_BUILTIN, HIGH); // Flash LED OFF
    }
  }
}
