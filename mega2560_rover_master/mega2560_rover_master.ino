/*
 * ==============================================================================
 * M.I.N.E.R.S. Rover - Arduino Mega 2560 Master Rover Firmware
 * Dual-Sensor 4-Direction Sonar Configuration (2 Sensors per Direction = 8 Total)
 * 1. FRONT: Front-1 (Pin 22/23) & Front-2 (Pin 42/43)
 * 2. RIGHT: Right-1 (Pin 26/27) & Right-2 (Pin 46/47)
 * 3. REAR:  Rear-1  (Pin 50/51) & Rear-2  (Pin 48/49)
 * 4. LEFT:  Left-1  (Pin 24/25) & Left-2  (Pin 40/41)
 * ==============================================================================
 */

// --- MOTOR DRIVER SELECTION ---
#define USE_BTS7960 true  // Set to true for BTS7960 (RPWM/LPWM), false for L298N

// --- BTS7960 MOTOR DRIVER PINOUT (2x BTS7960 MODULES OR DUAL H-BRIDGE) ---
const int L_RPWM = 2;  // Left Motor Forward PWM
const int L_LPWM = 3;  // Left Motor Reverse PWM
const int R_RPWM = 4;  // Right Motor Forward PWM
const int R_LPWM = 5;  // Right Motor Reverse PWM
const int L_EN   = 30; // Left Enable Pin (Connect to L_EN & R_EN on Left Driver, or wire directly to 5V)
const int R_EN   = 32; // Right Enable Pin (Connect to L_EN & R_EN on Right Driver, or wire directly to 5V)

// --- L298N MOTOR DRIVER PINOUT FALLBACK ---
const int L_IN1 = 30;
const int L_IN2 = 31;
const int L_ENA = 2;

const int R_IN3 = 32;
const int R_IN4 = 33;
const int R_ENB = 3;

// --- 4-DIRECTION DUAL ULTRASONIC SENSORS PINOUT (CORRECTED PHYSICAL ORIENTATION) ---
// FRONT DIRECTION (Previously Rear Pins)
const int TRIG_FRONT1 = 50; const int ECHO_FRONT1 = 51;
const int TRIG_FRONT2 = 48; const int ECHO_FRONT2 = 49;

// RIGHT DIRECTION (Previously Left Pins)
const int TRIG_RIGHT1 = 24; const int ECHO_RIGHT1 = 25;
const int TRIG_RIGHT2 = 40; const int ECHO_RIGHT2 = 41;

// REAR DIRECTION (Previously Front Pins)
const int TRIG_REAR1  = 22; const int ECHO_REAR1  = 23;
const int TRIG_REAR2  = 42; const int ECHO_REAR2  = 43;

// LEFT DIRECTION (Previously Right Pins)
const int TRIG_LEFT1  = 26; const int ECHO_LEFT1  = 27;
const int TRIG_LEFT2  = 46; const int ECHO_LEFT2  = 47;

// --- 3x GAS SENSORS (ANALOG INPUTS) ---
const int PIN_MQ4 = A0; // Methane (CH4)
const int PIN_MQ7 = A1; // Carbon Monoxide (CO)
const int PIN_MQ2 = A2; // Smoke / LPG

// --- OBSTACLE SAFETY GOVERNOR (DISABLED FOR TRIALS AS REQUESTED) ---
bool obstacleGovernorActive = false; // Set to false to allow free testing without sensor blockage
const int OBSTACLE_STOP_CM = 30;     // 30cm safety threshold if governor enabled

// Sensor individual & combined distances
long distFront1 = 100, distFront2 = 100;
long distRight1 = 100, distRight2 = 100;
long distRear1  = 100, distRear2  = 100;
long distLeft1  = 100, distLeft2  = 100;

long distFront = 100, distRight = 100, distRear = 100, distLeft = 100;

int valMQ4 = 0, valMQ7 = 0, valMQ2 = 0;
char currentMotion = 'S';

enum ModeSector {
  SECTOR_1_MANUAL = 1,
  SECTOR_2_AUTOMATIC = 2
};
ModeSector currentSector = SECTOR_1_MANUAL;

