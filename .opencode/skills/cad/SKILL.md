---
name: Robot CAD
description: Use when designing or editing the robot's mechanical parts in Python CAD (build123d or CadQuery), including LEGO Technic interfaces, joint modules, belts, bearings, and the 4-bar ankle.
---

# Robot CAD

Parametric CAD for the biped, in Python over OpenCascade. The goal is that
changing one number in `cad/skeleton.py` regenerates every part.

## Stack

- **build123d** (preferred): `pip install build123d`. OCCT kernel, headless,
  assembly support.
- **CadQuery** (alternative): more tutorials, same kernel.
- **FreeCAD + Python** only if a GUI assembly is needed.

## File layout

```text
cad/
  skeleton.py       link lengths, joint axes, ROM, belt ratios
  lego.py           LEGO Technic hole/axle/pin helpers
  joint_module.py   motor mount + pulleys + belt + bearing housing
  links.py          thigh, shank, foot
  ankle_4bar.py     4-bar linkage geometry
  assembly.py       assemble + interference + ROM check
  export.py         STEP + STL per part
  README.md         dimensions, tolerances, print settings
```

## LEGO Technic dimensions

| Feature | Dimension |
|---|---|
| Hole diameter | 4.8 mm |
| Axle cross | 4.8 mm |
| Hole pitch | 8.0 mm |
| Beam thickness | 3.2 mm (plate) / 9.6 mm (beam) |
| Friction pin length | 6.4 mm |
| Printed axle hole | 4.9–5.0 mm press, 5.1 mm slip |
| Printed pin hole | 4.8–4.9 mm |

## Printing tolerances

- Sliding fit: 0.2 mm clearance.
- Press fit: 0.1 mm.
- Minimum wall: 1.2 mm (3 perimeters at 0.4 mm).
- Infill: 40–60 % links, 80–100 % bearing housings.
- Print bearing bores vertical so layers are perpendicular to the load.
- Heat-set M3 inserts for motor mounts.

## Joint module

The knee and hip pitch share one module:

- DM5015 mount (bolt pattern from the datasheet).
- 3:1 belt: motor pulley, joint pulley, slotted tensioner.
- 6805 bearing (25 × 37 × 7 mm) as the joint bearing.
- Encoder magnet mount on the joint shaft, centred on the MT6701.

The ankle uses a 4:1 belt plus the 4-bar, which adds a 1.5–2:1 torque
advantage at the foot.

## Reference projects

- ODRI Solo / Solo8 — belt-driven BLDC legs, open CAD.
- Poppy Project — 3D-printed humanoid.
- Pupper V3 — 3D-printed quadruped brackets.

## Rules

- Read `cad/skeleton.py` first; never hard-code a link length in a part file.
- Check interference and range of motion before exporting.
- Print and test one joint module before the full leg.
- Record the print orientation and tolerances in `cad/README.md`.
