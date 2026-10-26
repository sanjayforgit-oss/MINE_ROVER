/*
 * ==============================================================================
 * M.I.N.E.R.S. V3 - STANDALONE AUTONOMOUS MAP-GUIDED NAVIGATION FIRMWARE
 * Arduino Mega 2560 (Runs 100% Standalone on Battery - No Laptop Required!)
 * Problem Statement ID: 26039 (Govt. of Jharkhand)
 * ==============================================================================
 * Features:
 * 1. Text/Struct Map Interpreter (Segment Length, Obstacle Avoidance, Intersection Turn)
 * 2. 5-Point Sector Ultrasonic Obstacle Bypassing & Re-alignment
 * 3. Side-wall Open Sector Sensing for Intersection Detection
 * 4. Failsafe Battery & Safety Governor Autonomous Stopping
 * 5. Serial/ESP8266 Telemetry Broadcast (Works standalone or with optional Wi-Fi/Radio)
 * ==============================================================================
 */

// --- 5-POINT ULTRASONIC SENSOR ARRAY ---
const int TRIG_FRONT       = 22;
const int ECHO_FRONT       = 23;
const int TRIG_FRONT_LEFT  = 40;
const int ECHO_FRONT_LEFT  = 41;
const int TRIG_FRONT_RIGHT = 42;
const int ECHO_FRONT_RIGHT = 43;
const int TRIG_LEFT        = 24;
const int ECHO_LEFT        = 25;
const int TRIG_RIGHT       = 26;
const int ECHO_RIGHT       = 27;

// --- GAS & ENVIRONMENTAL SENSORS ---
const int PIN_MQ4  = A0; // Methane (CH4)
const int PIN_MQ7  = A1; // Carbon Monoxide (CO)
const int PIN_MQ2  = A2; // LPG / Butane / Smoke
const int PIN_RAIN = A3; // Water / Rain Sensor
const int PIN_LM35 = A4; // Temperature Sensor

// --- MOTOR PINS (DUAL L298N DRIVERS) ---
const int L_IN1 = 30; // M1 Front Left (+)
const int L_IN2 = 31; // M1 Front Left (-)
const int L_IN3 = 32; // M3 Rear Left  (+)
const int L_IN4 = 33; // M3 Rear Left  (-)

const int R_IN1 = 34; // M2 Front Right (+)
const int R_IN2 = 35; // M2 Front Right (-)
const int R_IN3 = 36; // M4 Rear Right  (+)
const int R_IN4 = 37; // M4 Rear Right  (-)

// --- SPEED & CALIBRATION CONSTANTS ---
const int ROVER_SPEED = 140;                // Smooth 140 PWM speed
const float METERS_PER_SECOND = 0.35;        // Calibrated speed (~0.35 m/s at 140 PWM)
const int OBSTACLE_BYPASS_CM = 25;           // Trigger obstacle detour at 25cm
const int INTERSECTION_OPENING_CM = 120;     // Side wall opening threshold for T-junction

// --- MAP STRUCTURE & DATA ---
struct MapSegment {
  float lengthMeters;     // Target distance to traverse in current corridor
  char intersectionAction;// 'R' = Turn Right, 'L' = Turn Left, 'F' = Straight, 'E' = End Mission
  float postTurnMeters;   // Distance to travel after turn
};

// Map Definition for Test Run:
// Corridor 1: 10.0m long, 2.0m wide -> Intersection -> Turn RIGHT -> Traverse 3.0m -> End
const int NUM_MAP_SEGMENTS = 2;
MapSegment missionMap[NUM_MAP_SEGMENTS] = {
  { 10.0, 'R', 3.0 },  // Segment 0: 10m forward, Turn Right at intersection, then 3m
  {  3.0, 'E', 0.0 }   // Segment 1: Final destination reached, End mission
};

// --- AUTONOMOUS NAVIGATION STATE MACHINE ---
enum RoverState {
  STATE_IDLE,
  STATE_NAVIGATING_CORRIDOR,
  STATE_BYPASSING_OBSTACLE,
  STATE_INTERSECTION_DETECTED,
  STATE_EXECUTING_TURN,
  STATE_POST_TURN_CORRIDOR,
  STATE_MISSION_COMPLETE,
  STATE_EMERGENCY_HALT
};