// Dynamic Map Structure
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
const float EST_SPEED_MPS = 0.35; // ~0.35 m/s

// Timers
unsigned long lastSonarScanTime = 0;
unsigned long lastTelemetryTime = 0;

// Function Prototypes
long readUltrasonic(int trigPin, int echoPin);
void driveMotors(int l_in1, int l_in2, int l_pwm, int r_in3, int r_in4, int r_pwm);
void sendMotorCommand(char dir, int speedVal);
void executeAutonomousLogic();
void broadcastTelemetry();
void parseSerialCommand(String msg);

void setup() {
  Serial.begin(115200);   // USB Monitor
  Serial1.begin(115200);  // Hardware Serial1 to Wemos D1 (TX1=18, RX1=19)

  // Motor Pins
#if USE_BTS7960
  pinMode(L_RPWM, OUTPUT);
  pinMode(L_LPWM, OUTPUT);
  pinMode(R_RPWM, OUTPUT);
  pinMode(R_LPWM, OUTPUT);
  pinMode(L_EN, OUTPUT);
  pinMode(R_EN, OUTPUT);
  digitalWrite(L_EN, HIGH);
  digitalWrite(R_EN, HIGH);
#else
  pinMode(L_IN1, OUTPUT);
  pinMode(L_IN2, OUTPUT);
  pinMode(L_ENA, OUTPUT);
  pinMode(R_IN3, OUTPUT);
  pinMode(R_IN4, OUTPUT);
  pinMode(R_ENB, OUTPUT);
#endif
  sendMotorCommand('S', 0);

  // Ultrasonic Pins (8 total)
  int trigPins[] = {TRIG_FRONT1, TRIG_FRONT2, TRIG_RIGHT1, TRIG_RIGHT2, TRIG_REAR1, TRIG_REAR2, TRIG_LEFT1, TRIG_LEFT2};
  int echoPins[] = {ECHO_FRONT1, ECHO_FRONT2, ECHO_RIGHT1, ECHO_RIGHT2, ECHO_REAR1, ECHO_REAR2, ECHO_LEFT1, ECHO_LEFT2};
  for (int i = 0; i < 8; i++) {
    pinMode(trigPins[i], OUTPUT);
    pinMode(echoPins[i], INPUT);
  }

  Serial.println("[Arduino Mega 2560 Ready - Obstacle Governor DISABLED for Trials]");
}

void loop() {
  // 1. Read commands from Wemos D1 Wi-Fi (via Serial1) or USB (Serial)
  if (Serial1.available() > 0) {
    String line = Serial1.readStringUntil('\n');
    line.trim();
    if (line.length() > 0) parseSerialCommand(line);
  }
  if (Serial.available() > 0) {
    String line = Serial.readStringUntil('\n');
    line.trim();
    if (line.length() > 0) parseSerialCommand(line);
  }

  // 2. Scan Dual-Sensors across 4 Directions (every 80ms)
  if (millis() - lastSonarScanTime > 80) {
    lastSonarScanTime = millis();
    
    distFront1 = readUltrasonic(TRIG_FRONT1, ECHO_FRONT1);
    distFront2 = readUltrasonic(TRIG_FRONT2, ECHO_FRONT2);
    distRight1 = readUltrasonic(TRIG_RIGHT1, ECHO_RIGHT1);
    distRight2 = readUltrasonic(TRIG_RIGHT2, ECHO_RIGHT2);
    distRear1  = readUltrasonic(TRIG_REAR1,  ECHO_REAR1);
    distRear2  = readUltrasonic(TRIG_REAR2,  ECHO_REAR2);
    distLeft1  = readUltrasonic(TRIG_LEFT1,  ECHO_LEFT1);
    distLeft2  = readUltrasonic(TRIG_LEFT2,  ECHO_LEFT2);

    // Combined 4 Directions (Take closest obstacle in each direction)
    distFront = min(distFront1, distFront2);
    distRight = min(distRight1, distRight2);
    distRear  = min(distRear1,  distRear2);
    distLeft  = min(distLeft1,  distLeft2);

    valMQ4 = analogRead(PIN_MQ4);
    valMQ7 = analogRead(PIN_MQ7);
    valMQ2 = analogRead(PIN_MQ2);
  }

  // 3. Sector 2 Autonomous Map Navigation
  if (currentSector == SECTOR_2_AUTOMATIC) {
    executeAutonomousLogic();
  }

  // 4. Send JSON Telemetry to Wemos D1 and USB (every 100ms)
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

  // 12ms timeout (~200cm range) prevents multi-sensor lag
  long duration = pulseIn(echoPin, HIGH, 12000);
  if (duration == 0) return 250;
  long distCm = duration * 0.034 / 2;
  return constrain(distCm, 2, 250);
}

