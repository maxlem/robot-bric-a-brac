// MicroSpora bring-up: one test at a time, selected by TEST_MODE.
//
// Stage the checks so that only one thing is unknown at a time:
//   MODE_BLINK     board is alive and flashable
//   MODE_VSENS     bus voltage divider matches a multimeter
//   MODE_ENCODER   MT6701 angle, direction, eccentricity
//   MODE_OPENLOOP  phases wired correctly, currents sum to zero
//   MODE_CURRENT   closed-loop current control, for tuning
//
// The motor parameters come from hardware/motor_params.json through the
// generated motor_params.h, so firmware and simulation share one source.

#include <Arduino.h>
#include <SPI.h>
#include <SimpleFOC.h>
#include <SimpleFOCDrivers.h>
#include "drivers/drv8316/drv8316.h"
#include "current_sense/hardware_specific/stm32/stm32g4/stm32g4_hal.h"
#include "encoders/mt6701/MagneticSensorMT6701SSI.h"
#include "ScopeData.h"
#include "motor_params.h"

#define MODE_BLINK 0
#define MODE_VSENS 1
#define MODE_ENCODER 2
#define MODE_OPENLOOP 3
#define MODE_CURRENT 4
#define MODE_STATIC 5
#define MODE_IDENT_R 6

#define TEST_MODE MODE_IDENT_R

// The Feather drove this motor through the same DRV8316 in 3-PWM mode, with the
// low-side inputs held high. Keep that as a switch so the two can be compared.
#define USE_3PWM 1

// Below this the DRV8316 is not supposed to run the motor at all.
#define SUPPLY_MIN_V 8.0f
#define VOLTAGE_LIMIT 0.5f
#define OPENLOOP_VELOCITY 5.0f  // rad/s, slow enough to see a wiring error
#define CURRENT_TARGET_A 0.2f
#define PRINT_PERIOD_MS 500

BLDCMotor motor = BLDCMotor(MOTOR_POLE_PAIRS);
#if USE_3PWM
DRV8316Driver3PWM driver = DRV8316Driver3PWM(PHA_H, PHB_H, PHC_H, DRV_CS);
#else
DRV8316Driver6PWM driver =
    DRV8316Driver6PWM(PHA_H, PHA_L, PHB_H, PHB_L, PHC_H, PHC_L, DRV_CS, false);
#endif

SPISettings mt6701Settings(10000000, MT6701_BITORDER, SPI_MODE2);
MagneticSensorMT6701SSI sensor = MagneticSensorMT6701SSI(ENC_CS, mt6701Settings);

// The 4-argument form is mV per amp, matching the DRV8316 current-sense gain.
LowsideCurrentSense current_sense =
    LowsideCurrentSense(MOTOR_CURRENT_SENSE_MV_PER_A, (int)ISENS_A, (int)ISENS_B, (int)ISENS_C);

SPIClass SPI_encoder(ENC_NC, ENC_SDO, ENC_CLK);
SPIClass SPI_driver(PB5_ALT1, PB4_ALT1, PC10);


// Scale comes from hardware/motor_params.json, calibrated against a
// multimeter; the VSCALE build flag is only the datasheet starting point.
// Bring-up convenience: repeat the configuration periodically so it can be
// read without catching the boot banner.
static void printConfig() {
  Serial.print("cfg: motor ");
  Serial.print(MOTOR_NAME);
  Serial.print(" | mode ");
  Serial.print(TEST_MODE);
  Serial.print(" | enabled ");
  Serial.print(motor.enabled ? 1 : 0);
  Serial.print(" | status ");
  Serial.print((int)motor.motor_status);
  Serial.print(" | volt_limit ");
  Serial.print(motor.voltage_limit, 2);
  Serial.print(" | supply ");
  Serial.print(driver.voltage_power_supply, 2);
  Serial.print(" | pwm ");
  Serial.print((int)driver.getPWMMode());
  DRV8316Status drv = driver.getStatus();
  Serial.print(" | drv_fault ");
  Serial.print(drv.isFault() ? 1 : 0);
  Serial.print(" | drv_spi_err ");
  Serial.print(drv.isSPIError() ? 1 : 0);
  Serial.print(" | Ua ");
  Serial.println(motor.voltage.q, 3);
}

static float busVoltage();

