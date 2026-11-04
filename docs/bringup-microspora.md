# MicroSpora bring-up

Board: SimpleFOC-microspora v1.7 — STM32G431CBU6, DRV8316 (6-PWM), three
low-side shunts, MT6701 magnetic encoder, CAN transceiver, USB-C.

## Wiring for the first tests

| Signal | Pin | Notes |
|---|---|---|
| ISENS_A / B / C | PA0 / PA1 / PA2 | DRV8316 current sense, gain 0.375 V/A |
| VSENS | PB11 | bus divider, 4.7k / 47k, scale ~11.6 |
| Encoder | PA4–PA7 | MT6701 over SSI, SPI1 |
| PWM | PA8–PA10, PB13–PB15 | 6-PWM |
| CAN | PB8 / PB9 | 120 ohm termination at the physical ends only |

Bench supply on **VBAT / PGND**, 8–12 V with the current limit set to 0.3 A for
the first tests. USB powers the MCU only; the motor supply powers the bridge.

## Flashing

### Once, with the button

Hold **BOOT**, tap **RESET**, release **BOOT**. The board enumerates as
`0483:df11` (DFU), then:

```bash
pio run -d firmware/microspora-bringup -t upload
```

On Linux this needs a udev rule, otherwise `dfu-util` fails with
`LIBUSB_ERROR_ACCESS`:

```bash
sudo tee /etc/udev/rules.d/60-stm32-dfu.rules >/dev/null <<'EOF'
SUBSYSTEM=="usb", ATTR{idVendor}=="0483", ATTR{idProduct}=="df11", MODE="0666"
EOF
sudo udevadm control --reload-rules
sudo udevadm trigger --action=add --subsystem-match=usb
```

`dfu-util: Error during download get_status` at the end is harmless; the image
is already written and the board reboots.

### Every time

The BOOT/RESET cycle is needed for each flash. A software jump to the system
bootloader was tried and removed: on this board the USB handover is unreliable
and the core hangs instead of enumerating, which strands the firmware until the
button is pressed anyway. Debugger access would solve it, but the SWD pins are
not broken out (SWDIO PA13 is not on any header; only SWCLK PA14 is).

## Test modes

Set `TEST_MODE` at the top of `src/main.cpp`, rebuild, flash.

| Mode | What it checks | Expected |
|---|---|---|
| `MODE_BLINK` | board alive, LED on PC6 | 1 Hz blink |
| `MODE_VSENS` | bus divider calibration | matches a multimeter within 0.05 V |
| `MODE_ENCODER` | MT6701 wiring, direction, magnet centring | smooth monotonic angle over a turn |
| `MODE_OPENLOOP` | phase order, current polarity | shaft turns slowly, `ia + ib + ic` ≈ 0 |
| `MODE_CURRENT` | alignment and current loop | `id` near 0, `iq` follows the target |

### Calibration done so far

- `vbus_scale`: 12.04 V measured against 11.450 V reported at scale 11.0, so the
  calibrated value is **11.57**. Recorded in `hardware/motor_params.json` with
  provenance `bench`.

## What prevented rotation (recorded because it cost a session)

Three separate defects, each enough on its own:

1. **PWM mode override.** `setup()` called `setPWMMode(PWM6_Mode)` unconditionally,
   so a 3-PWM build reported `pwm 0` and the chip was in the wrong mode for the
   wiring. The Feather configuration that works with this motor is 3-PWM with the
   low-side inputs held high.
2. **`loopFOC()` is required in open loop.** `velocityOpenloop()` only integrates
   `shaft_angle`; the electrical angle applied by `move()` is computed in
   `loopFOC()`. Without it the voltage vector sits at a fixed angle: constant
   currents, a short twitch, no rotation.
3. **Do not link the sensor in open loop.** Without `initFOC()` the direction
   stays `UNKNOWN`, and `BLDCMotor::init()` only defaults it to CW when no sensor
   is linked.

Symptom of (2) and (3) is identical: `ia/ib/ic` constant, rotor moves a fraction
of a turn and stops. Symptom of (1) is different: no current at all.

## Next after bring-up

Run `docs/motor-identification.md` in order: current offsets and gain, inverter
`V_error` from a DC hold with known `R`, `L(I)` from a step, `psi` from a spin,
then `J`, `B`, `Tc`. Write each result back into
`hardware/motor_params.json` and change its provenance from `assumed` to
`bench` or `in_situ`.
