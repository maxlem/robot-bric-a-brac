# Robot Bric-à-Brac

Firmware and notes for a small balancing robot built from LEGO, 3D printed
parts, and gimbal-class BLDC motors. The work here feeds the MuJoCo twin in
the `Clara` repository.

## Layout

```text
docs/            wiring, identification protocol, decisions
firmware/
  common/        shared by every target: scope packet, generated parameters
  feather-drv8316/   Adafruit Feather M4 CAN + DRV8316EVM (SAME51)
  microspora-bringup/ SimpleFOC MicroSpora (STM32G431, DRV8316, MT6701)
hardware/
  motor_params.json  single source of truth for measured motor parameters
tools/
  gen_motor_params.py  JSON to C header, runs before each build
  SimpleFOCScope/      PC-side scope (git submodule)
third_party/
  Arduino-FOC/         SimpleFOC fork with the SAME51 sensing changes (submodule)
plans/           mechanical plans
```

## Targets

| Target | Board | Build | Flash |
|---|---|---|---|
| `firmware/feather-drv8316` | Adafruit Feather M4 CAN | `pio run -d firmware/feather-drv8316` | USB, `pio run -d firmware/feather-drv8316 -t upload` |
| `firmware/microspora-bringup` | MicroSpora (STM32G431CB) | `pio run -d firmware/microspora-bringup` | DFU: hold BOOT, tap RESET, release BOOT, then upload |

Both targets select a test with `TEST_MODE` in their `src/main.cpp`.

## Motor parameters

`hardware/motor_params.json` holds the numbers that describe the motor:
resistance, inductance, flux linkage, inertia, friction, dead time, and the
current-sense calibration. `tools/gen_motor_params.py` turns it into
`firmware/common/include/motor_params.h` before every build, so firmware,
PC tools, and the simulation cannot disagree.

`provenance` records where each value came from: `bench`, `in_situ`,
`datasheet`, or `assumed`. The build prints a warning while values are still
assumed. Do not act on assumed numbers.

The protocol that replaces them with measured ones is in
[`docs/motor-identification.md`](docs/motor-identification.md).

## Flashing the MicroSpora

Each flash needs BOOT + RESET to enter the DFU bootloader; SWD is not broken
out on the board, so there is no debugger path. See
[`docs/bringup-microspora.md`](docs/bringup-microspora.md).

## Submodules

Clone with `git clone --recursive`, or after cloning run:

```bash
git submodule update --init --recursive
```

## Docs

- [`docs/wiring-feather-drv8316.md`](docs/wiring-feather-drv8316.md) — bench
  wiring and safety checks for the Feather and DRV8316EVM.
- [`docs/motor-identification.md`](docs/motor-identification.md) — how to
  measure R, L, flux linkage, inertia, and the inverter voltage error.
