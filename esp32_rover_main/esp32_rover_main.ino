/*
 * ==============================================================================
 * M.I.N.E.R.S. Rover - ESP32 Main Board Firmware (WROOM-32)
 * Features:
 * 1. 8-Direction Ultrasonic Sonar Array (N, NE, E, SE, S, SW, W, NW)
 * 2. 3x Multi-Gas Sensor Array (MQ-4 CH4, MQ-7 CO, MQ-2 Smoke)
 * 3. Wi-Fi Access Point & WebSockets Telemetry Server (Port 8888)
 * 4. Hardware Serial2 (TX2=17, RX2=16 @ 115200) to ESP8266 Motor Sub-Board
 * 5. Sector 1 (Manual WASD Teleop with 30cm Crash Prevention Safety Governor)
 * 6. Sector 2 (Autonomous Navigation with Auto Obstacle Detour & Path Resume)
 * ==============================================================================
 */

#include <WiFi.h>
#include <WiFiAP.h>
#include <WebSocketsServer.h>
#include <ArduinoJson.h>

const char *ssid = "MINERS_ROVER_AP";
const char *password = "123456789";

WebSocketsServer webSocket = WebSocketsServer(8888);

// --- 8-DIRECTION ULTRASONIC SONAR PINOUT ---
const int TRIG_N  = 23; const int ECHO_N  = 22;
const int TRIG_NE = 19; const int ECHO_NE = 21;
const int TRIG_E  = 18; const int ECHO_E  = 5;
const int TRIG_SE = 4;  const int ECHO_SE = 2;
const int TRIG_S  = 15; const int ECHO_S  = 13;
const int TRIG_SW = 12; const int ECHO_SW = 14;
const int TRIG_W  = 27; const int ECHO_W  = 26;
const int TRIG_NW = 33; const int ECHO_NW = 32;

// --- 3x GAS SENSORS (ANALOG INPUTS) ---
const int PIN_MQ4 = 36; // VP (CH4 Methane)
const int PIN_MQ7 = 39; // VN (CO Carbon Monoxide)
const int PIN_MQ2 = 34; // GPIO 34 (LPG/Smoke)

// --- OBSTACLE SAFETY THRESHOLD ---
const int OBSTACLE_STOP_CM = 30; // 30cm Safety Boundary for BOTH Modes

// --- TELEMETRY & SYSTEM STATE ---
long distN = 100, distNE = 100, distE = 100, distSE = 100;
long distS = 100, distSW = 100, distW = 100, distNW = 100;

int valMQ4 = 0, valMQ7 = 0, valMQ2 = 0;
char currentMotion = 'S'; // 'F','B','L','R','S'

enum ModeSector {
  SECTOR_1_MANUAL = 1,
  SECTOR_2_AUTOMATIC = 2
};

ModeSector currentSector = SECTOR_1_MANUAL;

// --- SECTOR 2 DYNAMIC MAP STRUCTURE ---
struct MapSegment {
  float lengthMeters;
  char turnAction; // 'R' = Right, 'L' = Left, 'F' = Straight, 'E' = End
};

#define MAX_MAP_SEGMENTS 10
MapSegment missionMap[MAX_MAP_SEGMENTS] = {
  { 10.0, 'R' }, // Segment 0: 10m forward -> Turn Right
  { 20.0, 'E' }  // Segment 1: 20m forward -> End Mission
};

int totalSegments = 2;
int currentSegment = 0;
float distanceTraveledMeters = 0.0;
unsigned long stateStartTime = 0;
const float EST_SPEED_MPS = 0.35; // ~0.35 m/s speed

// Timers
unsigned long lastSonarScanTime = 0;
unsigned long lastTelemetryTime = 0;

// Function Prototypes
long readUltrasonic(int trigPin, int echoPin);
void sendMotorCommand(char dir, int speedVal);
void executeAutonomousLogic();
void broadcastTelemetry();
void webSocketEvent(uint8_t num, WStype_t type, uint8_t * payload, size_t length);

