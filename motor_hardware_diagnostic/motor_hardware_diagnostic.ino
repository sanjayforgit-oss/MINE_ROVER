/*
 * ==============================================================================
 * M.I.N.E.R.S. Rover - BTS7960 / V1326 Motor Hardware Diagnostic Test
 * VERSION 2: BMS-Safe Soft-Start + Detailed Serial Feedback
 * ==============================================================================
 * WIRING TO ARDUINO MEGA (BTS7960 / V1326 Modules):
 *
 * Driver 1 (LEFT SIDE MOTORS):
 *   VCC  -> Arduino 5V
 *   GND  -> Arduino GND  (ALSO connect to 12V Battery B-)
 *   R_EN -> Arduino Pin 30  ** jumper R_EN to L_EN on the driver board **
 *   L_EN -> Arduino Pin 30  ** both EN pins MUST go to same Mega pin **
 *   RPWM -> Arduino Pin D2 (PWM)
 *   LPWM -> Arduino Pin D3 (PWM)
 *   B+   -> 12V Battery Positive (+)
 *   B-   -> 12V Battery Negative (-)
 *   M+   -> Left Motors (+)
 *   M-   -> Left Motors (-)
 *
 * Driver 2 (RIGHT SIDE MOTORS):
 *   VCC  -> Arduino 5V
 *   GND  -> Arduino GND  (ALSO connect to 12V Battery B-)
 *   R_EN -> Arduino Pin 32 ** jumper R_EN to L_EN on the driver board **
 *   L_EN -> Arduino Pin 32 ** both EN pins MUST go to same Mega pin **
 *   RPWM -> Arduino Pin D4 (PWM)
 *   LPWM -> Arduino Pin D5 (PWM)
 *   B+   -> 12V Battery Positive (+)
 *   B-   -> 12V Battery Negative (-)
 *   M+   -> Right Motors (+)
 *   M-   -> Right Motors (-)
 *
 * ==============================================================================
 * KEY NOTE: On each BTS7960 board, R_EN and L_EN are SEPARATE pins.
 * You must bridge them together on the driver board with a short wire/jumper,
 * then connect that to the Mega pin. If only ONE of them is connected,
 * the half-bridge on that side stays disabled and motors won't run.
 * ==============================================================================
 */

const int L_RPWM = 2;   // Left Driver Forward PWM
const int L_LPWM = 3;   // Left Driver Reverse PWM
const int R_RPWM = 4;   // Right Driver Forward PWM
const int R_LPWM = 5;   // Right Driver Reverse PWM
const int L_EN   = 30;  // Left Driver Enable  (BOTH R_EN + L_EN on that board)
const int R_EN   = 32;  // Right Driver Enable (BOTH R_EN + L_EN on that board)

const int TEST_SPEED = 180;  // PWM target (0-255)
const int RAMP_STEP  = 5;    // PWM increment per step
const int RAMP_DELAY = 20;   // ms between steps (BMS-safe slow ramp)

// ---- Helper: Stop everything ----
void stopAll() {
  analogWrite(L_RPWM, 0); analogWrite(L_LPWM, 0);
  analogWrite(R_RPWM, 0); analogWrite(R_LPWM, 0);
}

// ---- Helper: Slowly ramp ONE pin up (protects Li-ion BMS) ----
void rampUp(int pin, int target) {
  for (int spd = 0; spd <= target; spd += RAMP_STEP) {
    analogWrite(pin, spd);
    delay(RAMP_DELAY);
  }
}

void setup() {
  Serial.begin(115200);
  delay(1500);

  Serial.println("=================================================");
  Serial.println(">>> BTS7960/V1326 DIAGNOSTIC v2 (Soft-Start) <<<");
  Serial.println("=================================================");
  Serial.println("PRE-FLIGHT CHECKLIST:");
  Serial.println("  [?] VCC -> Arduino 5V ?");
  Serial.println("  [?] GND -> Arduino GND AND 12V Battery B- ?");
  Serial.println("  [?] Left Driver:  R_EN + L_EN BOTH -> Pin 30 ?");
  Serial.println("  [?] Right Driver: R_EN + L_EN BOTH -> Pin 32 ?");
  Serial.println("  [?] RPWM/LPWM on correct Mega PWM pins ?");
  Serial.println("  [?] B+ to 12V Battery (+), B- to 12V Battery (-) ?");
  Serial.println("  [?] Battery voltage > 11V ?");
  Serial.println("=================================================");
  Serial.println("Starting in 3 seconds...");
  delay(3000);

  pinMode(L_RPWM, OUTPUT); pinMode(L_LPWM, OUTPUT);
  pinMode(R_RPWM, OUTPUT); pinMode(R_LPWM, OUTPUT);
  pinMode(L_EN, OUTPUT);
  pinMode(R_EN, OUTPUT);

  digitalWrite(L_EN, HIGH);
  digitalWrite(R_EN, HIGH);
  Serial.println("[OK] EN pins set HIGH - Both drivers enabled.");

  stopAll();
  Serial.println("[OK] PWM outputs zeroed. Motors stopped.");
  delay(500);
}

void loop() {
  // TEST 1: LEFT FORWARD
  Serial.println("\n[TEST 1] LEFT MOTORS FORWARD - soft ramp...");
  rampUp(L_RPWM, TEST_SPEED);
  analogWrite(L_LPWM, 0);
  Serial.print("[TEST 1] Running PWM="); Serial.println(TEST_SPEED);
  delay(3000);
  stopAll();
  Serial.println("[TEST 1] STOPPED.");
  delay(1500);

  // TEST 2: LEFT REVERSE
  Serial.println("\n[TEST 2] LEFT MOTORS REVERSE - soft ramp...");
  analogWrite(L_RPWM, 0);
  rampUp(L_LPWM, TEST_SPEED);
  Serial.print("[TEST 2] Running PWM="); Serial.println(TEST_SPEED);
  delay(3000);
  stopAll();
  Serial.println("[TEST 2] STOPPED.");
  delay(1500);

  // TEST 3: RIGHT FORWARD
  Serial.println("\n[TEST 3] RIGHT MOTORS FORWARD - soft ramp...");
  rampUp(R_RPWM, TEST_SPEED);
  analogWrite(R_LPWM, 0);
  Serial.print("[TEST 3] Running PWM="); Serial.println(TEST_SPEED);
  delay(3000);
  stopAll();
  Serial.println("[TEST 3] STOPPED.");
  delay(1500);

  // TEST 4: RIGHT REVERSE
  Serial.println("\n[TEST 4] RIGHT MOTORS REVERSE - soft ramp...");
  analogWrite(R_RPWM, 0);
  rampUp(R_LPWM, TEST_SPEED);
  Serial.print("[TEST 4] Running PWM="); Serial.println(TEST_SPEED);
  delay(3000);
  stopAll();
  Serial.println("[TEST 4] STOPPED.");
  delay(1500);

  // TEST 5: BOTH FORWARD
  Serial.println("\n[TEST 5] BOTH MOTORS FORWARD - full rover...");
  rampUp(L_RPWM, TEST_SPEED);
  rampUp(R_RPWM, TEST_SPEED);
  analogWrite(L_LPWM, 0); analogWrite(R_LPWM, 0);
  Serial.print("[TEST 5] Running PWM="); Serial.println(TEST_SPEED);
  delay(3000);
  stopAll();
  Serial.println("[TEST 5] STOPPED.");

  Serial.println("\n=================================================");
  Serial.println("All tests done. Pausing 8 sec, then repeating...");
  Serial.println("=================================================");
  delay(8000);
}
