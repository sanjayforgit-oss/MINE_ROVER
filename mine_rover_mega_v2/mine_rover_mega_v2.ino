/*
 * ==============================================================================
 * AI-POWERED UNDERGROUND MINE SAFETY, MONITORING AND RESCUE SYSTEM - V2
 * Arduino Mega 2560 Firmware (5-Point Ultrasonic Array + Multi-Gas + Motor Control)
 * Problem Statement ID: 26039 (Govt. of Jharkhand)
 * ==============================================================================
 */

// --- 5-POINT ULTRASONIC SENSOR ARRAY ---
// Center Front
const int TRIG_FRONT = 22;
const int ECHO_FRONT = 23;

// Angled Front-Left (-45 deg)
const int TRIG_FRONT_LEFT  = 40;
const int ECHO_FRONT_LEFT  = 41;

// Angled Front-Right (+45 deg)
const int TRIG_FRONT_RIGHT = 42;
const int ECHO_FRONT_RIGHT = 43;

// 90-degree Side Left
const int TRIG_LEFT  = 24;
const int ECHO_LEFT  = 25;

// 90-degree Side Right
const int TRIG_RIGHT = 26;
const int ECHO_RIGHT = 27;

// --- GAS & ENVIRONMENTAL SENSOR PINS ---
const int PIN_MQ4  = A0;  // Methane (CH4)
const int PIN_MQ7  = A1;  // Carbon Monoxide (CO)
const int PIN_MQ2  = A2;  // LPG / Butane / Smoke
const int PIN_RAIN = A3;  // Rain Drop / Subterranean Water Accumulation Sensor
const int PIN_LM35 = A4;  // LM35 Temperature Sensor

// --- MOTOR PINS (DUAL L298N DRIVERS) ---
// Left Motors (Driver 1: M1 Front-Left, M3 Rear-Left)
const int L_IN1 = 30; // M1 Front Left (+)
const int L_IN2 = 31; // M1 Front Left (-)
const int L_IN3 = 32; // M3 Rear Left  (+)
const int L_IN4 = 33; // M3 Rear Left  (-)

// Right Motors (Driver 2: M2 Front-Right, M4 Rear-Right)
const int R_IN1 = 34; // M2 Front Right (+)
const int R_IN2 = 35; // M2 Front Right (-)
const int R_IN3 = 36; // M4 Rear Right  (+)
const int R_IN4 = 37; // M4 Rear Right  (-)

// --- MOTOR SPEED & THRESHOLDS ---
const int ROVER_SPEED = 140;          // Smooth PWM speed (prevents battery brownout)
const int OBSTACLE_STOP_CM = 5;        // Stop if obstacle within 5 cm ahead

// --- TELEMETRY VARIABLES ---
long distFront = 100;
long distFrontLeft = 100;
long distFrontRight = 100;
long distLeft = 100;
long distRight = 100;

int valMQ4 = 0, valMQ7 = 0, valMQ2 = 0, valRain = 1023;
float tempC = 25.0;
char currentMotion = 'S';

unsigned long lastTelemetryTime = 0;
const unsigned long TELEMETRY_INTERVAL = 80; // ~12Hz broadcast

// Function prototypes
long readUltrasonic(int trigPin, int echoPin);
float readLM35(int pin);
void setIndividualMotorsPWM(int m1_f, int m1_r, int m3_f, int m3_r, int m2_f, int m2_r, int m4_f, int m4_r);
void moveForward();
void moveBackward();
void turnLeft();
void turnRight();
void stopMotors();
void executeCommand(char cmd);

void setup() {
  Serial.begin(115200);

  // Initialize Ultrasonic Pins
  pinMode(TRIG_FRONT, OUTPUT);
  pinMode(ECHO_FRONT, INPUT);
  pinMode(TRIG_FRONT_LEFT, OUTPUT);
  pinMode(ECHO_FRONT_LEFT, INPUT);
  pinMode(TRIG_FRONT_RIGHT, OUTPUT);
  pinMode(ECHO_FRONT_RIGHT, INPUT);
  pinMode(TRIG_LEFT,  OUTPUT);
  pinMode(ECHO_LEFT,  INPUT);
  pinMode(TRIG_RIGHT, OUTPUT);
  pinMode(ECHO_RIGHT, INPUT);

  // Ensure all Trigs are LOW initially
  digitalWrite(TRIG_FRONT, LOW);
  digitalWrite(TRIG_FRONT_LEFT, LOW);
  digitalWrite(TRIG_FRONT_RIGHT, LOW);
  digitalWrite(TRIG_LEFT, LOW);
  digitalWrite(TRIG_RIGHT, LOW);

  // Initialize Motor Pins
  pinMode(L_IN1, OUTPUT);
  pinMode(L_IN2, OUTPUT);
  pinMode(L_IN3, OUTPUT);
  pinMode(L_IN4, OUTPUT);
  pinMode(R_IN1, OUTPUT);
  pinMode(R_IN2, OUTPUT);
  pinMode(R_IN3, OUTPUT);
  pinMode(R_IN4, OUTPUT);

  stopMotors();

  delay(400);
  Serial.println(F("{\"status\":\"ROVER_V2_READY\",\"sensors\":5,\"baud\":115200}"));
}