void driveMotors(int l_fwd, int l_rev, int l_pwm, int r_fwd, int r_rev, int r_pwm) {
#if USE_BTS7960
  // BTS7960 Motor Driver Speed & Direction Control via RPWM & LPWM
  digitalWrite(L_EN, HIGH);
  digitalWrite(R_EN, HIGH);

  // Left Side Motors
  if (l_fwd) {
    analogWrite(L_RPWM, l_pwm);
    analogWrite(L_LPWM, 0);
  } else if (l_rev) {
    analogWrite(L_RPWM, 0);
    analogWrite(L_LPWM, l_pwm);
  } else {
    analogWrite(L_RPWM, 0);
    analogWrite(L_LPWM, 0);
  }

  // Right Side Motors
  if (r_fwd) {
    analogWrite(R_RPWM, r_pwm);
    analogWrite(R_LPWM, 0);
  } else if (r_rev) {
    analogWrite(R_RPWM, 0);
    analogWrite(R_LPWM, r_pwm);
  } else {
    analogWrite(R_RPWM, 0);
    analogWrite(R_LPWM, 0);
  }
#else
  // L298N Motor Driver Control
  digitalWrite(L_IN1, l_fwd ? HIGH : LOW);
  digitalWrite(L_IN2, l_rev ? HIGH : LOW);
  if (l_pwm >= 250) {
    digitalWrite(L_ENA, HIGH);
  } else {
    analogWrite(L_ENA, l_pwm);
  }

  digitalWrite(R_IN3, r_fwd ? HIGH : LOW);
  digitalWrite(R_IN4, r_rev ? HIGH : LOW);
  if (r_pwm >= 250) {
    digitalWrite(R_ENB, HIGH);
  } else {
    analogWrite(R_ENB, r_pwm);
  }
#endif
}

void sendMotorCommand(char dir, int speedVal) {
  // CRASH SAFETY GOVERNOR: Only active if obstacleGovernorActive is true
  if (obstacleGovernorActive && dir == 'F' && distFront < OBSTACLE_STOP_CM) {
    dir = 'S';
    speedVal = 0;
    Serial.println("[SAFETY] Obstacle detected! Forward blocked.");
  }

  currentMotion = dir;
  speedVal = constrain(speedVal, 0, 255);

  switch (dir) {
    case 'F': // Both Forward (Physical orientation corrected)
      driveMotors(0, 1, speedVal, 0, 1, speedVal);
      Serial.print("[DRIVE] FORWARD Speed: "); Serial.println(speedVal);
      break;
    case 'B': // Both Backward (Physical orientation corrected)
      driveMotors(1, 0, speedVal, 1, 0, speedVal);
      Serial.print("[DRIVE] BACKWARD Speed: "); Serial.println(speedVal);
      break;
    case 'L': // Spin Left (Left Backward 1,0, Right Forward 0,1)
      driveMotors(1, 0, speedVal, 0, 1, speedVal);
      Serial.print("[DRIVE] SPIN LEFT Speed: "); Serial.println(speedVal);
      break;
    case 'R': // Spin Right (Left Forward 0,1, Right Backward 1,0)
      driveMotors(0, 1, speedVal, 1, 0, speedVal);
      Serial.print("[DRIVE] SPIN RIGHT Speed: "); Serial.println(speedVal);
      break;
    case 'S': // Stop
    default:
      driveMotors(0, 0, 0, 0, 0, 0);
      Serial.println("[DRIVE] MOTORS STOPPED");
      break;
  }
}

