#include <Arduino.h>
#include <SPI.h>
#include <SimpleFOC.h>
#include <SimpleFOCDrivers.h>
#include "drivers/drv8316/drv8316.h"
#include "current_sense/hardware_specific/samd/samd51_sensing.h"
#include "ScopeData.h"

#define MODE_SENSOR_TEST 0
#define MODE_OPEN_LOOP 1
#define MODE_CLOSED_LOOP 2
#define MODE_ENCODER_RAW 3
#define MODE_SPI_LOOPBACK 4
#define MODE_PIN_LOOPBACK 5
#define MODE_DIAG 6
#define MODE_DRV_TEST 7
#define MODE_SCOPE 8
#define MODE_SENSING_SCOPE 9

#define TEST_MODE MODE_SENSING_SCOPE
#define USE_6PWM 0

#define PIN_PWM_A 10
#define PIN_PWM_B 11
#define PIN_PWM_C 12
#define PIN_INL_A 1
#define PIN_INL_B 0
#define PIN_INL_C 13
#define PIN_DRV_CS 9
#define PIN_N_SLEEP 6
#define PIN_ENC_CS 5

#define ENCODER_AS5047P 0
#define ENCODER_AS5048A 1

#define ENCODER_TYPE ENCODER_AS5048A

#define POLE_PAIRS 7
#define SUPPLY_VOLTAGE 12.0f
#define VOLTAGE_LIMIT 1.5f
#define TARGET_VELOCITY 5.0f
#define MOTOR_RUN_TIMEOUT_MS 30000

BLDCMotor motor(POLE_PAIRS);
LowsideCurrentSense current_sense(150.0f, A2, A3, _NC);
uint32_t motor_start_ms = 0;
#if USE_6PWM
DRV8316Driver6PWM driver(PIN_PWM_A, PIN_INL_A, PIN_PWM_B, PIN_INL_B, PIN_PWM_C, PIN_INL_C, PIN_DRV_CS);
#else
DRV8316Driver3PWM driver(PIN_PWM_A, PIN_PWM_B, PIN_PWM_C, PIN_DRV_CS);
#endif

#if ENCODER_TYPE == ENCODER_AS5047P
MagneticSensorSPI sensor = MagneticSensorSPI(AS5047_SPI, PIN_ENC_CS, 1000000);
#else
MagneticSensorSPI sensor = MagneticSensorSPI(AS5048_SPI, PIN_ENC_CS, 1000000);
#endif

uint16_t readEncoderRaw(uint16_t command, uint8_t mode) {
  SPI.beginTransaction(SPISettings(1000000, MSBFIRST, mode));
  digitalWrite(PIN_ENC_CS, LOW);
  SPI.transfer16(command);
  digitalWrite(PIN_ENC_CS, HIGH);
  delayMicroseconds(1);
  digitalWrite(PIN_ENC_CS, LOW);
  uint16_t response = SPI.transfer16(0x0000);
  digitalWrite(PIN_ENC_CS, HIGH);
  SPI.endTransaction();
  return response;
}

uint16_t readSpiLoopback(uint16_t data, uint8_t mode) {
  SPI.beginTransaction(SPISettings(1000000, MSBFIRST, mode));
  digitalWrite(PIN_ENC_CS, LOW);
  uint16_t response = SPI.transfer16(data);
  digitalWrite(PIN_ENC_CS, HIGH);
  SPI.endTransaction();
  return response;
}

void testDRV() {
  Serial.print("PWM mode: ");
  Serial.println((int)driver.getPWMMode());
  Serial.print("registers locked: ");
  Serial.println(driver.isRegistersLocked());
  DRV8316Status status = driver.getStatus();
  Serial.print("fault: ");
  Serial.println(status.isFault());
  Serial.print("SPI error: ");
  Serial.println(status.isSPIError());
  DRV8316_PWM100DUTY original = driver.getPWM100Frequency();
  Serial.print("PWM100 original: ");
  Serial.println((int)original);
  driver.setPWM100Frequency(original == DRV8316_PWM100DUTY::FREQ_20KHz ? DRV8316_PWM100DUTY::FREQ_40KHz : DRV8316_PWM100DUTY::FREQ_20KHz);
  delayMicroseconds(5);
  DRV8316_PWM100DUTY changed = driver.getPWM100Frequency();
  Serial.print("PWM100 readback: ");
  Serial.println((int)changed);
  driver.setPWM100Frequency(original);
  delayMicroseconds(5);
  Serial.print("PWM100 restored: ");
  Serial.println((int)driver.getPWM100Frequency());
  if (status.isFault()) driver.clearFault();
}

static uint64_t oldestTimestamp(const uint64_t* timestamps, uint8_t count) {
  uint64_t base = 0;
  for (uint8_t i = 0; i < count; i++) {
    if (timestamps[i] != 0 && (base == 0 || timestamps[i] < base)) base = timestamps[i];
  }
  return base;
}

static uint16_t timestampOffsetUs(uint64_t timestamp_us, uint64_t base_us) {
  if (timestamp_us < base_us) return 0;
  uint64_t offset_us = timestamp_us - base_us;
  return offset_us > 0xFFFF ? 0xFFFF : (uint16_t)offset_us;
}