void loop() {
  // 1. Process Incoming Commands from Python GUI
  if (Serial.available() > 0) {
    char cmd = Serial.read();
    if (cmd != '\r' && cmd != '\n') {
      executeCommand(cmd);
    }
  }

  // 2. Periodic Sensor Polling & Telemetry Transmission
  unsigned long now = millis();
  if (now - lastTelemetryTime >= TELEMETRY_INTERVAL) {
    lastTelemetryTime = now;

    // Sequential Ultrasonic Polling with 10ms anti-crosstalk acoustic settling delays
    distFront = readUltrasonic(TRIG_FRONT, ECHO_FRONT);
    delay(10);
    distFrontLeft = readUltrasonic(TRIG_FRONT_LEFT, ECHO_FRONT_LEFT);
    delay(10);
    distFrontRight = readUltrasonic(TRIG_FRONT_RIGHT, ECHO_FRONT_RIGHT);
    delay(10);
    distLeft = readUltrasonic(TRIG_LEFT, ECHO_LEFT);
    delay(10);
    distRight = readUltrasonic(TRIG_RIGHT, ECHO_RIGHT);

    // Read Gas & Environmental Sensors
    valMQ4  = analogRead(PIN_MQ4);
    valMQ7  = analogRead(PIN_MQ7);
    valMQ2  = analogRead(PIN_MQ2); // LPG / Butane / Smoke
    valRain = analogRead(PIN_RAIN); // Rain Drop / Water Level Sensor
    tempC   = readLM35(PIN_LM35);

    // Safety Auto-Braking: If moving forward and front collision imminent (<5cm)
    if (currentMotion == 'F' && (distFront > 0 && distFront <= OBSTACLE_STOP_CM)) {
      stopMotors();
      currentMotion = 'S';
    }

    // Broadcast Real-time JSON Telemetry Packet
    Serial.print(F("{\"front\":"));
    Serial.print(distFront);
    Serial.print(F(",\"front_left\":"));
    Serial.print(distFrontLeft);
    Serial.print(F(",\"front_right\":"));
    Serial.print(distFrontRight);
    Serial.print(F(",\"left\":"));
    Serial.print(distLeft);
    Serial.print(F(",\"right\":"));
    Serial.print(distRight);
    Serial.print(F(",\"mq2\":"));
    Serial.print(valMQ2);
    Serial.print(F(",\"mq4\":"));
    Serial.print(valMQ4);
    Serial.print(F(",\"mq7\":"));
    Serial.print(valMQ7);
    Serial.print(F(",\"rain\":"));
    Serial.print(valRain);
    Serial.print(F(",\"temp\":"));
    Serial.print(tempC, 1);
    Serial.print(F(",\"motion\":\""));
    Serial.print(currentMotion);
    Serial.println(F("\"}"));
  }
}

// Precision Ultrasonic Reader with 18ms echo timeout (~300cm max range)
long readUltrasonic(int trigPin, int echoPin) {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  long duration = pulseIn(echoPin, HIGH, 18000);
  if (duration == 0) return 400; // Out of range or no echo
  
  long cm = duration * 0.0343 / 2;
  if (cm <= 0 || cm > 400) return 400;
  return cm;
}

// Convert LM35 analog reading to Celsius
float readLM35(int pin) {
  int raw = analogRead(pin);
  return raw * (5.0 / 1023.0) * 100.0;
}

// Command Parser supporting WASD, FBLR, and Space/X for Stop
void executeCommand(char cmd) {
  switch (cmd) {
    case 'W':
    case 'w':
    case 'F':
    case 'f':
      if (distFront > 0 && distFront <= OBSTACLE_STOP_CM) {
        stopMotors();
        currentMotion = 'S';
      } else {
        moveForward();
        currentMotion = 'F';
      }
      break;

    case 'S':
    case 's':
    case 'B':
    case 'b':
      moveBackward();
      currentMotion = 'B';
      break;

    case 'A':
    case 'a':
    case 'L':
    case 'l':
      turnLeft();
      currentMotion = 'L';
      break;

    case 'D':
    case 'd':
    case 'R':
    case 'r':
      turnRight();
      currentMotion = 'R';
      break;

    case ' ':
    case 'X':
    case 'x':
    case 'Q':
    case 'q':
    case '0':
      stopMotors();
      currentMotion = 'S';
      break;
  }
}

// Low-power PWM driver: applies ROVER_SPEED (PWM) to active pin, 0 to inactive pin
void setIndividualMotorsPWM(int m1_f, int m1_r, int m3_f, int m3_r, int m2_f, int m2_r, int m4_f, int m4_r) {
  // M1 Front Left
  analogWrite(L_IN1, m1_f ? ROVER_SPEED : 0);
  analogWrite(L_IN2, m1_r ? ROVER_SPEED : 0);
  // M3 Rear Left
  analogWrite(L_IN3, m3_f ? ROVER_SPEED : 0);
  analogWrite(L_IN4, m3_r ? ROVER_SPEED : 0);
  // M2 Front Right
  analogWrite(R_IN1, m2_f ? ROVER_SPEED : 0);
  analogWrite(R_IN2, m2_r ? ROVER_SPEED : 0);
  // M4 Rear Right
  analogWrite(R_IN3, m4_f ? ROVER_SPEED : 0);
  analogWrite(R_IN4, m4_r ? ROVER_SPEED : 0);
}

// Calibrated Motor Polarities:
void moveForward() {
  // M1(fwd), M3(fwd), M2(fwd), M4(fwd)
  setIndividualMotorsPWM(1, 0,   0, 1,   1, 0,   0, 1);
}

void moveBackward() {
  setIndividualMotorsPWM(0, 1,   1, 0,   0, 1,   1, 0);
}

void turnLeft() {
  setIndividualMotorsPWM(0, 1,   1, 0,   1, 0,   0, 1);
}

void turnRight() {
  setIndividualMotorsPWM(1, 0,   0, 1,   0, 1,   1, 0);
}

void stopMotors() {
  setIndividualMotorsPWM(0, 0,   0, 0,   0, 0,   0, 0);
}
