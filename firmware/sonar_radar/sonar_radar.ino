/*
 * Ultrasonic radar firmware (Arduino UNO R4 WiFi)
 *
 * Re-implementation of the original firmware, written to match the serial
 * protocol used by the Python host program.
 *
 * Serial: 115200 baud, newline-terminated text.
 *
 * Host -> Arduino commands:
 *   start          begin sweeping 0..180..0 and reporting measurements
 *   stop           pause the sweep (servo holds its position)
 *   continue       resume the sweep from the current angle
 *   rotate <deg>   point the sensor at <deg> (0-180) and hold there
 *
 * Arduino -> Host, one line per measurement:
 *   Angle: 90°, Distance: 23 cm
 *
 * Hardware: HC-SR04-style ultrasonic sensor on an SG90 servo.
 * Wiring (assumed; change the pin constants below to match your build):
 *   HC-SR04 TRIG -> D9, ECHO -> D10
 *   Servo signal -> D6
 */

#include <Servo.h>

// ---- pins (assumed; adjust to your wiring) ----
const uint8_t TRIG_PIN  = 9;
const uint8_t ECHO_PIN  = 10;
const uint8_t SERVO_PIN = 6;

// ---- sweep settings ----
const int ANGLE_MIN = 0;
const int ANGLE_MAX = 180;
const int ANGLE_STEP = 1;                    // degrees per step
const unsigned long STEP_INTERVAL_MS = 30;   // time between steps
const unsigned long SERVO_SETTLE_MS = 15;    // wait after moving before measuring
const int MAX_DISTANCE_CM = 100;             // matches r_max on the host
// echo timeout: round trip for MAX_DISTANCE_CM at ~58 us/cm, with margin
const unsigned long ECHO_TIMEOUT_US = (unsigned long)MAX_DISTANCE_CM * 58UL * 2UL;

enum State { IDLE, SCANNING, PAUSED };

Servo servo;
State state = IDLE;
int angle = ANGLE_MIN;
int direction = 1;                 // +1 sweeping up, -1 sweeping down
unsigned long lastStepMs = 0;
String rxLine;

void setup() {
  Serial.begin(115200);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  digitalWrite(TRIG_PIN, LOW);
  servo.attach(SERVO_PIN);
  servo.write(angle);
  rxLine.reserve(32);
}

void loop() {
  readCommands();

  if (state == SCANNING && millis() - lastStepMs >= STEP_INTERVAL_MS) {
    lastStepMs = millis();
    stepAndMeasure();
  }
}

// Move one step, take a reading, report it.
void stepAndMeasure() {
  servo.write(angle);
  delay(SERVO_SETTLE_MS);

  int distance = measureCm();
  if (distance > 0) {              // skip readings with no echo / out of range
    Serial.print("Angle: ");
    Serial.print(angle);
    Serial.print("\xC2\xB0, Distance: ");   // UTF-8 degree sign
    Serial.print(distance);
    Serial.println(" cm");
  }

  angle += direction * ANGLE_STEP;
  if (angle >= ANGLE_MAX) { angle = ANGLE_MAX; direction = -1; }
  if (angle <= ANGLE_MIN) { angle = ANGLE_MIN; direction = 1; }
}

// Returns distance in cm, or 0 if nothing was detected within range.
int measureCm() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  unsigned long duration = pulseIn(ECHO_PIN, HIGH, ECHO_TIMEOUT_US);
  if (duration == 0) return 0;

  int cm = (int)(duration / 58UL);
  if (cm <= 0 || cm > MAX_DISTANCE_CM) return 0;
  return cm;
}

// Collect characters until newline, then handle the line.
void readCommands() {
  while (Serial.available() > 0) {
    char c = (char)Serial.read();
    if (c == '\n' || c == '\r') {
      if (rxLine.length() > 0) {
        handleCommand(rxLine);
        rxLine = "";
      }
    } else if (rxLine.length() < 31) {
      rxLine += c;
    }
  }
}

void handleCommand(String cmd) {
  cmd.trim();

  if (cmd == "start") {
    angle = ANGLE_MIN;
    direction = 1;
    state = SCANNING;
  } else if (cmd == "stop") {
    if (state == SCANNING) state = PAUSED;
  } else if (cmd == "continue") {
    if (state == PAUSED) state = SCANNING;
  } else if (cmd.startsWith("rotate")) {
    int target = constrain(cmd.substring(6).toInt(), ANGLE_MIN, ANGLE_MAX);
    angle = target;
    servo.write(angle);
    state = PAUSED;                // hold on the target until "continue"
  }
}