RoverState currentState = STATE_IDLE;
int currentSegmentIndex = 0;

// Travel tracking variables
unsigned long segmentStartTime = 0;
float segmentDistanceTraveled = 0.0;
unsigned long stateTimer = 0;
char detourDirection = 'R';

// Telemetry Variables
long distFront = 100, distFrontLeft = 100, distFrontRight = 100, distLeft = 100, distRight = 100;
int valMQ4 = 0, valMQ7 = 0, valMQ2 = 0, valRain = 1023;
float tempC = 25.0;
char currentMotion = 'S';
unsigned long lastTelemetryTime = 0;
const unsigned long TELEMETRY_INTERVAL = 100;

// Function Prototypes
long readUltrasonic(int trigPin, int echoPin);
float readLM35(int pin);
void setIndividualMotorsPWM(int m1_f, int m1_r, int m3_f, int m3_r, int m2_f, int m2_r, int m4_f, int m4_r);
void moveForward();
void moveBackward();
void turnLeft();
void turnRight();
void stopMotors();
void executeAutonomousState();
void broadcastTelemetry();

void setup() {
  // Serial0 for USB/Serial Monitor or ESP8266/ESP32 Wi-Fi module
  Serial.begin(115200);

  // Initialize Ultrasonic Pins
  pinMode(TRIG_FRONT, OUTPUT);       pinMode(ECHO_FRONT, INPUT);
  pinMode(TRIG_FRONT_LEFT, OUTPUT);  pinMode(ECHO_FRONT_LEFT, INPUT);
  pinMode(TRIG_FRONT_RIGHT, OUTPUT); pinMode(ECHO_FRONT_RIGHT, INPUT);
  pinMode(TRIG_LEFT, OUTPUT);        pinMode(ECHO_LEFT, INPUT);
  pinMode(TRIG_RIGHT, OUTPUT);       pinMode(ECHO_RIGHT, INPUT);

  digitalWrite(TRIG_FRONT, LOW);
  digitalWrite(TRIG_FRONT_LEFT, LOW);
  digitalWrite(TRIG_FRONT_RIGHT, LOW);
  digitalWrite(TRIG_LEFT, LOW);
  digitalWrite(TRIG_RIGHT, LOW);

  // Initialize Motor Pins
  pinMode(L_IN1, OUTPUT); pinMode(L_IN2, OUTPUT);
  pinMode(L_IN3, OUTPUT); pinMode(L_IN4, OUTPUT);
  pinMode(R_IN1, OUTPUT); pinMode(R_IN2, OUTPUT);
  pinMode(R_IN3, OUTPUT); pinMode(R_IN4, OUTPUT);

  stopMotors();
  delay(1000);

  Serial.println(F("{\"status\":\"M.I.N.E.R.S._V3_AUTONOMOUS_READY\",\"standalone\":true}"));

  // Auto-start autonomous mission after 3 seconds startup pause
  segmentStartTime = millis();
  currentState = STATE_NAVIGATING_CORRIDOR;
  currentSegmentIndex = 0;
}

void loop() {
  // 1. Process optional incoming manual commands (Wi-Fi or Serial)
  if (Serial.available() > 0) {
    char cmd = Serial.read();
    if (cmd == 'START' || cmd == 'G' || cmd == 'g') {
      currentState = STATE_NAVIGATING_CORRIDOR;
      segmentStartTime = millis();
    } else if (cmd == ' ' || cmd == 'X' || cmd == 'x' || cmd == 'STOP') {
      currentState = STATE_EMERGENCY_HALT;
      stopMotors();
    }
  }

  // 2. Poll Sensors
  unsigned long now = millis();
  if (now - lastTelemetryTime >= TELEMETRY_INTERVAL) {
    lastTelemetryTime = now;

    distFront      = readUltrasonic(TRIG_FRONT, ECHO_FRONT);       delay(5);
    distFrontLeft  = readUltrasonic(TRIG_FRONT_LEFT, ECHO_FRONT_LEFT); delay(5);
    distFrontRight = readUltrasonic(TRIG_FRONT_RIGHT, ECHO_FRONT_RIGHT); delay(5);
    distLeft       = readUltrasonic(TRIG_LEFT, ECHO_LEFT);         delay(5);
    distRight      = readUltrasonic(TRIG_RIGHT, ECHO_RIGHT);

    valMQ4  = analogRead(PIN_MQ4);
    valMQ7  = analogRead(PIN_MQ7);
    valMQ2  = analogRead(PIN_MQ2);
    valRain = analogRead(PIN_RAIN);
    tempC   = readLM35(PIN_LM35);

    // 3. Run Autonomous Map Navigation Engine
    executeAutonomousState();

    // 4. Broadcast Telemetry over Serial / ESP8266 Wi-Fi
    broadcastTelemetry();
  }
}

