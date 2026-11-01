# Motor identification protocol

How to obtain the parameters a sensorless (InstaSPIN-style) controller needs
for a gimbal-class BLDC motor, using bench instruments plus the `motor-test`
rig. Written for the SAME51 / DRV8316 setup and portable to the STM32G4
MicroSpora boards.

The target is not "match InstaSPIN". The target is a set of numbers that are
independently validated, so that a back-EMF observer built on them has a
chance of working.

## Parameters, and why each one matters

| Symbol | Meaning | Used by | Typical sensitivity |
|---|---|---|---|
| `R_phase` | stator resistance per phase, DC, 4-wire | current loop, observer | +0.4 %/K |
| `R_total` | `R_phase` + inverter conduction | observer, voltage model | 10-20 % of total |
| `L_d`, `L_q` | inductance on each axis | current loop | falls 10-30 % at 3 A |
| `psi` | flux linkage, peak per phase | torque, back-EMF observer | the key sensorless parameter |
| `Kt` | `1.5 * pole_pairs * psi` | torque control | derived, not independent |
| `J` | rotor + load inertia | speed loop | — |
| `B`, `Tc` | viscous and Coulomb friction | speed loop, coast-down | — |
| `V_error(I, duty)` | inverter dead-time and conduction error | voltage model | 6-12 % of current at low modulation |

Everything except `psi`, `J`, `B`, `Tc`, and `V_error` can be measured on the
bench with the motor stopped. The rest must be identified while the motor
turns, which is the part that "runs and learns" about it.

## 0. Safety and setup

- Bench supply current-limited to just above the highest test current.
- Motor free to spin for every test that spins it, clamped for the hold tests.
- Start at the lowest bus voltage that works (8-12 V). Nothing here needs 24 V.
- Keep `I^2 t` small during DC tests: a winding that heats changes `R` under
  you and the change looks exactly like inverter nonlinearity.

## 1. Bench measurements (instrument only)

Do these before powering the rig.

**Resistance, per phase, 4-wire.** Probe at the phase terminals, not at the
board. Rotate the rotor to a few positions and average; variation indicates a
wye/star point issue or a damaged winding. Record ambient temperature.

**Inductance, per phase.** Small-signal value from the LCR meter. Note the
test frequency. This is the *unsaturated* value and will not match what the
current loop sees.

**`L_d` / `L_q`.** Rotate the rotor in steps of 10-15 electrical degrees with
the meter connected between two phases; the inductance will vary at twice the
electrical frequency if the motor has saliency. Record min and max. A near-flat
curve means a surface-PM motor, which rules high-frequency injection in or out
for start-up.

Record everything in the table at the end. These numbers are the anchors every
later fit is checked against.

## 2. Rig calibration

Before any identification, fix the measurement chain:

1. **Current offsets.** Zero current, all phases, average over >=1000 PWM
   periods. Repeat per session; it drifts with temperature.
2. **Current gain.** Verify against a known DC current (series resistor or
   electronic load). The DRV8316 gain is set in firmware
   (`setCurrentSenseGain`); record which one.
3. **Bus voltage scale.** Compare `VSENS` reading against a multimeter at two
   supply voltages.

If these are wrong, every subsequent number is confidently wrong.

## 3. Inverter voltage error, using `R_phase` as the reference

This is what replaces phase-voltage sensing.

Clamp the rotor (or command a fixed electrical angle) and hold a DC current.
At steady state, with no back-EMF:

```
V_applied_actual = R_phase * I
V_error          = duty * V_bus - R_phase * I
```

Sweep current in both directions at 3-4 levels, fit:

```
V_error(I) = V_offset + k * sign(I) * V_dead     (plus a small linear term)
```

The sign flip at zero current is the dead-time signature. `V_dead` should land
near `V_bus * t_dead / T_pwm`; with 25 kHz PWM and a few hundred ns of dead
time, expect tenths of a volt.

Cross-check: `R_total - R_phase` should be roughly the two conducting FET
`RDS(on)` values, about 0.2 ohm for the DRV8316. A large disagreement means
the current gain is off, not that the inverter is strange.

## 4. Inductance at operating current

Step the voltage at fixed rotor angle and fit the current rise. For
`t << L/R`:

```
L = V * dt / di
```

Better, fit the full first-order response:

```
i(t) = (V/R) * (1 - exp(-t/tau)),   tau = L/R
```

