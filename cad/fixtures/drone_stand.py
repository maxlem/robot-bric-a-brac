"""Phase 1 fixture: drone motor test stand.

A table-mounted stand for a 5010 outrunner with two encoder interfaces:

- **Stator side (back)**: MicroSpora behind a wall, magnet on the through-shaft.
  This is the main encoder, on the same side as the motor wires.
- **Rotor side (front)**: AS5048A breakout on a bracket, magnet on the rotor.
  This is the output encoder for the Feather bring-up.

Assembly, front (-Y) to back (+Y):

    AS5048A | gap | magnet B | carrier | rotor ‖ stator ‖ 25 mm head
            | magnet A | wall | MicroSpora

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
    motor_pitch_19: float = 19.0  # vertical pair
    motor_pitch_16: float = 16.0  # horizontal pair
    motor_hole_d: float = 3.4  # M3 clearance
    motor_bore: float = 12.0  # through-shaft clearance

    # Stator-side encoder: MicroSpora behind a wall, magnet on the shaft.
    back_wall_t: float = 3.0
    back_wall_hole: float = 8.0
    microspora_w: float = 33.0
    microspora_h: float = 34.0
    microspora_pitch_x: float = 28.0
    microspora_pitch_y: float = 29.0
    microspora_hole_d: float = 2.4  # M2 clearance
    microspora_offset_x: float = 0.0
    microspora_offset_y: float = 0.0

    # Rotor-side encoder: AS5048A on a front bracket.
    as5048a_plate_w: float = 40.0
    as5048a_plate_h: float = 40.0
    as5048a_plate_t: float = 5.0
    as5048a_pocket_w: float = 15.0
    as5048a_pocket_h: float = 17.0
    as5048a_pocket_d: float = 1.8
    as5048a_gap: float = 3.5  # magnet face to plate face
    as5048a_post_w: float = 20.0
    as5048a_post_d: float = 10.0

    # Magnet carrier (rotor side) and magnet holder (stator side).
    rotor_pitch: float = 12.0
    rotor_hole_d: float = 2.4  # M2 clearance
    rotor_d: float = 20.0
    carrier_t: float = 4.0
    holder_d: float = 10.0
    holder_t: float = 2.5
    magnet_d: float = 6.2  # pocket: 6 mm magnet + 0.2 mm
    magnet_t: float = 2.25  # pocket: 2.15 mm magnet + 0.1 mm
    magnet_actual_d: float = 6.0
    magnet_actual_t: float = 2.15
    shaft_d: float = 4.0

    # Motor envelope: mounting face to rotor face (21.3 mm on the drawing).
    motor_height: float = 21.3


def build(cfg: DroneStand = DroneStand()) -> tuple[Part, Part, Part]:
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
    # Stator holes: Ø19 pair vertical, Ø16 pair horizontal. The plate is
    # vertical, so the holes run along Y.
    for x, z in (
        (0, cfg.motor_pitch_19 / 2),
        (0, -cfg.motor_pitch_19 / 2),
        (cfg.motor_pitch_16 / 2, 0),
        (-cfg.motor_pitch_16 / 2, 0),
    ):
        motor_plate -= Pos(x, 0, z) * Rot(90, 0, 0) * Cylinder(
            cfg.motor_hole_d / 2, cfg.motor_plate_t + 2
        )
    motor_plate -= Rot(90, 0, 0) * Cylinder(
        cfg.motor_bore / 2, cfg.motor_plate_t + 2
    )
    motor_plate = Pos(0, 0, plate_z) * motor_plate

    # Gussets on the back of the plate, clear of the motor.
    gusset = Box(6, 12, 14)
    for x in (-20, 20):
        motor_plate += Pos(x, 3 + 6, cfg.base_t + 7) * gusset

    # Standoffs from the motor plate to the back wall.
    for x in (-20, 20):
        for z in (-20, 20):
            standoff = Rot(90, 0, 0) * Cylinder(5, cfg.holder_t)
            motor_plate += Pos(
                x, cfg.motor_plate_t / 2 + cfg.holder_t / 2, plate_z + z
            ) * standoff

    # Back wall: separates the magnet from the MicroSpora.
    wall_y = cfg.motor_plate_t / 2 + cfg.holder_t + cfg.back_wall_t / 2
    back_wall = Box(cfg.motor_plate_w, cfg.back_wall_t, cfg.motor_plate_h)
    back_wall -= Rot(90, 0, 0) * Cylinder(
        cfg.back_wall_hole / 2, cfg.back_wall_t + 2
    )
    for x in (-cfg.microspora_pitch_x / 2, cfg.microspora_pitch_x / 2):
        for z in (-cfg.microspora_pitch_y / 2, cfg.microspora_pitch_y / 2):
            back_wall -= Pos(x, 0, z) * Rot(90, 0, 0) * Cylinder(
                cfg.microspora_hole_d / 2, cfg.back_wall_t + 2
            )
    back_wall = Pos(0, wall_y, plate_z) * back_wall

    # Rotor-side bracket: a post from the base, in front of the motor.
    rotor_y = -cfg.motor_plate_t / 2 - cfg.motor_height
    carrier_front = rotor_y - cfg.carrier_t
    sensor_face = carrier_front - cfg.as5048a_gap
    sensor_plate_y = sensor_face - cfg.as5048a_plate_t / 2

    sensor_plate = Box(cfg.as5048a_plate_w, cfg.as5048a_plate_t, cfg.as5048a_plate_h)
    sensor_plate -= Pos(
        0, cfg.as5048a_plate_t / 2 - cfg.as5048a_pocket_d / 2, 0
    ) * Box(cfg.as5048a_pocket_w, cfg.as5048a_pocket_d, cfg.as5048a_pocket_h)
    sensor_plate = Pos(0, sensor_plate_y, plate_z) * sensor_plate

    post_h = plate_z - cfg.as5048a_plate_h / 2 - cfg.base_t
    post = Pos(
        0,
        sensor_plate_y - cfg.as5048a_plate_t / 2 + cfg.as5048a_post_d / 2,
        cfg.base_t + post_h / 2,
    ) * Box(cfg.as5048a_post_w, cfg.as5048a_post_d, post_h)

    stand = base + motor_plate + back_wall + sensor_plate + post

    # Rotor-side magnet carrier: bolts to the rotor, magnet on the front.
    carrier = Cylinder(cfg.rotor_d / 2, cfg.carrier_t)
    for x, z in (
        (0, cfg.rotor_pitch / 2),
        (0, -cfg.rotor_pitch / 2),
        (cfg.rotor_pitch / 2, 0),
        (-cfg.rotor_pitch / 2, 0),
    ):
        carrier -= Pos(x, z, 0) * Cylinder(
            cfg.rotor_hole_d / 2, cfg.carrier_t + 2
        )
    carrier -= Cylinder(cfg.shaft_d / 2, cfg.carrier_t + 2)
    carrier -= Pos(0, 0, cfg.carrier_t / 2 - cfg.magnet_t / 2 + 0.5) * Cylinder(
        cfg.magnet_d / 2, cfg.magnet_t + 1
    )
    carrier = Rot(90, 0, 0) * carrier
    carrier = Pos(0, rotor_y - cfg.carrier_t / 2, plate_z) * carrier

    # Stator-side magnet holder: sits on the through-shaft, magnet on the
    # back face, facing the MicroSpora through the wall.
    holder = Cylinder(cfg.holder_d / 2, cfg.holder_t)
    holder -= Cylinder(cfg.shaft_d / 2, cfg.holder_t + 2)
    holder -= Pos(0, 0, cfg.holder_t / 2 - cfg.magnet_t / 2 + 0.5) * Cylinder(
        cfg.magnet_d / 2, cfg.magnet_t + 1
    )
    holder = Rot(90, 0, 0) * holder
    holder = Pos(0, cfg.motor_plate_t / 2 + cfg.holder_t / 2, plate_z) * holder

    return stand, carrier, holder


def sensor_board_as5048a(cfg: DroneStand = DroneStand()) -> Part:
    """Reference AS5048A board, sitting in the front pocket."""
    board = Box(cfg.as5048a_pocket_w - 0.2, 1.6, cfg.as5048a_pocket_h - 0.2)
    chip = Box(3.0, 0.8, 3.0)
    board += Pos(0, 0.8 + 0.4, 0) * chip
    return board


def sensor_board_microspora(cfg: DroneStand = DroneStand()) -> Part:
    """Reference MicroSpora board, on the back wall."""
    board = Box(cfg.microspora_w, 1.6, cfg.microspora_h)
    chip = Box(3.0, 0.8, 3.0)
    board += Pos(
        cfg.microspora_offset_x, -0.8 - 0.4, cfg.microspora_offset_y
    ) * chip
    return board


def magnet(cfg: DroneStand = DroneStand()) -> Part:
    """Reference diametric magnet."""
    return Rot(90, 0, 0) * Cylinder(cfg.magnet_actual_d / 2, cfg.magnet_actual_t)


def assembly_parts(
    cfg: DroneStand = DroneStand(), sensor: str = "microspora"
) -> list[tuple[str, Part, str]]:
    """Stand, motor, and the chosen encoder, in their working positions."""
    stand, carrier, holder = build(cfg)
    plate_z = cfg.base_t + cfg.motor_plate_h / 2

    motor = Pos(0, -cfg.motor_plate_t / 2, plate_z) * motor_5010.build()

    parts: list[tuple[str, Part, str]] = [
        ("stand", stand, "#8fa8c8"),
        ("motor", motor, "#e0a060"),
    ]

    if sensor == "microspora":
        # Magnet A on the through-shaft, board on the back wall.
        magnet_y = cfg.motor_plate_t / 2 + cfg.holder_t - cfg.magnet_actual_t / 2
        wall_back = (
            cfg.motor_plate_t / 2 + cfg.holder_t + cfg.back_wall_t
        )
        parts += [
            ("holder", holder, "#7fc8a0"),
            ("magnet", Pos(0, magnet_y, plate_z) * magnet(cfg), "#c080d0"),
            (
                "microspora",
                Pos(0, wall_back + 0.8, plate_z) * sensor_board_microspora(cfg),
                "#d07070",
            ),
        ]
    else:
        # Magnet B on the rotor, board in the front bracket.
        rotor_y = -cfg.motor_plate_t / 2 - cfg.motor_height
        magnet_y = rotor_y - cfg.carrier_t + cfg.magnet_actual_t / 2
        sensor_face = rotor_y - cfg.carrier_t - cfg.as5048a_gap
        parts += [
            ("carrier", carrier, "#7fc8a0"),
            ("magnet", Pos(0, magnet_y, plate_z) * magnet(cfg), "#c080d0"),
            (
                "as5048a",
                Pos(0, sensor_face + 0.8, plate_z) * sensor_board_as5048a(cfg),
                "#d07070",
            ),
        ]

    return parts


def assemblies() -> dict[str, list[tuple[str, Part, str]]]:
    return {
        "drone_stand_microspora": assembly_parts(sensor="microspora"),
        "drone_stand_as5048a": assembly_parts(sensor="as5048a"),
    }


def parts() -> dict[str, Part]:
    """Named parts, for the viewer and the exporter."""
    stand, carrier, holder = build()
    return {
        "drone_stand": stand,
        "drone_magnet_carrier": carrier,
        "drone_magnet_holder": holder,
        "drone_magnet": magnet(),
        "drone_sensor_as5048a": sensor_board_as5048a(),
        "drone_sensor_microspora": sensor_board_microspora(),
    }


def main() -> None:
    for name, part in parts().items():
        export(part, name)


if __name__ == "__main__":
    main()
