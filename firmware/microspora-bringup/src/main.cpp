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
#include <string.h>
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

#define TEST_MODE MODE_OPENLOOP

// Below this the DRV8316 is not supposed to run the motor at all.
#define SUPPLY_MIN_V 8.0f
#define VOLTAGE_LIMIT 1.5f
#define OPENLOOP_VELOCITY 5.0f  // rad/s, slow enough to see a wiring error
#define CURRENT_TARGET_A 0.2f
#define PRINT_PERIOD_MS 500

BLDCMotor motor = BLDCMotor(MOTOR_POLE_PAIRS);
DRV8316Driver6PWM driver =
    DRV8316Driver6PWM(PHA_H, PHA_L, PHB_H, PHB_L, PHC_H, PHC_L, DRV_CS, false);

SPISettings mt6701Settings(10000000, MT6701_BITORDER, SPI_MODE2);
MagneticSensorMT6701SSI sensor = MagneticSensorMT6701SSI(ENC_CS, mt6701Settings);

// The 4-argument form is mV per amp, matching the DRV8316 current-sense gain.
LowsideCurrentSense current_sense =
    LowsideCurrentSense(MOTOR_CURRENT_SENSE_MV_PER_A, (int)ISENS_A, (int)ISENS_B, (int)ISENS_C);

SPIClass SPI_encoder(ENC_NC, ENC_SDO, ENC_CLK);
SPIClass SPI_driver(PB5_ALT1, PB4_ALT1, PC10);


// Jump into the STM32 system bootloader so the host can flash without touching
// BOOT0. The bootloader stays mapped at 0x1FFF0000 even with BOOT0 low.
static void jumpToDfu() {
  Serial.println("jumping to DFU");
  Serial.flush();
  // Let the USB transfer finish; jumping mid-transfer leaves the bootloader
  // unable to enumerate and the chip appears hung.
  delay(300);
  // Minimal handover: no HAL_RCC_DeInit here, it disables the HSI48 clock the
  // bootloader needs for USB and the core hangs.
  __disable_irq();
  SysTick->CTRL = 0;
  SysTick->LOAD = 0;
  SysTick->VAL = 0;
  const uint32_t base = 0x1FFF0000;
  __set_MSP(*reinterpret_cast<volatile uint32_t*>(base));
  void (*entry)(void) =
      reinterpret_cast<void (*)(void)>(*reinterpret_cast<volatile uint32_t*>(base + 4));
  entry();
}

// One-line serial commands, available in every mode.
static void pollCommands() {
  static char buffer[16];
  static uint8_t length = 0;
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      buffer[length] = 0;
      if (strcmp(buffer, "dfu") == 0) jumpToDfu();
      else if (length > 0) Serial.println("commands: dfu");
      length = 0;
    } else if (length < sizeof(buffer) - 1) {
      buffer[length++] = c;
    }
  }
}

// Scale comes from hardware/motor_params.json, calibrated against a
// multimeter; the VSCALE build flag is only the datasheet starting point.
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
  sensor.init(&SPI_encoder);

#if TEST_MODE == MODE_ENCODER
  return;
#endif

  driver.voltage_power_supply = busVoltage();
  driver.voltage_limit = VOLTAGE_LIMIT;
  driver.init(&SPI_driver);
  driver.setPWMMode(PWM6_Mode);
  driver.setOCPMode(NoAction);
  driver.setCurrentSenseGain(Gain_0V375);

  current_sense.linkDriver(&driver);
  if (!current_sense.init()) {
    Serial.println("current sense init failed");
    return;
  }
  current_sense.skip_align = true;
  motor.linkCurrentSense(&current_sense);

  motor.linkDriver(&driver);
  motor.linkSensor(&sensor);
  motor.voltage_limit = VOLTAGE_LIMIT;
  motor.velocity_limit = 20.0f;
  motor.motion_downsample = 4;

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
  pollCommands();

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

#if TEST_MODE == MODE_OPENLOOP
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
