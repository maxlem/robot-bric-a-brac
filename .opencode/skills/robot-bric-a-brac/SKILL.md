---
name: Robot Bric-à-Brac
description: Use when working in the robot-bric-a-brac repo — SimpleFOC firmware, MicroSpora bring-up, motor parameters, the DM5010/DM5015 leg motors, or the CAD plans.
---

# Robot Bric-à-Brac

A small balancing biped built from LEGO, 3D-printed parts, and gimbal-class
BLDC motors. The firmware and the MuJoCo twin in the `Clara` repo share
`hardware/motor_params.json`.

## Layout

```text
docs/            wiring, identification protocol, decisions
firmware/
  common/        shared: scope packet, generated parameters
  feather-drv8316/   Feather M4 CAN + DRV8316EVM (SAME51)
  microspora-bringup/ MicroSpora (STM32G431, DRV8316, MT6701)
hardware/
  motor_params.json  single source of truth for motor parameters
tools/
  gen_motor_params.py  JSON -> C header, runs before each build
  SimpleFOCScope/      PC-side scope (submodule)
third_party/
  Arduino-FOC/         SimpleFOC fork (submodule)
plans/           mechanical plans
cad/             parametric CAD (build123d) — see the CAD skill
```

## Build and flash

```sh
pio run -d firmware/microspora-bringup
tools/flash-microspora.sh          # board must be in DFU: BOOT, tap RESET, release BOOT
```

Serial is 250000 baud. Use `tools/SimpleFOCScope/.venv/bin/python`; the system
python lacks pyserial.

## Test modes

`TEST_MODE` at the top of `firmware/microspora-bringup/src/main.cpp`:

| Mode | Purpose |
|---|---|
| `MODE_BLINK` | board alive |
| `MODE_VSENS` | bus divider |
| `MODE_ENCODER` | MT6701 angle |
| `MODE_OPENLOOP` | phases, current polarity |
| `MODE_CURRENT` | closed-loop current |
| `MODE_STATIC` | fixed vector |
| `MODE_IDENT_R` | R and inverter error sweep |
| `MODE_CHARACTERISE` | SimpleFOC R/L identification |
| `MODE_WEB` | Commander for the SimpleFOC WebController |

## Motor set (ordered)

| Motor | R_line | Kt | Pole pairs | Mass | Use |
|---|---|---|---|---|---|
| DM5015 | 13.5 Ω | 0.47 | 14 | 174 g | knee, hip pitch |
| DM5010 | 10.3 Ω (measured) | 0.27 | 14 | 135 g | ankle |

At 12 V: DM5015 ≈ 0.42 N·m, DM5010 ≈ 0.32 N·m. Both are bare motors: add a
diametric magnet and use the MicroSpora's MT6701.

## Conventions

- Never hard-code motor numbers in firmware; edit `hardware/motor_params.json`
  and let `tools/gen_motor_params.py` generate the header.
- The belt is a mass-placement device: keep motors proximal.
- The knee and hip pitch use 3:1 belts; the ankle uses 4:1 plus the 4-bar.
- Record measured values with provenance (`bench`, `in_situ`, `datasheet`).

## Key docs

- `docs/bringup-microspora.md` — wiring, DFU, the three defects that blocked
  rotation, the official 6-PWM configuration.
- `docs/motor-identification.md` — R/L/ψ/J protocol.
- `docs/wiring-feather-drv8316.md` — the known-working Feather reference.
