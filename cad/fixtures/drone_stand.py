"""Phase 1 fixture: drone motor test stand.

A table-mounted stand that holds a drone motor (4108/5208 class) with the
shaft horizontal, a magnet carrier on the shaft, and a bracket for an
AS5047P/AS5048A sensor facing the magnet.

Dimensions are first-draft. Confirm the motor bolt pattern, the shaft
diameter, and the sensor board size before printing.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from build123d import Box, Cylinder, Part, Pos

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from export import export  # noqa: E402


@dataclass(frozen=True)
class DroneStand:
    # Base: the table mount. A clamp slot plus four screw holes.
    base_w: float = 100.0
    base_d: float = 70.0
    base_t: float = 6.0
    clamp_slot_w: float = 20.0
    clamp_slot_d: float = 8.0
    table_screw_d: float = 4.5  # M4 clearance
    table_screw_inset: float = 8.0

    # Riser and motor plate.
    riser_w: float = 20.0
    riser_d: float = 20.0
    riser_h: float = 40.0
    motor_plate_w: float = 50.0
    motor_plate_h: float = 50.0
    motor_plate_t: float = 6.0

    # Motor interface: stator-side pattern 19 x 16 mm, M3.
    # Swap x/y if the motor's cable exit needs the other orientation.
    motor_pitch_x: float = 19.0
    motor_pitch_y: float = 16.0
    motor_hole_d: float = 3.4  # M3 clearance
    motor_bore: float = 12.0

    # Sensor bracket.
    sensor_plate_w: float = 25.0
    sensor_plate_h: float = 25.0
    sensor_plate_t: float = 3.0
    sensor_pocket_w: float = 15.0
    sensor_pocket_h: float = 17.0
    sensor_pocket_d: float = 1.5
    sensor_clearance: float = 1.5  # magnet face to sensor face

    # Magnet carrier: bolts to the rotor side (12 x 12 mm pattern).
    rotor_pitch: float = 12.0
    rotor_hole_d: float = 2.4  # M2 clearance
    rotor_d: float = 20.0
    carrier_t: float = 4.0
    magnet_d: float = 6.2
    magnet_t: float = 2.5
    shaft_d: float = 4.0


def build(cfg: DroneStand = DroneStand()) -> tuple[Part, Part]:
    # Base: clamp slot plus four table screws.
    base = Pos(0, 0, cfg.base_t / 2) * Box(cfg.base_w, cfg.base_d, cfg.base_t)
    base -= Pos(0, -cfg.base_d / 2 + 10, cfg.base_t / 2) * Box(
        cfg.clamp_slot_w, cfg.clamp_slot_d, cfg.base_t + 2
    )
    sx = cfg.base_w / 2 - cfg.table_screw_inset
    sy = cfg.base_d / 2 - cfg.table_screw_inset
    for x in (-sx, sx):
        for y in (-sy, sy):
            base -= Pos(x, y, cfg.base_t / 2) * Cylinder(
                cfg.table_screw_d / 2, cfg.base_t + 2
            )

    # Riser at the back.
    riser_y = cfg.base_d / 2 - cfg.riser_d / 2
    riser = Pos(0, riser_y, cfg.base_t + cfg.riser_h / 2) * Box(
        cfg.riser_w, cfg.riser_d, cfg.riser_h
    )

    # Vertical motor plate at the top of the riser, facing -Y.
    plate_y = riser_y - cfg.riser_d / 2 - cfg.motor_plate_t / 2
    plate_z = cfg.base_t + cfg.riser_h - cfg.motor_plate_h / 2
    motor_plate = Box(cfg.motor_plate_w, cfg.motor_plate_t, cfg.motor_plate_h)
    for x in (-cfg.motor_pitch_x / 2, cfg.motor_pitch_x / 2):
        for z in (-cfg.motor_pitch_y / 2, cfg.motor_pitch_y / 2):
            motor_plate -= Pos(x, 0, z) * Cylinder(cfg.motor_hole_d / 2, cfg.motor_plate_t + 2)
    motor_plate -= Cylinder(cfg.motor_bore / 2, cfg.motor_plate_t + 2)
    motor_plate = Pos(0, plate_y, plate_z) * motor_plate

    # Sensor plate behind the motor, facing -Y, on a post. The carrier sits
    # between the motor plate and the sensor, so the sensor clears it.
    sensor_y = (
        plate_y
        + cfg.motor_plate_t / 2
        + cfg.carrier_t
        + cfg.sensor_clearance
        + cfg.sensor_plate_t / 2
    )
    sensor_plate = Box(cfg.sensor_plate_w, cfg.sensor_plate_t, cfg.sensor_plate_h)
    sensor_plate -= Pos(0, -cfg.sensor_plate_t / 2, 0) * Box(
        cfg.sensor_pocket_w, cfg.sensor_pocket_d, cfg.sensor_pocket_h
    )
    sensor_plate = Pos(0, sensor_y, plate_z) * sensor_plate

    post_h = plate_z - cfg.base_t
    post = Pos(0, sensor_y, cfg.base_t + post_h / 2) * Box(10, 10, post_h)

    stand = base + riser + motor_plate + sensor_plate + post

    # Magnet carrier: bolts to the rotor side (12 x 12 mm), holds the magnet
    # on the sensor side, and clears the shaft.
    carrier = Cylinder(cfg.rotor_d / 2, cfg.carrier_t)
    for x in (-cfg.rotor_pitch / 2, cfg.rotor_pitch / 2):
        for y in (-cfg.rotor_pitch / 2, cfg.rotor_pitch / 2):
            carrier -= Pos(x, y, 0) * Cylinder(cfg.rotor_hole_d / 2, cfg.carrier_t + 2)
    carrier -= Cylinder(cfg.shaft_d / 2, cfg.carrier_t + 2)
    carrier -= Pos(0, 0, cfg.carrier_t / 2 - cfg.magnet_t / 2) * Cylinder(
        cfg.magnet_d / 2, cfg.magnet_t + 2
    )

    return stand, carrier


def main() -> None:
    stand, carrier = build()
    export(stand, "drone_stand")
    export(carrier, "drone_magnet_carrier")


if __name__ == "__main__":
    main()