void sendScopeData() {
  ScopeData data = {};
#if TEST_MODE == MODE_SENSING_SCOPE
  PhaseCurrent_s currents = current_sense.getPhaseCurrents();
  uint64_t timestamps[7] = {
    _getSAMD51SensingTimestamp(A2),
    _getSAMD51SensingTimestamp(A3),
    0,
    _getSAMD51SensingTimestamp(A0),
    _getSAMD51SensingTimestamp(A1),
    _getSAMD51SensingTimestamp(A4),
    _getSAMD51SensingTimestamp(A5)
  };
  data.ia = currents.a;
  data.ib = currents.b;
  data.ic = -(currents.a + currents.b);

  data.va = _readSAMD51VoltageSense(A0);
  timestamps[3] = _getSAMD51SensingTimestamp(A0);
  data.vb = _readSAMD51VoltageSense(A1);
  timestamps[4] = _getSAMD51SensingTimestamp(A1);
  data.vc = _readSAMD51VoltageSense(A4);
  timestamps[5] = _getSAMD51SensingTimestamp(A4);
  data.vm = _readSAMD51VMSense(A5);
  timestamps[6] = _getSAMD51SensingTimestamp(A5);

  uint64_t base_us = oldestTimestamp(timestamps, 7);
  data.base_timestamp_us = base_us;
  data.ia_offset_us = timestampOffsetUs(timestamps[0], base_us);
  data.ib_offset_us = timestampOffsetUs(timestamps[1], base_us);
  data.ic_offset_us = timestampOffsetUs(timestamps[0], base_us);
  data.va_offset_us = timestampOffsetUs(timestamps[3], base_us);
  data.vb_offset_us = timestampOffsetUs(timestamps[4], base_us);
  data.vc_offset_us = timestampOffsetUs(timestamps[5], base_us);
  data.vm_offset_us = timestampOffsetUs(timestamps[6], base_us);
#endif
  Serial.write("ScopeData\n", 10);
  Serial.write((uint8_t*)&data, sizeof(data));
}

void setup() {
  Serial.begin(115200);
  delay(3000);
  analogRead(A3);

  pinMode(PIN_N_SLEEP, OUTPUT);
  digitalWrite(PIN_N_SLEEP, LOW);
  pinMode(PIN_DRV_CS, OUTPUT);
  digitalWrite(PIN_DRV_CS, HIGH);
  pinMode(PIN_PWM_A, OUTPUT);
  pinMode(PIN_PWM_B, OUTPUT);
  pinMode(PIN_PWM_C, OUTPUT);
  digitalWrite(PIN_PWM_A, LOW);
  digitalWrite(PIN_PWM_B, LOW);
  digitalWrite(PIN_PWM_C, LOW);

  pinMode(PIN_INL_A, OUTPUT);
  pinMode(PIN_INL_B, OUTPUT);
  pinMode(PIN_INL_C, OUTPUT);
#if USE_6PWM
  digitalWrite(PIN_INL_A, LOW);
  digitalWrite(PIN_INL_B, LOW);
  digitalWrite(PIN_INL_C, LOW);
#else
  digitalWrite(PIN_INL_A, HIGH);
  digitalWrite(PIN_INL_B, HIGH);
  digitalWrite(PIN_INL_C, HIGH);
#endif

#if TEST_MODE == MODE_SPI_LOOPBACK || TEST_MODE == MODE_PIN_LOOPBACK || TEST_MODE == MODE_DIAG || TEST_MODE == MODE_DRV_TEST
  SPI.begin();
  pinMode(PIN_ENC_CS, OUTPUT);
  digitalWrite(PIN_ENC_CS, HIGH);
#else
  sensor.init(&SPI);
#endif

#if TEST_MODE == MODE_DRV_TEST
  digitalWrite(PIN_N_SLEEP, HIGH);
  delay(10);
  driver.voltage_power_supply = SUPPLY_VOLTAGE;
  driver.voltage_limit = VOLTAGE_LIMIT;
  driver.init(&SPI);
  testDRV();
#elif TEST_MODE != MODE_SENSOR_TEST && TEST_MODE != MODE_ENCODER_RAW && TEST_MODE != MODE_SPI_LOOPBACK && TEST_MODE != MODE_PIN_LOOPBACK && TEST_MODE != MODE_DIAG
  digitalWrite(PIN_N_SLEEP, HIGH);
  delay(10);

  driver.voltage_power_supply = SUPPLY_VOLTAGE;
  driver.voltage_limit = VOLTAGE_LIMIT;
  driver.init(&SPI);
  driver.setCurrentSenseGain(DRV8316_CSAGain::Gain_0V15);

#if TEST_MODE == MODE_SENSING_SCOPE
  current_sense.linkDriver(&driver);
  _configureSAMD51VoltageSense(A0, A1, A4);
  _configureSAMD51VMSense(A5);
  Serial.print("current sense init: ");
  Serial.println(current_sense.init());
#endif

  motor.linkDriver(&driver);
  motor.linkSensor(&sensor);
  motor.voltage_limit = VOLTAGE_LIMIT;
  motor.voltage_sensor_align = VOLTAGE_LIMIT;
  motor.velocity_limit = 20.0f;
#if TEST_MODE == MODE_SENSING_SCOPE
  motor.linkCurrentSense(&current_sense);
#endif

  Serial.print("driver initialized: ");
  Serial.println(driver.initialized);

#if TEST_MODE == MODE_OPEN_LOOP || TEST_MODE == MODE_SCOPE || TEST_MODE == MODE_SENSING_SCOPE
  motor.controller = MotionControlType::velocity_openloop;
  Serial.print("motor init: ");
  Serial.println(motor.init());
  motor_start_ms = millis();
#else
  motor.controller = MotionControlType::velocity;
  motor.init();
  Serial.print("initFOC ");
  Serial.println(motor.initFOC());
#endif
#endif

  Serial.println("ready");
}

