# Feather M4 CAN + DRV8316EVM + magnetic encoder wiring

This is the wiring for the `motor-test` PlatformIO project, configured for the Adafruit Feather M4 CAN Express (`adafruit_feather_m4_can`).

## 1. Before you start

- Do not connect the motor power supply until all signal wiring and checks are done.
- The Feather M4 has only one GND pin. Run it to a ground rail (breadboard rail or small terminal block), then connect the EVM AGND, encoder GND, and `DRVOFF` to that rail.
- The laptop connects to the Feather USB port for programming and Serial Monitor only. Motor power comes from the bench supply through the EVM, never from USB.
- `INLA`, `INLB`, and `INLC` are wired to PWM-capable pins and held high for 3-PWM, so the same wiring can be switched to 6-PWM later.
- This project is configured for the **Feather M4 CAN Express** (SAME51). If you use a plain Feather M4 Express (SAMD51), change `board` in `platformio.ini` to `adafruit_feather_m4`; the wiring pins used here are the same.
- The DRV8316EVM is a TI LaunchPad booster. Use the **male headers on the top** of the EVM with Dupont wires. The female headers on the bottom are meant for a LaunchPad.
- The EVM silkscreen labels are on the **bottom** of the board. Use the signal names, not only the pin numbers.
- On the Feather, the SPI pins are labeled **SCK, MOSI, MISO** (Arduino D25/D24/D23); RX/TX are D0/D1. Use the printed signal names.
- This guide assumes the EVM has the **DRV8316R** (SPI) variant, which is the default. If the chip is marked **DRV8316T**, stop and use the hardware-variant configuration instead.
- Required: Dupont wires, a breadboard or 3.3 V/ground distribution point, a multimeter, and a current-limited bench supply.

## 2. What connects to what

```text
Laptop USB ----> Feather M4 ----> DRV8316EVM ----> Motor phases A/B/C
                    |                  |
                    |                  +---- VBAT / PGND from bench PSU
                    |
                    +---- SPI (SCK/MOSI/MISO/CS) ----> AS5047P / AS5048A encoder
                    +---- 3V3 ------------------------> encoder VDD
                    +---- GND --> ground rail --> EVM AGND, encoder GND, DRVOFF
```

The DRV8316 and the encoder share the Feather SPI bus. Each has its own chip-select pin.

## 3. Quick wire checklist

The Feather has one GND pin. Use a ground rail or a small 3-way junction: one wire from the Feather GND, then to the EVM AGND, encoder GND, and `DRVOFF`.

- [ ] Feather `GND` -> ground rail
- [ ] Ground rail -> EVM `J3-4 AGND`
- [ ] Feather `D10` -> EVM `J4-1 INHA`
- [ ] Feather `D11` -> EVM `J4-5 INHB`
- [ ] Feather `D12` -> EVM `J4-9 INHC`
- [ ] Feather `TX (D1)` -> EVM `J4-3 INLA`
- [ ] Feather `RX (D0)` -> EVM `J4-7 INLB`
- [ ] Feather `D13` -> EVM `J4-11 INLC`
- [ ] Feather `D9` -> EVM `J4-4 nSCS`
- [ ] Feather `MOSI (D24)` -> EVM `J4-12 SDI`
- [ ] Feather `MISO (D23)` -> EVM `J4-14 SDO`
- [ ] Feather `SCK (D25)` -> EVM `J3-13 SCLK`
- [ ] Feather `D6` -> EVM `J3-17 nSLEEP`
- [ ] Ground rail -> EVM `J4-16 DRVOFF`
- [ ] Feather `3V3` -> encoder `VDD`
- [ ] Ground rail -> encoder `GND`
- [ ] Feather `SCK (D25)` -> encoder `SCK`
- [ ] Feather `MOSI (D24)` -> encoder `MOSI`
- [ ] Feather `MISO (D23)` -> encoder `MISO`
- [ ] Feather `D5` -> encoder `CSn`
- [ ] Motor phase A -> `OUTA`
- [ ] Motor phase B -> `OUTB`
- [ ] Motor phase C -> `OUTC`
- [ ] PSU positive -> `VBAT`
- [ ] PSU negative -> `PGND`
- [ ] Leave EVM `J3-19 nFAULT` unconnected
- [ ] EVM `J3-14 ISENA` -> Feather `A0` (current sense)
- [ ] EVM `J3-16 ISENB` -> Feather `A1` (current sense)
- [ ] EVM `J3-18 ISENC` -> Feather `A2` (current sense)
- [ ] EVM `J3-6 VSENA` -> Feather `A3` (voltage sense)
- [ ] EVM `J3-8 VSENB` -> Feather `A4` (voltage sense)
- [ ] EVM `J3-10 VSENC` -> Feather `A5` (voltage sense)