Repeat at 3-4 current levels and at several rotor angles using the encoder.
Expect the in-situ `L` to be lower than the bench value; that is saturation,
and it belongs in the table.

Sampling note: the scope link runs at 100 Hz and cannot resolve a millisecond
transient. Either fit on the MCU and stream only the result, or move the scope
to USB CDC for kilohertz streaming.

## 5. Flux linkage, `psi` (the spin test)

Ramp the open-loop electrical frequency and, at each steady-state speed, find
the voltage at which the current is minimal. Then:

```
psi = (V_q - R_total * I_q - L_q * di_q/dt) / omega_e
```

At constant speed the derivative term drops out and, with `R` and `L` already
known from sections 1 and 4, `psi` is the only unknown. That is the whole
payoff of measuring the electrical parameters first.

Cross-checks, all of which should agree within about 5 %:

1. `psi` from the fit above.
2. Encoder speed versus commanded electrical frequency: a voltage-model error
   shows up as an inconsistency between them.
3. `Kt = 1.5 * pole_pairs * psi`, compared against a measured torque (lever arm
   and a known current).
4. Datasheet `Kv`, loosely: it assumes conventions that rarely match.

Do not run this near 100 % modulation: three-shunt low-side sensing has a
blind zone there, and the voltage model is least accurate exactly where the
correction is largest.

## 6. Inertia and friction

**Inertia.** Apply a current step, measure angular acceleration from the
encoder, and use `J = Kt * delta_I / alpha`. Repeat at two or three torque
levels; a consistent `J` means `Kt` is sane.

**Friction.** Disable the bridge and let the rotor coast. Fit:

```
J * domega/dt = -B * omega - Tc
```

A fit with both terms separates viscous drag from Coulomb friction. Friction
is not constant with speed or load, so treat this as a first-order model.

## 7. Cogging (optional, later)

Rotate slowly with current control and record torque current versus electrical
angle. A 7-pole-pair motor shows 7 or 14 periods per mechanical revolution.
Useful for feed-forward later; not needed for the observer.

## Expected values for a 4108-class gimbal motor

| Parameter | Typical range | Notes |
|---|---|---|
| `R_phase` | 5-15 ohm | gimbal windings are high-resistance |
| `R_total` | `R_phase` + ~0.2 ohm | DRV8316 RDS(on), temperature dependent |
| `L` | 5-20 mH | falls with current |
| `L_d` vs `L_q` | within 10 % | surface PM: low saliency |
| `psi` | 0.005-0.02 Wb | derived from Kv if available |
| `Kt` | 0.05-0.2 N.m/A | `1.5 * 7 * psi` |
| `J` | 1e-5 to 1e-4 kg.m^2 | rotor plus wheel |

Measure, do not assume. These ranges exist only to catch a result that is
wrong by an order of magnitude.

## Recorded values

| Parameter | Bench | In situ | Temperature | Notes |
|---|---|---|---|---|
| `R_phase` A/B/C |  |  |  |  |
| `R_total` |  |  |  |  |
| `V_dead` |  |  |  |  |
| `L` at 1 A |  |  |  |  |
| `L` at 3 A |  |  |  |  |
| `L_d` / `L_q` |  |  |  |  |
| `psi` |  |  |  |  |
| `Kt` |  |  |  |  |
| `J` |  |  |  |  |
| `B` |  |  |  |  |
| `Tc` |  |  |  |  |

## Acceptance checks

Identification is done when all of these hold:

- `R_total - R_phase` matches the expected FET conduction resistance within 30 %.
- In-situ `L` is below the bench value and monotonic with current.
- `psi` agrees across the three cross-checks in section 5 within 5 %.
- `Kt` predicts torque within 10 % on a lever arm.
- `J` is consistent across torque levels.

If a check fails, fix the measurement chain (section 2) before changing the
model. Nine times out of ten the problem is a current or voltage scale, not
the physics.

## Firmware modes to implement

| Mode | Purpose |
|---|---|
| `MODE_IDENT_R` | fixed-angle DC hold, current sweep, both polarities, print fit |
| `MODE_IDENT_L` | voltage step at selected rotor angles and current levels |
| `MODE_IDENT_FLUX` | open-loop V/f ramp, steady-state sampling, print `psi` |
| `MODE_IDENT_INERT` | torque step, then coast-down, print `J`, `B`, `Tc` |
| `MODE_IDENT_PARAMS` | print the current parameter set, one line |

PC side: a script that drives the modes over the existing scope protocol,
fits, and writes the recorded-values table above.