void setup() {
  Serial.begin(115200);   
  Serial2.begin(115200, SERIAL_8N1, 16, 17); // UART2 to ESP8266 (RX=16, TX=17)

  int trigPins[] = {TRIG_N, TRIG_NE, TRIG_E, TRIG_SE, TRIG_S, TRIG_SW, TRIG_W, TRIG_NW};
  int echoPins[] = {ECHO_N, ECHO_NE, ECHO_E, ECHO_SE, ECHO_S, ECHO_SW, ECHO_W, ECHO_NW};
  
  for (int i = 0; i < 8; i++) {
    pinMode(trigPins[i], OUTPUT);
    pinMode(echoPins[i], INPUT);
  }

  WiFi.softAP(ssid, password);
  IPAddress apIP = WiFi.softAPIP();
  Serial.print("[ESP32 AP Ready] IP: ");
  Serial.println(apIP);

  webSocket.begin();
  webSocket.onEvent(webSocketEvent);
  Serial.println("[ESP32 WebSocket Server Started on Port 8888]");
}

void loop() {
  webSocket.loop();
  
  // 1. Scan 8-Direction Sonar Array & Gas Sensors (every 60ms)
  if (millis() - lastSonarScanTime > 60) {
    lastSonarScanTime = millis();
    
    distN  = readUltrasonic(TRIG_N, ECHO_N);
    distNE = readUltrasonic(TRIG_NE, ECHO_NE);
    distE  = readUltrasonic(TRIG_E, ECHO_E);
    distSE = readUltrasonic(TRIG_SE, ECHO_SE);
    distS  = readUltrasonic(TRIG_S, ECHO_S);
    distSW = readUltrasonic(TRIG_SW, ECHO_SW);
    distW  = readUltrasonic(TRIG_W, ECHO_W);
    distNW = readUltrasonic(TRIG_NW, ECHO_NW);
    
    valMQ4 = analogRead(PIN_MQ4);
    valMQ7 = analogRead(PIN_MQ7);
    valMQ2 = analogRead(PIN_MQ2);
  }

  // 2. Execute Sector 2 Autonomous Engine if active
  if (currentSector == SECTOR_2_AUTOMATIC) {
    executeAutonomousLogic();
  }

  // 3. Broadcast JSON Telemetry to Laptop (every 100ms)
  if (millis() - lastTelemetryTime > 100) {
    lastTelemetryTime = millis();
    broadcastTelemetry();
  }
}

long readUltrasonic(int trigPin, int echoPin) {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);
  
  long duration = pulseIn(echoPin, HIGH, 20000); // 20ms timeout
  if (duration == 0) return 350; // Clear path
  long distanceCm = duration * 0.034 / 2;
  return constrain(distanceCm, 2, 350);
}

void sendMotorCommand(char dir, int speedVal) {
  // SAFETY GOVERNOR ENFORCEMENT FOR MANUAL FORWARD COMMANDS:
  // Prevent Forward motion if obstacle < 30 cm in front (N, NE, NW)
  if (dir == 'F' && (distN < OBSTACLE_STOP_CM || distNE < OBSTACLE_STOP_CM || distNW < OBSTACLE_STOP_CM)) {
    dir = 'S';
    speedVal = 0;
    Serial.println("[SAFETY GOVERNOR] Forward Motion Override: Obstacle < 30cm Detected!");
  }
  
  currentMotion = dir;
  String cmdStr = "M:" + String(dir) + ":" + String(speedVal) + "\n";
  Serial2.print(cmdStr);
}