## 4. Feather M4 pins used

| Feather pin | Use | Direction | Notes |
|---|---|---|---|
| D10 | DRV8316 `INHA` | output, PWM | TCC0 channel 0 |
| D11 | DRV8316 `INHB` | output, PWM | TCC0 channel 1 |
| D12 | DRV8316 `INHC` | output, PWM | TCC0 channel 2 |
| TX (D1) | DRV8316 `INLA` | output/PWM | low-side A; high in 3-PWM |
| RX (D0) | DRV8316 `INLB` | output/PWM | low-side B; high in 3-PWM |
| D13 | DRV8316 `INLC` | output/PWM | low-side C; high in 3-PWM; red LED |
| D9 | DRV8316 `nSCS` | output | SPI chip select |
| D6 | DRV8316 `nSLEEP` | output | high = awake |
| MOSI (D24) | SPI `MOSI` / `SDI` | output | shared by DRV8316 and encoder |
| MISO (D23) | SPI `MISO` / `SDO` | input | shared by DRV8316 and encoder |
| SCK (D25) | SPI `SCK` | output | shared by DRV8316 and encoder |
| D5 | Encoder `CSn` | output | encoder chip select |
| 3V3 | encoder VDD | power | 3.3 V logic |
| GND | ground rail -> EVM `AGND`; encoder GND and `DRVOFF` join the rail | ground | common logic ground |
| A0 | DRV8316 `ISENA` | analog input | synchronized current sensing |
| A1 | DRV8316 `ISENB` | analog input | synchronized current sensing |
| A2 | DRV8316 `ISENC` | analog input | synchronized current sensing |
| A3 | DRV8316 `VSENA` | analog input | synchronized voltage sensing |
| A4 | DRV8316 `VSENB` | analog input | synchronized voltage sensing |
| A5 | DRV8316 `VSENC` | analog input | synchronized voltage sensing |

## 5. DRV8316EVM connections

The EVM header pin numbers below are from the DRV8316xEVM user guide. Verify pin 1 on the physical header before inserting wires.

| Feather M4 | EVM header | EVM signal | Purpose |
|---|---|---|---|
| D10 | J4 pin 1 | `INHA` | phase A PWM |
| D11 | J4 pin 5 | `INHB` | phase B PWM |
| D12 | J4 pin 9 | `INHC` | phase C PWM |
| TX (D1) | J4 pin 3 | `INLA` | low-side A; high in 3-PWM mode |
| RX (D0) | J4 pin 7 | `INLB` | low-side B; high in 3-PWM mode |
| D13 | J4 pin 11 | `INLC` | low-side C; high in 3-PWM mode |
| D9 | J4 pin 4 | `nSCS` | DRV8316 SPI chip select |
| MOSI (D24) | J4 pin 12 | `SDI` | SPI data into DRV8316 |
| MISO (D23) | J4 pin 14 | `SDO` | SPI data out of DRV8316 |
| SCK (D25) | J3 pin 13 | `SCLK` | SPI clock |
| D6 | J3 pin 17 | `nSLEEP` | high = device awake |
| Ground rail | J4 pin 16 | `DRVOFF` | low = gate driver enabled |
| Ground rail | J3 pin 4 | `AGND` | logic ground |
| A0 | J3 pin 14 | `ISENA` | phase A current sense |
| A1 | J3 pin 16 | `ISENB` | phase B current sense |
| A2 | J3 pin 18 | `ISENC` | phase C current sense |
| A3 | J3 pin 6 | `VSENA` | phase A voltage sense |
| A4 | J3 pin 8 | `VSENB` | phase B voltage sense |
| A5 | J3 pin 10 | `VSENC` | phase C voltage sense |

Leave `nFAULT` (J3-19) unconnected. D4 is the CAN boost enable and D5 is the encoder CS; do not put nFAULT on either. The firmware reads the DRV8316 fault status over SPI.

The `ISENx`/`VSENx` rows above are the synchronized-sensing mapping; wire them to A0-A5. `VSENVM` (J3-12) is not used because the main bus voltage is sensed centrally.

Do not use J3 pin 9 (`nSLEEP` DNP) or J3 pin 15 (`nFAULT` DNP). They are not populated for external use.

On J3, only pin 4 is ground (`AGND`). The unlabeled / "Not used" pins are not ground. J4 pin 2 is the second `AGND` connection.