// Hold a fixed electrical angle and sweep the applied voltage in both
// polarities. At standstill the winding is purely resistive, so
// V_applied = R_total * I and the shortfall against duty * V_bus is the
// inverter error (dead time plus conduction drops).
static void identifyResistance() {
  static const float levels[] = {0.05f, 0.10f, 0.20f, 0.35f, 0.50f};
  Serial.println("ident R: fixed angle, voltage sweep, both polarities");
  Serial.println("v_cmd v_bus ia ib ic");
  for (float level : levels) {
    for (int polarity = 1; polarity >= -1; polarity -= 2) {
      motor.setPhaseVoltage(polarity * level, 0.0f, 0.0f);
      delay(400);
      float sum_a = 0, sum_b = 0, sum_c = 0;
      int samples = 0;
      uint32_t start = millis();
      while (millis() - start < 200) {
        PhaseCurrent_s currents = current_sense.getPhaseCurrents();
        sum_a += currents.a;
        sum_b += currents.b;
        sum_c += -(currents.a + currents.b);
        samples++;
        delay(5);
      }
      float voltage = busVoltage();
      Serial.print(polarity * level, 3);
      Serial.print(" ");
      Serial.print(voltage, 3);
      Serial.print(" ");
      Serial.print(sum_a / samples, 3);
      Serial.print(" ");
      Serial.print(sum_b / samples, 3);
      Serial.print(" ");
      Serial.println(sum_c / samples, 3);
    }
  }
  motor.setPhaseVoltage(0.0f, 0.0f, 0.0f);
  Serial.println("ident R done");
}

static float busVoltage() { return _readRegularADCVoltage(VSENS) * MOTOR_VBUS_SCALE; }

static bool voltageOk() {
  float voltage = busVoltage();
  if (voltage >= SUPPLY_MIN_V) return true;
  Serial.print("bus voltage: ");
  Serial.print(voltage, 2);
  Serial.println(" V, refusing to drive the motor below SUPPLY_MIN_V");
  return false;
}

void setup() {
  Serial.begin(250000);
  delay(3000);

  Serial.println();
  Serial.println("MicroSpora bring-up");
  Serial.print("mode: ");
  Serial.println(TEST_MODE);
  Serial.print("motor: ");
  Serial.println(MOTOR_NAME);
  Serial.print("params: ");
  Serial.println(MOTOR_PARAMS_STATUS);
  Serial.print("pole pairs: ");
  Serial.println(MOTOR_POLE_PAIRS);
  Serial.print("R phase: ");
  Serial.print(MOTOR_R_PHASE_OHM, 3);
  Serial.println(" ohm");
  Serial.print("psi: ");
  Serial.print(MOTOR_PSI_WB, 5);
  Serial.println(" Wb");

#if TEST_MODE == MODE_BLINK
  pinMode(LED_BUILTIN, OUTPUT);
  return;
#endif

#if TEST_MODE == MODE_VSENS
  return;
#endif

  digitalWrite(DRV_CS, HIGH);
#if USE_3PWM
  // 3-PWM expects the low-side inputs tied high; the DRV generates the
  // complementary signal and its own dead time.
  pinMode(PHA_L, OUTPUT);
  pinMode(PHB_L, OUTPUT);
  pinMode(PHC_L, OUTPUT);
  digitalWrite(PHA_L, HIGH);
  digitalWrite(PHB_L, HIGH);
  digitalWrite(PHC_L, HIGH);
#endif
  sensor.init(&SPI_encoder);

#if TEST_MODE == MODE_ENCODER
  return;
#endif

  driver.voltage_power_supply = busVoltage();
  driver.voltage_limit = VOLTAGE_LIMIT;
  driver.init(&SPI_driver);
#if !USE_3PWM
  driver.setPWMMode(PWM6_Mode);
#endif
  driver.setOCPMode(NoAction);
  driver.setCurrentSenseGain(Gain_0V375);

  DRV8316Status status = driver.getStatus();
  Serial.print("driver fault: ");
  Serial.print(status.isFault() ? "YES" : "no");
  Serial.print("  spi error: ");
  Serial.print(status.isSPIError() ? "YES" : "no");
  Serial.print("  pwm mode: ");
  Serial.print((int)driver.getPWMMode());
  Serial.print("  supply: ");
  Serial.print(driver.voltage_power_supply, 2);
  Serial.println(" V");

  current_sense.linkDriver(&driver);
  if (!current_sense.init()) {
    Serial.println("current sense init failed");
    return;
  }
  current_sense.skip_align = true;
  motor.linkCurrentSense(&current_sense);

  motor.linkDriver(&driver);
  // Open loop must not have a sensor linked: without initFOC the direction stays
  // UNKNOWN and the electrical angle never advances, freezing the voltage vector.
  if (TEST_MODE == MODE_CURRENT) motor.linkSensor(&sensor);
  motor.voltage_limit = VOLTAGE_LIMIT;
  motor.velocity_limit = 20.0f;
  motor.motion_downsample = 4;

  if (TEST_MODE == MODE_IDENT_R) {
    if (!motor.init()) {
      Serial.println("motor init failed");
      return;
    }
    identifyResistance();
    return;
  }

  if (TEST_MODE == MODE_STATIC) {
    if (!motor.init()) {
      Serial.println("motor init failed");
      return;
    }
    Serial.println("static vector: measure A-B with a DC voltmeter, expect ~0.5 V");
    return;
  }

  if (TEST_MODE == MODE_OPENLOOP) {
    motor.controller = MotionControlType::velocity_openloop;
    if (!motor.init()) {
      Serial.println("motor init failed");
      return;
    }
    Serial.println("open loop: check that ia + ib + ic is ~0 and the rotor turns smoothly");
    return;
  }

  if (TEST_MODE == MODE_CURRENT) {
    motor.torque_controller = TorqueControlType::foc_current;
    motor.controller = MotionControlType::torque;
    if (!motor.init()) {
      Serial.println("motor init failed");
      return;
    }
    Serial.println("aligning the sensor: the rotor will move");
    if (!motor.initFOC()) {
      Serial.println("initFOC failed");
      return;
    }
    Serial.println("current mode: target");
    Serial.print(CURRENT_TARGET_A, 2);
    Serial.println(" A");
  }
}

