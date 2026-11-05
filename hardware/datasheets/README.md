# Datasheets

Reference documents for the parts on the robot. Keep the original PDF and
record where it came from, so a dimension can always be traced back.

| File | Part | Source |
|---|---|---|
| `5010-360kv-brushless-motor.pdf` | 5010 360KV outrunner | <https://robu-prod-media.s3.ap-south-1.amazonaws.com/uploads/2017/10/5010-360KV-High-Torque-Brushless-Motor-for-Drone.pdf> |

## 5010 360KV

| Spec | Value |
|---|---|
| Configuration | 12N14P |
| Motor size | Φ50 × 26 mm |
| Stator boss | **Ø25 × 10 mm** (the plate sits on its end face) |
| Mounting face to rotor face | 21.3 mm |
| Shaft (out) | 4 mm |
| Shaft (in) | 5 mm |
| Weight | 92 g |
| Stator holes | 4 × M3: Ø19 pair (vertical) + Ø16 pair (horizontal) |
| Rotor holes | 4 × M3 on a Ø12 bolt circle |
| Cable | 40 cm |

The CAD model in `cad/fixtures/motor_5010.py` uses the 21.3 mm mounting face
to rotor face, the Ø19/Ø16 stator cross, and the Ø12 rotor circle.