There are two separate chip-select lines because the DRV8316 and encoder share the SPI bus: D9 -> EVM `J4-4 nSCS` (DRV8316), and D5 -> encoder `CSn`. Both are required.

## 6. Motor, power and encoder

### Motor

Connect the three motor phases to the screw terminal labeled `OUTA`, `OUTB`, `OUTC`. The phase order does not need to be perfect for the first test; if the motor runs the wrong way later, swap any two phases or invert the sensor direction in software.

### Power

| Bench supply | EVM terminal |
|---|---|
| Positive | `VBAT` |
| Negative / ground | `PGND` |

Start with **12 V** and a **0.5 A to 1 A current limit**. Increase only after the open-loop test works. Never connect or disconnect motor phases while the supply is on.

The EVM's internal buck converter should be set to 3.3 V (default). The `3.3VBK` LED should light when `VM` is present. Do not connect the EVM `3.3VBK` output to the Feather `3V3` pin while the Feather is powered over USB. Do not connect it to the Feather `AREF` pin either: `AREF` is the ADC reference, not ground, and tying it to the EVM buck can shut the buck down.

### Encoder

The encoder's 3.3 V comes from the Feather; its ground joins the EVM AGND, which is the same node as the Feather GND.

| AS5047P / AS5048A | Feather M4 |
|---|---|
| VDD / 3V3 | 3V3 |
| GND | ground rail / EVM AGND |
| SCK / CLK | SCK (D25) |
| MOSI / SDI | MOSI (D24) |
| MISO / SDO | MISO (D23) |
| CSn / CS | D5 |

The encoder must be mounted with its magnet centered on the motor shaft and at the correct air gap. Check the encoder datasheet for the exact gap; typically 0.5 mm to 3 mm.

## 7. Wiring order

1. **Ground first.** Connect Feather `GND` to a ground rail, then connect the rail to EVM `J3-4 AGND`. Tie the encoder `GND` and `DRVOFF` to the same rail; the Feather has only one GND pin.
2. **Motor phases.** Connect `OUTA`, `OUTB`, `OUTC` to the motor. Leave the power supply off.
3. **Power input.** Connect the PSU to `VBAT` and `PGND`. Leave the PSU output disabled.
4. **PWM.** Connect D10, D11, D12 to `INHA`, `INHB`, `INHC`.
5. **Low-side inputs.** Connect `TX (D1)` to `INLA`, `RX (D0)` to `INLB`, and `D13` to `INLC`. The firmware holds them high in 3-PWM mode; they are PWM-capable for a later 6-PWM switch.
6. **Enable pins.** Connect D6 to `nSLEEP`. Connect `DRVOFF` to the ground rail.
7. **DRV8316 SPI.** Connect D9 to `nSCS`, MOSI (D24) to `SDI`, MISO (D23) to `SDO`, SCK (D25) to `SCLK`.
8. **Encoder.** Connect 3V3, GND, SCK, MOSI, MISO, and CS as in the encoder table.
9. **Fault.** Leave `nFAULT` (J3-19) unconnected; the firmware reads fault status over SPI. D4 is the CAN boost enable and D5 is the encoder CS.

## 8. Pre-power checks

With all power off, use a multimeter:

- Check for a short between `VBAT` and `PGND`. It should not be a direct short.
- Check for a short between the Feather `3V3` and `GND`. Do this before powering the Feather.
- Check continuity from `TX (D1)`, `RX (D0)`, and `D13` to `INLA`, `INLB`, and `INLC`.
- Remember that `D13` is also the red LED; it will be on while 3-PWM mode holds `INLC` high.
- Check that `DRVOFF` is connected to the ground rail.
- Check that the encoder `VDD` is on 3.3 V and not 5 V unless the encoder board explicitly requires 5 V.
- Check that no motor phase is shorted to `PGND` or to the motor body.
- Check that the Feather GND, ground rail, EVM AGND, encoder GND, and PSU PGND are connected.

## 9. Power-up sequence

1. **Encoder-only test.** Connect the Feather USB and upload the sensor test with the 12 V supply output off. Then power the EVM at 12 V with a 0.2 A current limit. The firmware keeps `nSLEEP` low and PWM low, so the motor stays asleep. Rotate the motor by hand and confirm that the angle changes smoothly. Do not leave the EVM unpowered while the Feather is driving its inputs.
2. **Open-loop test.** Set the PSU to 12 V with a 1–3 A limit, enable the PSU, and upload the open-loop/scope firmware. The motor should spin slowly. If it does not, raise `VOLTAGE_LIMIT` in `src/main.cpp` and check the current limit. The 5010 motor may need up to 3 A to break cogging; the DRV8316EVM is rated for 3 A continuous.
3. **Closed-loop test.** Secure the motor, upload the closed-loop firmware, and watch the serial output. `initFOC` will move the rotor during alignment. `initFOC 1` means success.

