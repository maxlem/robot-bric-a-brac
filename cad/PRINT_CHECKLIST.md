# Before the first print

Work top to bottom. Do not slice until every measurement is confirmed and every
CAD check passes.

## 1. Measurements

### Drone motor (Phase 1, #13)

- [ ] Stator holes: **4 × M3, Ø19 pair (vertical) + Ø16 pair (horizontal)**
- [ ] Rotor holes: **4 × M2 on a Ø12 bolt circle**
- [ ] Shaft diameter: **4 mm**
- [ ] Magnet: **6 mm × 2.15 mm**
- [ ] Mounting face to rotor face: **21.3 mm**
- [ ] Cable exit direction (sets the plate orientation)

### AS5048A board (Phase 1, #13, rotor side)

- [ ] PCB outline (assumed 15 × 17 mm)
- [ ] Mounting hole pattern and diameter
- [ ] Connector position and height
- [ ] Magnet-to-sensor gap: 0.5–3 mm (0.9 mm in the model)

### MicroSpora (Phase 1, #13, stator side)

- [ ] Board outline: **33 × 34 mm**
- [ ] Mounting hole pattern and diameter
- [ ] MT6701 position relative to the board centre
- [ ] USB and connector clearance
- [ ] Magnet-to-sensor gap: 0.5–3 mm (2.2 mm in the model)

### DM5010 (Phase 1, #14)

- [ ] Mounting holes: **4 × M2.5 on a 20.4 mm pattern**
- [ ] Bore: **8.1 mm**
- [ ] Shaft / rotor face height

### Belt (Phase 2, #15)

- [ ] Pitch: GT3 3 mm (or GT2 2 mm)
- [ ] Width: 9 mm
- [ ] Pulley teeth: 20T / 60T
- [ ] Center distance and belt length

## 2. CAD checks

- [ ] Every hole has clearance: 0.2 mm sliding, 0.1 mm press
- [ ] Minimum wall ≥ 1.2 mm
- [ ] No overhang > 45° without support
- [ ] Bearing bore prints vertical
- [ ] Magnet pocket: 6.2 mm × 2.25 mm
- [ ] Sensor gap 0.5–3 mm
- [ ] Motor and sensor do not collide through the assembly
- [ ] Belt path clears the frame
- [ ] STEP and STL exported for every part
- [ ] Part is oriented for strength, not just for printing

## 3. Slicer

- [ ] Orientation: bearing bores vertical, motor plate flat on the bed
- [ ] Layer height: 0.2 mm (0.12 mm for pulley teeth)
- [ ] Perimeters: 4
- [ ] Infill: 40–60 % links, 80–100 % bearing housings
- [ ] Supports: only where needed; none inside bearing bores or magnet pockets
- [ ] Brim for tall, thin parts
- [ ] Check the first layer preview

## 4. Printer

- [ ] Bed level and Z offset
- [ ] Filament dry (PETG especially)
- [ ] Nozzle clean, no partial clog
- [ ] First-layer test patch
- [ ] Spool has enough filament for the part

## 5. Post-print

- [ ] Test-fit the motor, sensor, magnet, and bearing **before** gluing
- [ ] Heat-set inserts: M3 motor mounts, M2.5 DM5010, M2 MicroSpora
- [ ] Magnet sits flush and centred; check the gap with a 1.5 mm shim
- [ ] Bearing seats without binding
- [ ] Belt tension: ~3 mm deflection at mid-span
- [ ] No cracks at the insert bosses

## 6. Sign-off

| Part | Measured | CAD | Sliced | Printed | Fits |
|---|---|---|---|---|---|
| Drone stand | ☐ | ☐ | ☐ | ☐ | ☐ |
| Drone magnet carrier | ☐ | ☐ | ☐ | ☐ | ☐ |
| DM5010 mount | ☐ | ☐ | ☐ | ☐ | ☐ |
| DM5010 magnet carrier | ☐ | ☐ | ☐ | ☐ | ☐ |
| Belt rig | ☐ | ☐ | ☐ | ☐ | ☐ |