void executeAutonomousLogic() {
  unsigned long elapsed = millis() - stateStartTime;
  distanceTraveledMeters = (elapsed / 1000.0) * EST_SPEED_MPS;

  // --- SECTOR 2 AUTOMATIC OBSTACLE DETOUR & PATH RESUME ---
  if (distN < OBSTACLE_STOP_CM || distNE < OBSTACLE_STOP_CM || distNW < OBSTACLE_STOP_CM) {
    // 1. Immediate Halt
    sendMotorCommand('S', 0);
    delay(200);
    
    // 2. Evaluate Left vs Right clearance
    if (distW > distE) {
      // Pivot Turn Left until Front Path is clear (> 45cm)
      while (distN < 45) {
        sendMotorCommand('L', 180);
        delay(150);
        distN = readUltrasonic(TRIG_N, ECHO_N);
      }
    } else {
      // Pivot Turn Right until Front Path is clear (> 45cm)
      while (distN < 45) {
        sendMotorCommand('R', 180);
        delay(150);
        distN = readUltrasonic(TRIG_N, ECHO_N);
      }
    }
    
    // 3. Short bypass step forward
    sendMotorCommand('F', 180);
    delay(500);
    return;
  }

  // Segment Path Continuation
  MapSegment seg = missionMap[currentSegment];

  if (distanceTraveledMeters < seg.lengthMeters) {
    sendMotorCommand('F', 180); // Continue forward along corridor
  } else {
    // Target Segment Length Reached -> Execute Turn Action
    if (seg.turnAction == 'R') {
      sendMotorCommand('R', 200); // 90° Right Pivot Turn
      delay(900);
      currentSegment++;
      stateStartTime = millis();
    } else if (seg.turnAction == 'L') {
      sendMotorCommand('L', 200); // 90° Left Pivot Turn
      delay(900);
      currentSegment++;
      stateStartTime = millis();
    } else if (seg.turnAction == 'F') {
      currentSegment++;
      stateStartTime = millis();
    } else {
      sendMotorCommand('S', 0); // Mission Complete
    }
  }
}

void broadcastTelemetry() {
  StaticJsonDocument<512> doc;
  doc["sector"] = (int)currentSector;
  doc["motion"] = String(currentMotion);
  
  JsonObject sonar = doc.createNestedObject("sonar");
  sonar["N"]  = distN;  sonar["NE"] = distNE;
  sonar["E"]  = distE;  sonar["SE"] = distSE;
  sonar["S"]  = distS;  sonar["SW"] = distSW;
  sonar["W"]  = distW;  sonar["NW"] = distNW;

  JsonObject gas = doc.createNestedObject("gas");
  gas["mq4"] = valMQ4;
  gas["mq7"] = valMQ7;
  gas["mq2"] = valMQ2;
  
  doc["dist_m"] = distanceTraveledMeters;
  doc["segment"] = currentSegment;
  doc["total_seg"] = totalSegments;

  String output;
  serializeJson(doc, output);
  webSocket.broadcastTXT(output);
}

void webSocketEvent(uint8_t num, WStype_t type, uint8_t * payload, size_t length) {
  if (type == WStype_TEXT) {
    String msg = String((char*)payload);
    msg.trim();
    
    if (msg.startsWith("SECTOR:")) {
      int sec = msg.substring(7).toInt();
      currentSector = (ModeSector)sec;
      if (currentSector == SECTOR_2_AUTOMATIC) {
        stateStartTime = millis();
        currentSegment = 0;
      } else {
        sendMotorCommand('S', 0);
      }
    } else if (msg.startsWith("CMD:") && currentSector == SECTOR_1_MANUAL) {
      char dir = msg.charAt(4);
      int spd = msg.substring(6).toInt();
      sendMotorCommand(dir, spd);
    } else if (msg.startsWith("MAP:")) {
      String jsonStr = msg.substring(4);
      StaticJsonDocument<1024> mapDoc;
      DeserializationError err = deserializeJson(mapDoc, jsonStr);
      if (!err) {
        JsonArray arr = mapDoc.as<JsonArray>();
        int idx = 0;
        for (JsonObject item : arr) {
          if (idx < MAX_MAP_SEGMENTS) {
            missionMap[idx].lengthMeters = item["len"] | 10.0;
            String turnStr = item["turn"] | "E";
            missionMap[idx].turnAction = turnStr.charAt(0);
            idx++;
          }
        }
        totalSegments = idx;
        currentSegment = 0;
        stateStartTime = millis();
      }
    }
  }
}