Do not leave the motor free to jump during `initFOC`. Keep the shaft lightly loaded or clamped.

## 10. Firmware settings to match the wiring

In `src/main.cpp`:

| Setting | Default | Change when |
|---|---|---|
| `TEST_MODE` | `MODE_SENSING_SCOPE` | use `MODE_SENSOR_TEST` when the AS5048A arrives, `MODE_OPEN_LOOP` for motor-only tests |
| `USE_6PWM` | `0` | set to `1` only when you want 6-PWM with the existing wiring |
| `ENCODER_TYPE` | `ENCODER_AS5048A` | set to `ENCODER_AS5047P` if that is your chip |
| `POLE_PAIRS` | `7` | 14 magnets = 7 pole pairs, which matches this motor |
| `SUPPLY_VOLTAGE` | `12.0f` | match your bench supply, or the central bus voltage |
| `VOLTAGE_LIMIT` | `1.5f` | increase if the motor does not start in open loop |
| `TARGET_VELOCITY` | `8.0f` | initial test speed in rad/s |

## 11. Troubleshooting

| Symptom | Check |
|---|---|
| Encoder angle stays at 0 or jumps randomly | Encoder type, CS on D5, SCK/MOSI/MISO, 3.3 V and GND, magnet position |
| Motor does not move in open loop | PSU current limit, `VOLTAGE_LIMIT`, `TX/RX/D13` high, `nSLEEP` high, `DRVOFF` low |
| Motor vibrates but does not rotate | One phase wire loose, phase order, low voltage limit |
| `initFOC 0` | Encoder not reading, sensor direction, alignment voltage too low, motor mechanically stuck |
| DRV8316 fault LED on | Short on a phase output, overcurrent, overtemperature, supply problem |
| Feather disconnects when the motor spins | Supply noise or ground bounce; keep the PSU current limit low, improve grounding, keep motor wires away from USB/SPI wires |
| Motor spins the wrong way in closed loop | Swap two motor phases or set `motor.sensor_direction` after checking the sensor |

## 12. Notes

- The firmware uses **3-PWM mode**, so the code drives `INLA`, `INLB`, and `INLC` high through TX (D1), RX (D0), and D13. The DRV8316 SPI configuration selects 3-PWM mode at startup.
- On the Feather M4, D0 and D1 are labeled **RX** and **TX**. They are also Serial1; if you later add the Raspberry Pi on Serial1, use a different low-side pin set.
- The low-side pins are intentionally PWM-capable and timer-compatible with the high-side pins: D10/TX (D1), D11/RX (D0), and D12/D13. Setting `USE_6PWM` to `1` switches the driver to 6-PWM without changing the wiring.
- D13 is also the Feather's red LED, so it will be on during 3-PWM operation and may flicker in 6-PWM mode.
- The DRV8316 current-sense outputs (`ISENA/B/C`) connect to A0-A2 and the phase-voltage outputs (`VSENA/B/C`) to A3-A5 for synchronized telemetry. The motor still runs in voltage open-loop; the measurements are for the scope, not closed-loop current control.
- The EVM Hall connector is not used because the motor has an SPI magnetic encoder.
- The Feather SPI header is labeled SCK/MOSI/MISO, not D25/D24/D23. The DRV8316 and encoder share those three lines; each has its own CS.
- Keep the encoder SPI wires short. If the encoder readings are noisy, lower the SPI clock in `src/main.cpp` from 1 MHz to 500 kHz.

## 13. Scope telemetry

`MODE_SCOPE` streams SimpleFOCScope packets over USB serial at 115200 baud:

- newline-terminated header `ScopeData`, then the binary `ScopeData` struct
- struct definition: `firmware/motor-test/include/ScopeData.h`
- fields: `ia`, `ib`, `ic`, `va`, `vb`, `vc`
- `ia`…`vc` are populated in `MODE_SENSING_SCOPE` from A0–A5
- `ia`…`ic` use the DRV8316 150 mV/A current-sense output
- `va`…`vc` are the raw ADC voltages from the EVM’s phase-voltage dividers; scale them with the divider ratio for actual phase volts

Power the EVM at 12 V **before** resetting the Feather so the current-sense offset calibration sees the real 0 A bias. If you power it later, reset the Feather again.

In SimpleFOCScope, set `headers = ["ScopeData.h"]` and `bauds = 115200`, and copy `ScopeData.h` into the app’s working directory.
