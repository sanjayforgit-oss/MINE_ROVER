/*
 * ==============================================================================
 * M.I.N.E.R.S. Rover - ESP8266 Motor Sub-Board Firmware
 * Microcontroller: ESP8266 NodeMCU
 * Motor Drivers: 2x L298N (Left Front+Rear in parallel, Right Front+Rear in parallel)
 * Steering: Zero-Radius Skid Steer (Tank Turn)
 * Interface: Hardware UART Serial (115200 Baud) from ESP32 Main Board
 * ==============================================================================
 */

// Left L298N Driver (Controls Left Front + Left Rear Motors)
const int L_IN1 = 5;  // NodeMCU D1 (GPIO 5)
const int L_IN2 = 4;  // NodeMCU D2 (GPIO 4)
const int L_ENA = 14; // NodeMCU D5 (GPIO 14 - PWM Speed)

// Right L298N Driver (Controls Right Front + Right Rear Motors)
const int R_IN3 = 12; // NodeMCU D6 (GPIO 12)
const int R_IN4 = 13; // NodeMCU D7 (GPIO 13)
const int R_ENB = 15; // NodeMCU D8 (GPIO 15 - PWM Speed)

// Watchdog Failsafe
unsigned long lastCommandTime = 0;
const unsigned long WATCHDOG_TIMEOUT = 500; // Auto-stop if no command for 500ms

void setup() {
  Serial.begin(115200);
  
  pinMode(L_IN1, OUTPUT);
  pinMode(L_IN2, OUTPUT);
  pinMode(L_ENA, OUTPUT);
  
  pinMode(R_IN3, OUTPUT);
  pinMode(R_IN4, OUTPUT);
  pinMode(R_ENB, OUTPUT);
  
  stopMotors();
  Serial.println("[ESP8266 Zero-Radius Skid-Steer Driver Ready]");
}

void loop() {
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    if (cmd.length() > 0) {
      parseAndExecuteCommand(cmd);
      lastCommandTime = millis();
    }
  }
  
  // Watchdog Safety Timeout
  if (millis() - lastCommandTime > WATCHDOG_TIMEOUT) {
    stopMotors();
  }
}

void parseAndExecuteCommand(String cmd) {
  // Protocol: M:<DIR>:<SPEED>
  if (!cmd.startsWith("M:")) return;
  
  int firstColon = cmd.indexOf(':');
  int secondColon = cmd.indexOf(':', firstColon + 1);
  if (secondColon == -1) return;
  
  char dir = cmd.charAt(firstColon + 1);
  int speedVal = cmd.substring(secondColon + 1).toInt();
  speedVal = constrain(speedVal, 0, 255);
  
  switch (dir) {
    case 'F': // Forward: Both Left and Right move Forward
      driveMotors(1, 0, speedVal, 1, 0, speedVal);
      break;
    case 'B': // Backward: Both Left and Right move Backward
      driveMotors(0, 1, speedVal, 0, 1, speedVal);
      break;
    case 'L': // Turn Left: Left moves Backward, Right moves Forward (Zero Radius Spin)
      driveMotors(0, 1, speedVal, 1, 0, speedVal);
      break;
    case 'R': // Turn Right: Left moves Forward, Right moves Backward (Zero Radius Spin)
      driveMotors(1, 0, speedVal, 0, 1, speedVal);
      break;
    case 'S': // Stop
    default:
      stopMotors();
      break;
  }
}

void driveMotors(int l_in1, int l_in2, int l_pwm, int r_in3, int r_in4, int r_pwm) {
  digitalWrite(L_IN1, l_in1 ? HIGH : LOW);
  digitalWrite(L_IN2, l_in2 ? HIGH : LOW);
  analogWrite(L_ENA, l_pwm);
  
  digitalWrite(R_IN3, r_in3 ? HIGH : LOW);
  digitalWrite(R_IN4, r_in4 ? HIGH : LOW);
  analogWrite(R_ENB, r_pwm);
}

void stopMotors() {
  digitalWrite(L_IN1, LOW);
  digitalWrite(L_IN2, LOW);
  analogWrite(L_ENA, 0);
  
  digitalWrite(R_IN3, LOW);
  digitalWrite(R_IN4, LOW);
  analogWrite(R_ENB, 0);
}
