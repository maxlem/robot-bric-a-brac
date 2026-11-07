# Datasheets

Reference documents for the parts on the robot. Keep the original PDF and
record where it came from, so a dimension can always be traced back.

| File | Part | Source |
|---|---|---|
| `5010-360kv-brushless-motor.pdf` | Flycat 5010 360KV outrunner | <https://robu-prod-media.s3.ap-south-1.amazonaws.com/uploads/2017/10/5010-360KV-High-Torque-Brushless-Motor-for-Drone.pdf> / <https://www.flyrobo.in/5010-360kv-high-torque-brushless-motor> |

## Flycat 5010 360KV

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

The CAD model in `cad/fixtures/flycat_5010.py` uses the 21.3 mm mounting face
to rotor face, the Ø19/Ø16 stator cross, and the Ø12 rotor circle.

## DM5010 + BGC-CAN-DRV (`25150101`)

| Spec | Value |
|---|---|
| Product page | <http://shop.smc-powers.com/DM5010-BGC-DRV.html> |
| Drawing | <http://shop.smc-powers.com/image/data/SMC/DM5010D-12.jpg> |
| Configuration | 24N28P (14 pole pairs) |
| Outer envelope | **Ø49.0 × 28.90 mm** |
| Hollow slip-ring bore | **Ø12.7 mm** through-hole |
| Stator / rear cover holes | 4 × M2.5 on a **20.0 × 20.0 mm** square |
| Rotor / front face holes | 4 × M3 on a **Ø25.0 mm** bolt circle |
| Weight | 131–135 g |

The CAD model in `cad/fixtures/dm5010.py` (`DM5010`) models the Ø49.0 × 28.90 mm
housing, the Ø12.7 mm slip-ring through-bore, the 20 × 20 mm M2.5 stator pattern,
the Ø25 mm M3 rotor bolt circle, and the side BGC-CAN-DRV connector pocket.

## SMC Powers Motor Inventory & Specifications

Ordered / owned motors from [SMC Powers](http://shop.smc-powers.com/) for the biped joints:

| Motor | SKU | Qty | Type | Encoder | Unit Price | Total | Source |
|---|---|---|---|---|---|---|---|
| **PM5225 + AS5048A** | `2552252` | 4 | Housed outrunner | Built-in AS5048A (PWM / SPI) | $47.41 | $189.64 | <http://shop.smc-powers.com/PM5225.html> |
| **FL-OR5225** | `20052250` | 2 | Frameless outrunner | External (MT6701 / AS5048A) | $21.80 | $43.60 | <http://shop.smc-powers.com/Frameless-OR5225.html> |
| **DM5015** | `25150151` | 2 | Housed gimbal (Ø12.7 mm bore) | External (MT6701 / AS5048A) | $36.00 | $72.00 | <http://shop.smc-powers.com/Motor/For-Gimbal-Motor> |
| **DM5010** | `25150101` | 2 *(1 owned + 1 ordered)* | Housed gimbal (Ø12.7 mm bore) | External (MT6701 / AS5048A) | $31.50 | $63.00 | <http://shop.smc-powers.com/DM5010-BGC-DRV.html> |

### Electrical & Mechanical Specifications

| Parameter | Unit | DM5010 (`4310`) | DM5015 (`4315`) | FL-OR5225 | PM5225 |
|---|---|---|---|---|---|
| Stator size | mm | 43 × 10 | 43 × 15 | 52 × 25 | 52 × 25 |
| Nominal voltage | V | 16–24 | 16–24 | 24 | 24 |
| Nominal current | A | 0.79 | 0.59 | **1.28** | **1.28** |
| Stall / peak current (rated V) | A | 1.20 | 0.90 | **1.94** | **1.94** |
| Max current @ 12 V bus | A | ~1.17 | ~0.89 | **~1.02** | **~1.02** |
| Line-to-line resistance ($R$) | Ω | 10.8 *(10.3 meas.)* | 13.5–15.2 | 11.8 | 11.8 |
| Inductance ($L$) | mH | 4.74 | 6.56 | 11.31 | 11.31 |
| Torque constant ($K_t$) | N·m/A | 0.27 | 0.47 | **0.98** | **0.98** |
| Speed constant ($K_v$) | rpm/V | 33 | 23 | 14 | 14 |
| Nominal torque (rated V) | N·m | 0.21 | 0.28 | **1.26** | **1.26** |
| Stall / peak torque (rated V) | N·m | 0.32 | 0.42 | **1.90** | **1.90** |
| Stall torque @ 12 V bus | N·m | 0.32 | 0.42 | **1.00** | **1.00** |
| Nominal / max speed (rated V) | rpm | 585 / 875 | 425 / 608 | 313 / 455 | 313 / 455 |
| Rotor inertia | g·cm² | 202 | 268 | 933 | 933 |
| Pole pairs | — | 14 | 14 | 11 *(or 14, verify)* | 11 *(or 14, verify)* |
| Mass | g | 135 | 174 | ~250 *(bare)* | 330 |

