"""Phase 1 fixture: drone motor test stand.

A table-mounted stand that holds a 5010 outrunner with the shaft horizontal.
The motor bolts to the front of a vertical plate, the magnet carrier bolts to
the rotor, and a sensor bracket in front of the motor faces the magnet.

Assembly, front (-Y) to back (+Y):

    sensor plate | 1.5 mm gap | magnet carrier | rotor | motor | motor plate | base

The motor is a reference model (``motor_5010.py``), not a printed part.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from build123d import Box, Cylinder, Part, Pos, Rot

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from export import export  # noqa: E402
from fixtures import motor_5010  # noqa: E402


@dataclass(frozen=True)
class DroneStand:
    # Base: the table mount.
    base_w: float = 100.0
    base_d: float = 90.0
    base_t: float = 6.0
    clamp_slot_w: float = 20.0
    clamp_slot_d: float = 8.0
    table_screw_d: float = 4.5  # M4 clearance
    table_screw_inset: float = 8.0

    # Motor plate: vertical, motor bolts to the front (-Y) face.
    motor_plate_w: float = 50.0
    motor_plate_h: float = 50.0
    motor_plate_t: float = 6.0
    motor_pitch_x: float = 19.0
    motor_pitch_y: float = 16.0
    motor_hole_d: float = 3.4  # M3 clearance
    motor_bore: float = 12.0  # cable pass-through

    # Sensor bracket: in front of the motor, facing back (+Y).
    sensor_plate_w: float = 25.0
    sensor_plate_h: float = 25.0
    sensor_plate_t: float = 3.0
    sensor_pocket_w: float = 15.0
    sensor_pocket_h: float = 17.0
    sensor_pocket_d: float = 1.8  # 1.6 mm PCB + 0.2 mm
    sensor_gap: float = 1.5  # magnet face to board face
    sensor_post_w: float = 10.0

    # Magnet carrier: bolts to the rotor (12 x 12 mm).
    rotor_pitch: float = 12.0
    rotor_hole_d: float = 2.4  # M2 clearance
    rotor_d: float = 20.0
    carrier_t: float = 4.0
    magnet_d: float = 6.2  # 6 mm magnet + 0.2 mm
    magnet_t: float = 2.25  # 2.15 mm magnet + 0.1 mm
    shaft_d: float = 4.0

    # Motor envelope: mounting face to rotor face (5010 is 26 mm overall).
    motor_height: float = 26.0


def build(cfg: DroneStand = DroneStand()) -> tuple[Part, Part]:
    # Base: clamp slot at the back, four table screws.
    base = Pos(0, 0, cfg.base_t / 2) * Box(cfg.base_w, cfg.base_d, cfg.base_t)
    base -= Pos(0, cfg.base_d / 2 - 10, cfg.base_t / 2) * Box(
        cfg.clamp_slot_w, cfg.clamp_slot_d, cfg.base_t + 2
    )
    sx = cfg.base_w / 2 - cfg.table_screw_inset
    sy = cfg.base_d / 2 - cfg.table_screw_inset
    for x in (-sx, sx):
        for y in (-sy, sy):
            base -= Pos(x, y, cfg.base_t / 2) * Cylinder(
                cfg.table_screw_d / 2, cfg.base_t + 2
            )

    # Motor plate: vertical, front face at y = -motor_plate_t / 2.
    plate_z = cfg.base_t + cfg.motor_plate_h / 2
    motor_plate = Box(cfg.motor_plate_w, cfg.motor_plate_t, cfg.motor_plate_h)
    for x in (-cfg.motor_pitch_x / 2, cfg.motor_pitch_x / 2):
        for z in (-cfg.motor_pitch_y / 2, cfg.motor_pitch_y / 2):
            motor_plate -= Pos(x, 0, z) * Cylinder(
                cfg.motor_hole_d / 2, cfg.motor_plate_t + 2
            )
    motor_plate -= Cylinder(cfg.motor_bore / 2, cfg.motor_plate_t + 2)
    motor_plate = Pos(0, 0, plate_z) * motor_plate

    # Gussets on the back of the plate, clear of the motor.
    gusset = Box(6, 12, 14)
    for x in (-20, 20):
        motor_plate += Pos(x, 3 + 6, cfg.base_t + 7) * gusset

    # Sensor bracket: a post from the base, in front of the motor, holding a
    # plate that faces back (+Y) toward the magnet.
    rotor_y = -cfg.motor_plate_t / 2 - cfg.motor_height
    carrier_front = rotor_y - cfg.carrier_t
    sensor_face = carrier_front - cfg.sensor_gap
    sensor_plate_y = sensor_face - cfg.sensor_plate_t / 2

    sensor_plate = Box(cfg.sensor_plate_w, cfg.sensor_plate_t, cfg.sensor_plate_h)
    sensor_plate -= Pos(
        0, cfg.sensor_plate_t / 2 - cfg.sensor_pocket_d / 2, 0
    ) * Box(cfg.sensor_pocket_w, cfg.sensor_pocket_d, cfg.sensor_pocket_h)
    sensor_plate = Pos(0, sensor_plate_y, plate_z) * sensor_plate

    post_h = plate_z - cfg.sensor_plate_h / 2 - cfg.base_t
    post = Pos(0, sensor_plate_y, cfg.base_t + post_h / 2) * Box(
        cfg.sensor_post_w, cfg.sensor_plate_t, post_h
    )

    stand = base + motor_plate + sensor_plate + post

    # Magnet carrier: bolts to the rotor, magnet pocket on the front face.
    carrier = Cylinder(cfg.rotor_d / 2, cfg.carrier_t)
    for x in (-cfg.rotor_pitch / 2, cfg.rotor_pitch / 2):
        for z in (-cfg.rotor_pitch / 2, cfg.rotor_pitch / 2):
            carrier -= Pos(x, z, 0) * Cylinder(
                cfg.rotor_hole_d / 2, cfg.carrier_t + 2
            )
    carrier -= Cylinder(cfg.shaft_d / 2, cfg.carrier_t + 2)
    carrier -= Pos(0, 0, cfg.carrier_t / 2 - cfg.magnet_t / 2) * Cylinder(
        cfg.magnet_d / 2, cfg.magnet_t + 2
    )
    carrier = Rot(90, 0, 0) * carrier
    carrier = Pos(0, rotor_y - cfg.carrier_t / 2, plate_z) * carrier

    return stand, carrier


def sensor_board(cfg: DroneStand = DroneStand()) -> Part:
    """Reference AS5048A board, sitting in the sensor pocket."""
    board = Box(cfg.sensor_pocket_w - 0.2, 1.6, cfg.sensor_pocket_h - 0.2)
    chip = Box(3.0, 0.8, 3.0)
    board += Pos(0, 0.8 + 0.4, 0) * chip
    return board


def assembly(cfg: DroneStand = DroneStand()) -> Part:
    """Stand + motor + carrier + sensor board, in their working positions."""
    stand, carrier = build(cfg)
    plate_z = cfg.base_t + cfg.motor_plate_h / 2

    motor = motor_5010.build()
    motor = Pos(0, -cfg.motor_plate_t / 2, plate_z) * motor

    rotor_y = -cfg.motor_plate_t / 2 - cfg.motor_height
    sensor_face = rotor_y - cfg.carrier_t - cfg.sensor_gap
    board = Pos(0, sensor_face - 0.8, plate_z) * sensor_board(cfg)

    return stand + motor + carrier + board


def parts() -> dict[str, Part]:
    """Named parts, for the viewer and the exporter."""
    stand, carrier = build()
    return {
        "drone_stand": stand,
        "drone_magnet_carrier": carrier,
        "drone_stand_assembly": assembly(),
    }


def main() -> None:
    for name, part in parts().items():
        export(part, name)


if __name__ == "__main__":
    main()