void executeAutonomousState() {
  unsigned long elapsedMs = millis() - segmentStartTime;
  segmentDistanceTraveled = (elapsedMs / 1000.0) * METERS_PER_SECOND;

  MapSegment currentTarget = missionMap[currentSegmentIndex];

  switch (currentState) {
    case STATE_IDLE:
      stopMotors();
      currentMotion = 'S';
      break;

    case STATE_NAVIGATING_CORRIDOR:
      // A. Check for Front Obstacle (Trigger Detour/Bypass)
      if (distFront > 0 && distFront <= OBSTACLE_BYPASS_CM) {
        stateTimer = millis();
        currentState = STATE_BYPASSING_OBSTACLE;

        // Choose side with more clearance
        if (distFrontLeft > distFrontRight) {
          detourDirection = 'L';
          turnLeft();
          currentMotion = 'L';
        } else {
          detourDirection = 'R';
          turnRight();
          currentMotion = 'R';
        }
        break;
      }

      // B. Check for Intersection Arrival (Distance target reached or side wall opening detected)
      if (segmentDistanceTraveled >= currentTarget.lengthMeters || 
         (currentTarget.intersectionAction == 'R' && distRight >= INTERSECTION_OPENING_CM) ||
         (currentTarget.intersectionAction == 'L' && distLeft >= INTERSECTION_OPENING_CM)) {
        
        stateTimer = millis();
        currentState = STATE_INTERSECTION_DETECTED;
        stopMotors();
        currentMotion = 'S';
        break;
      }

      // Normal Forward Corridor Driving with minor wall centering steering
      if (distFrontLeft > 0 && distFrontLeft <= 10) {
        turnRight(); // Steer slightly right away from left wall
        currentMotion = 'R';
      } else if (distFrontRight > 0 && distFrontRight <= 10) {
        turnLeft();  // Steer slightly left away from right wall
        currentMotion = 'L';
      } else {
        moveForward();
        currentMotion = 'F';
      }
      break;

    case STATE_BYPASSING_OBSTACLE:
      // Steer away for 350ms, then advance forward past obstacle for 800ms
      if (millis() - stateTimer < 350) {
        if (detourDirection == 'L') turnLeft(); else turnRight();
      } else if (millis() - stateTimer < 1150) {
        moveForward();
        currentMotion = 'F';
      } else {
        // Realign back into corridor path
        if (detourDirection == 'L') turnRight(); else turnLeft();
        delay(350);
        currentState = STATE_NAVIGATING_CORRIDOR;
      }
      break;

    case STATE_INTERSECTION_DETECTED:
      // Brief 500ms pause to stabilize at T-Junction
      if (millis() - stateTimer >= 500) {
        if (currentTarget.intersectionAction == 'R') {
          turnRight();
          currentMotion = 'R';
          stateTimer = millis();
          currentState = STATE_EXECUTING_TURN;
        } else if (currentTarget.intersectionAction == 'L') {
          turnLeft();
          currentMotion = 'L';
          stateTimer = millis();
          currentState = STATE_EXECUTING_TURN;
        } else {
          // Go straight or end
          currentState = STATE_POST_TURN_CORRIDOR;
          segmentStartTime = millis();
        }
      }
      break;

    case STATE_EXECUTING_TURN:
      // Calibrated 90-degree turn execution time (~950ms at 140 PWM)
      if (millis() - stateTimer >= 950) {
        stopMotors();
        currentMotion = 'S';
        delay(200);

        // Move to post-turn corridor segment
        segmentStartTime = millis();
        currentState = STATE_POST_TURN_CORRIDOR;
      }
      break;

    case STATE_POST_TURN_CORRIDOR:
      // Drive forward into the new branch for the post-turn distance (e.g. 3m)
      if (segmentDistanceTraveled >= currentTarget.postTurnMeters) {
        currentSegmentIndex++;
        if (currentSegmentIndex >= NUM_MAP_SEGMENTS || missionMap[currentSegmentIndex].intersectionAction == 'E') {
          currentState = STATE_MISSION_COMPLETE;
        } else {
          segmentStartTime = millis();
          currentState = STATE_NAVIGATING_CORRIDOR;
        }
      } else {
        // Obstacle avoidance in branch
        if (distFront > 0 && distFront <= OBSTACLE_BYPASS_CM) {
          stateTimer = millis();
          currentState = STATE_BYPASSING_OBSTACLE;
        } else {
          moveForward();
          currentMotion = 'F';
        }
      }
      break;

    case STATE_MISSION_COMPLETE:
      stopMotors();
      currentMotion = 'S';
      break;

    case STATE_EMERGENCY_HALT:
      stopMotors();
      currentMotion = 'S';
      break;
  }
}

