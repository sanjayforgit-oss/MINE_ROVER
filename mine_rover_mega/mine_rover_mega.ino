/*
 * ==============================================================================
 * AI-POWERED UNDERGROUND MINE SAFETY, MONITORING AND RESCUE SYSTEM
 * Arduino Mega 2560 Firmware - Slow Speed PWM & Fixed Right Polarities
 * Problem Statement ID: 26039 (Govt. of Jharkhand)
 * ==============================================================================
 */

// --- ULTRASONIC PINS ---
const int TRIG_FRONT = 22;
const int ECHO_FRONT = 23;
const int TRIG_LEFT  = 24;
const int ECHO_LEFT  = 25;
const int TRIG_RIGHT = 26;
const int ECHO_RIGHT = 27;

// New 180-degree multi-angle sensors
const int TRIG_FRONT_LEFT  = 40;
const int ECHO_FRONT_LEFT  = 41;
const int TRIG_FRONT_RIGHT = 42;
const int ECHO_FRONT_RIGHT = 43;

// --- GAS & ENVIRONMENTAL SENSOR PINS ---
const int PIN_MQ4  = A0;  // Methane
const int PIN_MQ7  = A1;  // Carbon Monoxide
const int PIN_MQ2  = A2;  // Smoke / Flammable Gas
const int PIN_LM35 = A4;  // LM35 Temperature Sensor

// --- MOTOR PINS ---
// Left Motors (Driver 1: M1 Front Left, M3 Rear Left)
const int L_IN1 = 30; // M1 Front Left (+)
const int L_IN2 = 31; // M1 Front Left (-)
const int L_IN3 = 32; // M3 Rear Left  (+)
const int L_IN4 = 33; // M3 Rear Left  (-)

// Right Motors (Driver 2: M2 Front Right, M4 Rear Right)
const int R_IN1 = 34; // M2 Front Right (+)
const int R_IN2 = 35; // M2 Front Right (-)
const int R_IN3 = 36; // M4 Rear Right  (+)
const int R_IN4 = 37; // M4 Rear Right  (-)

// --- PWM SPEED LEVEL (0 - 255) ---
// 140 gives gentle, smooth rotation without huge inrush current on 9V batteries
const int ROVER_SPEED = 140; 

// --- SAFETY THRESHOLDS ---
const int OBSTACLE_THRESHOLD_CM = 5; // Auto-stop if obstacle <= 5cm ahead (range 4-5cm)

// --- VARIABLES ---
long distFront = 100, distLeft = 100, distRight = 100;
long distFrontLeft = 100, distFrontRight = 100;
int valMQ4 = 0, valMQ7 = 0, valMQ2 = 0;
float tempC = 0.0;
char currentMotion = 'S';
unsigned long lastTelemetryTime = 0;
const unsigned long TELEMETRY_INTERVAL = 100;

// Function prototypes
long readUltrasonic(int trigPin, int echoPin);
float readLM35(int pin);
void setIndividualMotorsPWM(int m1_a, int m1_b, int m3_a, int m3_b, int m2_a, int m2_b, int m4_a, int m4_b);
void moveForward();
void moveBackward();
void turnLeft();
void turnRight();
void stopMotors();
void executeCommand(char cmd);

void setup() {
  Serial.begin(115200);

  // Ultrasonic Pins
  pinMode(TRIG_FRONT, OUTPUT);
  pinMode(ECHO_FRONT, INPUT);
  pinMode(TRIG_LEFT,  OUTPUT);
  pinMode(ECHO_LEFT,  INPUT);
  pinMode(TRIG_RIGHT, OUTPUT);
  pinMode(ECHO_RIGHT, INPUT);
  pinMode(TRIG_FRONT_LEFT, OUTPUT);
  pinMode(ECHO_FRONT_LEFT, INPUT);
  pinMode(TRIG_FRONT_RIGHT, OUTPUT);
  pinMode(ECHO_FRONT_RIGHT, INPUT);

  // Motor Pins
  pinMode(L_IN1, OUTPUT);
  pinMode(L_IN2, OUTPUT);
  pinMode(L_IN3, OUTPUT);
  pinMode(L_IN4, OUTPUT);
  pinMode(R_IN1, OUTPUT);
  pinMode(R_IN2, OUTPUT);
  pinMode(R_IN3, OUTPUT);
  pinMode(R_IN4, OUTPUT);

  stopMotors();

  delay(500);
  Serial.println(F("{\"status\":\"ROVER_READY\",\"baud\":115200}"));
}