void executeAutonomousLogic() {
  unsigned long elapsed = millis() - stateStartTime;
  distanceTraveledMeters = (elapsed / 1000.0) * EST_SPEED_MPS;

  // Obstacle Avoidance: If Front < 30 cm -> Pivot Detour
  if (distFront < OBSTACLE_STOP_CM) {
    sendMotorCommand('S', 0);
    delay(200);

    // Turn towards whichever side has more clearance
    if (distLeft > distRight) {
      while (distFront < 45) {
        sendMotorCommand('L', 190);
        delay(150);
        distFront1 = readUltrasonic(TRIG_FRONT1, ECHO_FRONT1);
        distFront2 = readUltrasonic(TRIG_FRONT2, ECHO_FRONT2);
        distFront = min(distFront1, distFront2);
      }
    } else {
      while (distFront < 45) {
        sendMotorCommand('R', 190);
        delay(150);
        distFront1 = readUltrasonic(TRIG_FRONT1, ECHO_FRONT1);
        distFront2 = readUltrasonic(TRIG_FRONT2, ECHO_FRONT2);
        distFront = min(distFront1, distFront2);
      }
    }

    sendMotorCommand('F', 180);
    delay(500);
    return;
  }

  // Segment Progress
  MapSegment seg = missionMap[currentSegment];
  if (distanceTraveledMeters < seg.lengthMeters) {
    sendMotorCommand('F', 180);
  } else {
    // Reached target length
    if (seg.turnAction == 'R') {
      sendMotorCommand('R', 200);
      delay(900);
      currentSegment++;
      stateStartTime = millis();
    } else if (seg.turnAction == 'L') {
      sendMotorCommand('L', 200);
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
  String json = "{";
  json += "\"sector\":" + String((int)currentSector) + ",";
  json += "\"motion\":\"" + String(currentMotion) + "\",";
  
  // 4 Directions (Each direction has 2 sensors + minimum clearance)
  json += "\"sonar\":{";
  json += "\"F\":" + String(distFront) + ",\"F1\":" + String(distFront1) + ",\"F2\":" + String(distFront2) + ",";
  json += "\"R\":" + String(distRight) + ",\"R1\":" + String(distRight1) + ",\"R2\":" + String(distRight2) + ",";
  json += "\"B\":" + String(distRear)  + ",\"B1\":" + String(distRear1)  + ",\"B2\":" + String(distRear2)  + ",";
  json += "\"L\":" + String(distLeft)  + ",\"L1\":" + String(distLeft1)  + ",\"L2\":" + String(distLeft2);
  json += "},";

  json += "\"gas\":{";
  json += "\"mq4\":" + String(valMQ4) + ",\"mq7\":" + String(valMQ7) + ",\"mq2\":" + String(valMQ2) + "},";
  json += "\"dist_m\":" + String(distanceTraveledMeters, 2) + ",";
  json += "\"gov\":" + String(obstacleGovernorActive ? 1 : 0) + ",";
  json += "\"segment\":" + String(currentSegment) + ",";
  json += "\"total_seg\":" + String(totalSegments);
  json += "}";

  Serial1.println(json); // Send to Wemos D1 Wi-Fi bridge
  Serial.println(json);  // Send to USB Serial (Laptop Dashboard direct link & Serial Monitor)
}

void parseSerialCommand(String msg) {
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
  } else if (msg.startsWith("GOV:")) {
    if (msg.endsWith("ON")) obstacleGovernorActive = true;
    else if (msg.endsWith("OFF")) obstacleGovernorActive = false;
    Serial.print("[GOVERNOR] Active: "); Serial.println(obstacleGovernorActive ? "YES" : "NO (Trial Mode)");
  } else if (msg.startsWith("MAP:")) {
    currentSegment = 0;
    stateStartTime = millis();
  }
}