void loop() {
  static uint32_t last_config = 0;
  if (millis() - last_config >= 5000) {
    last_config = millis();
    printConfig();
  }

#if TEST_MODE == MODE_BLINK
  digitalWrite(LED_BUILTIN, !digitalRead(LED_BUILTIN));
  delay(500);
  return;
#endif

#if TEST_MODE == MODE_VSENS
  static uint32_t last_vsens = 0;
  if (millis() - last_vsens >= PRINT_PERIOD_MS) {
    last_vsens = millis();
    Serial.print("bus voltage: ");
    Serial.print(busVoltage(), 3);
    Serial.println(" V");
  }
  return;
#endif

#if TEST_MODE == MODE_ENCODER
  static uint32_t last_encoder = 0;
  sensor.update();
  if (millis() - last_encoder >= PRINT_PERIOD_MS) {
    last_encoder = millis();
    Serial.print("angle: ");
    Serial.print(sensor.getAngle(), 4);
    Serial.print("  velocity: ");
    Serial.println(sensor.getVelocity(), 4);
  }
  return;
#endif

  static uint32_t last_print = 0;
  static uint32_t last_voltage_check = 0;
  if (millis() - last_voltage_check >= 200) {
    last_voltage_check = millis();
    if (!voltageOk()) {
      motor.disable();
      return;
    }
  }

#if TEST_MODE == MODE_STATIC
  // Fixed vector at electrical angle 0: phase A high, B and C low. The average
  // phase-to-phase voltage is visible on a multimeter, unlike a rotating vector.
  motor.setPhaseVoltage(0.5f, 0.0f, 0.0f);
  delay(5);
#endif

#if TEST_MODE == MODE_OPENLOOP
  // loopFOC is required even in open loop: it turns the integrated shaft_angle
  // into the electrical angle that move() applies. The sensor is not linked in
  // this mode, so shaft_angle integrates freely.
  motor.loopFOC();
  motor.move(OPENLOOP_VELOCITY);
  if (millis() - last_print >= PRINT_PERIOD_MS) {
    last_print = millis();
    PhaseCurrent_s currents = current_sense.getPhaseCurrents();
    Serial.print("ia ");
    Serial.print(currents.a, 3);
    Serial.print(" ib ");
    Serial.print(currents.b, 3);
    Serial.print(" ic ");
    Serial.print(-(currents.a + currents.b), 3);
    Serial.print("  Ua ");
    Serial.print(motor.Ua, 3);
    Serial.print("  enabled ");
    Serial.print(motor.enabled ? 1 : 0);
    Serial.print("  status ");
    Serial.print((int)motor.motor_status);
    Serial.print("  angle ");
    Serial.println(sensor.getAngle(), 3);
  }
#endif

#if TEST_MODE == MODE_CURRENT
  motor.loopFOC();
  motor.move(CURRENT_TARGET_A);
  if (millis() - last_print >= PRINT_PERIOD_MS) {
    last_print = millis();
    PhaseCurrent_s currents = current_sense.getPhaseCurrents();
    Serial.print("id ");
    Serial.print(motor.current.d, 3);
    Serial.print(" iq ");
    Serial.print(motor.current.q, 3);
    Serial.print("  ia ");
    Serial.print(currents.a, 3);
    Serial.print(" ib ");
    Serial.println(currents.b, 3);
  }
#endif
}
