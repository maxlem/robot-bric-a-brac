// MicroSpora bring-up: one test at a time, selected by TEST_MODE.
//
// Stage the checks so that only one thing is unknown at a time:
//   MODE_BLINK     board is alive and flashable
//   MODE_VSENS     bus voltage divider matches a multimeter
//   MODE_ENCODER   MT6701 angle, direction, eccentricity
//   MODE_OPENLOOP  phases wired correctly, currents sum to zero
//   MODE_CURRENT   closed-loop current control, for tuning
//   MODE_CHARACTERISE  SimpleFOC's own R/L identification (needs current sense)
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
#define MODE_CHARACTERISE 7
#define MODE_SCOPE 8
#define MODE_WEB 9

#define TEST_MODE MODE_WEB

// 200 Hz: 66 bytes per packet at 250000 baud is 2.6 ms, so this leaves
// headroom and gives the scope a 0.5 s window over its last 100 samples.
#define SCOPE_PERIOD_US 5000

// The official MicroSpora firmware uses 6-PWM, and so does the DRV8316 driver
// class by default. 3-PWM was only a workaround for the 6-PWM build that
// produced no output; that build was missing the dead-time setting below.
#define USE_3PWM 0

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

// Commander interface for the SimpleFOC WebController. The motor is registered
// as 'M', and the monitor uses the same character as its start/end marker so
// the browser can tell motor data from command replies.
Commander command = Commander(Serial);
void doMotor(char *cmd) { command.motor(&motor, cmd); }


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
  // The driver limit is the hardware ceiling; motor.voltage_limit is the
  // safety limit. Clamping the driver to VOLTAGE_LIMIT makes the WebController
  // voltage slider ineffective, because setPwm() clamps every phase to it.
  driver.voltage_limit = busVoltage();
  // Match the official MicroSpora firmware. BLDCDriver6PWM defaults to a dead
  // time of 2 % of the PWM period; at 0.5 V on a 12 V bus (4 % duty) that
  // cancels most of the output, which is why the first 6-PWM build looked dead.
  // The DRV8316 needs about 0.1 %.
  driver.pwm_frequency = 25000;
  driver.dead_zone = 0.001f;
  driver.init(&SPI_driver);
#if !USE_3PWM
  driver.setPWMMode(PWM6_Mode);
#endif
  driver.setSlew(Slew_200Vus);
  driver.setOCPMode(NoAction);
  driver.setCurrentSenseGain(Gain_0V375);
  driver.setBuckVoltage(VB_5V);

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

  if (TEST_MODE == MODE_WEB) {
    // Open loop until the encoder magnet is mounted: the WebController can
    // change the target and the limits, but closed-loop modes need initFOC.
    motor.controller = MotionControlType::velocity_openloop;
    if (!motor.init()) {
      Serial.println("motor init failed");
      return;
    }
    command.add('M', doMotor, "motor");
    motor.useMonitoring(Serial);
    motor.monitor_start_char = 'M';
    motor.monitor_end_char = 'M';
    motor.monitor_downsample = 10;
    command.verbose = VerboseMode::machine_readable;
    Serial.println("web: commander ready, motor id M, open loop");
    return;
  }

  if (TEST_MODE == MODE_CHARACTERISE) {
    if (!motor.init()) {
      Serial.println("motor init failed");
      return;
    }
    // SimpleFOC's own identification: ramps a d-axis voltage to measure R, then
    // steps it to measure L. It needs a working current sense and returns 3
    // ("current too low") when the chain cannot see the current, so this doubles
    // as the current-sense test. No sensor is linked, so it runs at angle 0.
    Serial.println("characterise: measuring R and L, the rotor will not turn");
    // BLDCMotor's wrapper hardcodes correction_factor = 1.0, which reports
    // 3x R_phase. Call the base class with 1.5 so phase_resistance is the
    // phase-to-phase value (2x R_phase) that the milliohm meter measured.
    int result = motor.FOCMotor::characteriseMotor(VOLTAGE_LIMIT, 1.5f);
    Serial.print("characterise result: ");
    Serial.println(result);
    if (result == 0) {
      // The library stores the per-phase value the current controller needs,
      // even though its debug message calls it phase-to-phase.
      Serial.print("R phase: ");
      Serial.print(motor.phase_resistance, 4);
      Serial.println(" ohm");
      Serial.print("Ld: ");
      Serial.print(motor.axis_inductance.d * 1e6f, 2);
      Serial.println(" uH");
      Serial.print("Lq: ");
      Serial.print(motor.axis_inductance.q * 1e6f, 2);
      Serial.println(" uH");
    } else {
      Serial.println("characterise failed; the current sense is not usable yet");
    }
    return;
  }

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
#if TEST_MODE != MODE_WEB && TEST_MODE != MODE_SCOPE
  static uint32_t last_config = 0;
  if (millis() - last_config >= 5000) {
    last_config = millis();
    printConfig();
  }
#endif

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

#if TEST_MODE == MODE_WEB
  // The WebController drives the target through the Commander and reads the
  // monitor stream. Keep the FOC loop running at full rate.
  motor.loopFOC();
  motor.move();
  motor.monitor();
  command.run();
#endif
}