void loop() {
  if (Serial.available() > 0) {
    char cmd = Serial.read();
    if (cmd != '\r' && cmd != '\n') {
      executeCommand(cmd);
    }
  }

  unsigned long now = millis();
  if (now - lastTelemetryTime >= TELEMETRY_INTERVAL) {
    lastTelemetryTime = now;

    distFront = readUltrasonic(TRIG_FRONT, ECHO_FRONT);
    distLeft  = readUltrasonic(TRIG_LEFT,  ECHO_LEFT);
    distRight = readUltrasonic(TRIG_RIGHT, ECHO_RIGHT);
    distFrontLeft  = readUltrasonic(TRIG_FRONT_LEFT,  ECHO_FRONT_LEFT);
    distFrontRight = readUltrasonic(TRIG_FRONT_RIGHT, ECHO_FRONT_RIGHT);

    valMQ4 = analogRead(PIN_MQ4);
    valMQ7 = analogRead(PIN_MQ7);
    valMQ2 = analogRead(PIN_MQ2);
    tempC  = readLM35(PIN_LM35);

    if (currentMotion == 'F' && distFront > 0 && distFront < OBSTACLE_THRESHOLD_CM) {
      stopMotors();
      currentMotion = 'S';
    }

    Serial.print(F("{\"front\":"));
    Serial.print(distFront);
    Serial.print(F(",\"left\":"));
    Serial.print(distLeft);
    Serial.print(F(",\"right\":"));
    Serial.print(distRight);
    Serial.print(F(",\"front_left\":"));
    Serial.print(distFrontLeft);
    Serial.print(F(",\"front_right\":"));
    Serial.print(distFrontRight);
    Serial.print(F(",\"mq4\":"));
    Serial.print(valMQ4);
    Serial.print(F(",\"mq7\":"));
    Serial.print(valMQ7);
    Serial.print(F(",\"mq2\":"));
    Serial.print(valMQ2);
    Serial.print(F(",\"temp\":"));
    Serial.print(tempC, 1);
    Serial.print(F(",\"motion\":\""));
    Serial.print(currentMotion);
    Serial.println(F("\"}"));
  }
}

long readUltrasonic(int trigPin, int echoPin) {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  long duration = pulseIn(echoPin, HIGH, 25000);
  if (duration == 0) return 400;
  return duration * 0.0343 / 2;
}

float readLM35(int pin) {
  int raw = analogRead(pin);
  return raw * (5.0 / 1023.0) * 100.0;
}

void executeCommand(char cmd) {
  switch (cmd) {
    case 'W':
    case 'w':
    case 'F':
    case 'f':
      if (distFront > 0 && distFront < OBSTACLE_THRESHOLD_CM) {
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

/*
 * Calibrated Motor Directions & Polarity Alignment:
 * - Left side: M1 and M3 matched
 * - Right side: M2 and M4 matched to rotate forward in unison with left side
 */

void moveForward() {
  // M1 (fwd), M3 (fwd), M2 (fwd), M4 (fwd)
  setIndividualMotorsPWM(1, 0,   0, 1,   1, 0,   0, 1);
}

void moveBackward() {
  // All reverse
  setIndividualMotorsPWM(0, 1,   1, 0,   0, 1,   1, 0);
}

void turnLeft() {
  // Left reverse, Right forward
  setIndividualMotorsPWM(0, 1,   1, 0,   1, 0,   0, 1);
}

void turnRight() {
  // Left forward, Right reverse
  setIndividualMotorsPWM(1, 0,   0, 1,   0, 1,   1, 0);
}

void stopMotors() {
  setIndividualMotorsPWM(0, 0,   0, 0,   0, 0,   0, 0);
}