void loop() {
#if TEST_MODE == MODE_SENSOR_TEST
  sensor.update();
  Serial.print(sensor.getAngle(), 4);
  Serial.print('\t');
  Serial.println(sensor.getVelocity(), 4);
  delay(100);
#elif TEST_MODE == MODE_ENCODER_RAW
  for (uint8_t m = 0; m < 4; m++) {
    Serial.print("m");
    Serial.print(m);
    Serial.print(" FFFF=");
    Serial.print(readEncoderRaw(0xFFFF, m), HEX);
    Serial.print(" 0000=");
    Serial.print(readEncoderRaw(0x0000, m), HEX);
    Serial.print(" 4000=");
    Serial.println(readEncoderRaw(0x4000, m), HEX);
  }
  Serial.println("---");
  delay(500);
#elif TEST_MODE == MODE_SPI_LOOPBACK
  for (uint8_t m = 0; m < 4; m++) {
    Serial.print("m");
    Serial.print(m);
    Serial.print(" A5A5=");
    Serial.print(readSpiLoopback(0xA5A5, m), HEX);
    Serial.print(" 5A5A=");
    Serial.print(readSpiLoopback(0x5A5A, m), HEX);
    SPI.beginTransaction(SPISettings(1000000, MSBFIRST, m));
    digitalWrite(PIN_ENC_CS, LOW);
    uint8_t r8 = SPI.transfer(0xA5);
    digitalWrite(PIN_ENC_CS, HIGH);
    SPI.endTransaction();
    Serial.print(" 8=");
    Serial.println(r8, HEX);
  }
  Serial.println("---");
  delay(500);
#elif TEST_MODE == MODE_PIN_LOOPBACK
  pinMode(PIN_SPI_MOSI, OUTPUT);
  pinMode(PIN_SPI_MISO, INPUT_PULLUP);
  digitalWrite(PIN_SPI_MOSI, HIGH);
  delay(5);
  int hi = digitalRead(PIN_SPI_MISO);
  digitalWrite(PIN_SPI_MOSI, LOW);
  delay(5);
  int lo = digitalRead(PIN_SPI_MISO);
  Serial.print("hi=");
  Serial.print(hi);
  Serial.print(" lo=");
  Serial.println(lo);
  delay(500);
#elif TEST_MODE == MODE_DIAG
  pinMode(PIN_SPI_MISO, INPUT_PULLUP);
  int miso = digitalRead(PIN_SPI_MISO);
  int adc = analogRead(A1);
  Serial.print("MISO_PU=");
  Serial.print(miso);
  Serial.print(" A1=");
  Serial.println(adc * 3.3f / 1023.0f, 2);
  delay(500);
#elif TEST_MODE == MODE_DRV_TEST
  testDRV();
  delay(2000);
#elif TEST_MODE == MODE_OPEN_LOOP
  motor.loopFOC();
  motor.move(TARGET_VELOCITY);
  static uint32_t last_print = 0;
  if (millis() - last_print > 500) {
    last_print = millis();
    Serial.print("angle ");
    Serial.print(motor.shaft_angle, 3);
    Serial.print(" Uq ");
    Serial.print(motor.voltage.q, 2);
    Serial.print(" enabled ");
    Serial.print(motor.enabled);
    Serial.print(" status ");
    Serial.println((int)motor.motor_status);
  }
#elif TEST_MODE == MODE_SCOPE || TEST_MODE == MODE_SENSING_SCOPE
  static bool motor_tripped = false;
  if (!motor_tripped && millis() - motor_start_ms > MOTOR_RUN_TIMEOUT_MS) {
    motor_tripped = true;
    motor.disable();
    digitalWrite(PIN_N_SLEEP, LOW);
  }
#if TEST_MODE == MODE_SENSING_SCOPE
  _serviceSAMD51Sensing();
#endif
  motor.loopFOC();
  motor.move(TARGET_VELOCITY);
  static uint32_t last_scope = 0;
  if (micros() - last_scope >= 10000) {
    last_scope = micros();
    sendScopeData();
  }
#else
  motor.loopFOC();
  motor.move(TARGET_VELOCITY);
#endif
}