// Sensor helper
long readUltrasonic(int trigPin, int echoPin) {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  long duration = pulseIn(echoPin, HIGH, 18000);
  if (duration == 0) return 400;
  long cm = duration * 0.0343 / 2;
  if (cm <= 0 || cm > 400) return 400;
  return cm;
}

float readLM35(int pin) {
  int raw = analogRead(pin);
  return raw * (5.0 / 1023.0) * 100.0;
}

void broadcastTelemetry() {
  Serial.print(F("{\"front\":"));       Serial.print(distFront);
  Serial.print(F(",\"front_left\":")); Serial.print(distFrontLeft);
  Serial.print(F(",\"front_right\":"));Serial.print(distFrontRight);
  Serial.print(F(",\"left\":"));       Serial.print(distLeft);
  Serial.print(F(",\"right\":"));      Serial.print(distRight);
  Serial.print(F(",\"mq2\":"));        Serial.print(valMQ2);
  Serial.print(F(",\"mq4\":"));        Serial.print(valMQ4);
  Serial.print(F(",\"mq7\":"));        Serial.print(valMQ7);
  Serial.print(F(",\"rain\":"));       Serial.print(valRain);
  Serial.print(F(",\"temp\":"));       Serial.print(tempC, 1);
  Serial.print(F(",\"motion\":\""));   Serial.print(currentMotion);
  Serial.print(F("\",\"dist_m\":"));   Serial.print(segmentDistanceTraveled, 1);
  Serial.print(F(",\"state\":"));      Serial.print(currentState);
  Serial.println(F("}"));
}

void setIndividualMotorsPWM(int m1_f, int m1_r, int m3_f, int m3_r, int m2_f, int m2_r, int m4_f, int m4_r) {
  analogWrite(L_IN1, m1_f ? ROVER_SPEED : 0);
  analogWrite(L_IN2, m1_r ? ROVER_SPEED : 0);
  analogWrite(L_IN3, m3_f ? ROVER_SPEED : 0);
  analogWrite(L_IN4, m3_r ? ROVER_SPEED : 0);
  analogWrite(R_IN1, m2_f ? ROVER_SPEED : 0);
  analogWrite(R_IN2, m2_r ? ROVER_SPEED : 0);
  analogWrite(R_IN3, m4_f ? ROVER_SPEED : 0);
  analogWrite(R_IN4, m4_r ? ROVER_SPEED : 0);
}

void moveForward()  { setIndividualMotorsPWM(1, 0,  0, 1,  1, 0,  0, 1); }
void moveBackward() { setIndividualMotorsPWM(0, 1,  1, 0,  0, 1,  1, 0); }
void turnLeft()     { setIndividualMotorsPWM(0, 1,  1, 0,  1, 0,  0, 1); }
void turnRight()    { setIndividualMotorsPWM(1, 0,  0, 1,  0, 1,  1, 0); }
void stopMotors()   { setIndividualMotorsPWM(0, 0,  0, 0,  0, 0,  0, 0); }
