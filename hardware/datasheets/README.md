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
| Shaft (out) | 4 mm |
| Shaft (in) | 5 mm |
| Weight | 92 g |
| Mounting | rear threaded holes, 16 mm and 19 mm spacings |
| Cable | 40 cm |

The CAD model in `cad/fixtures/motor_5010.py` uses the 26 mm overall length,
the 19 × 16 mm stator pattern, and the 12 × 12 mm rotor pattern.
