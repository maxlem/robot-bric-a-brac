"""Phase 1 fixture: L-shaped drone motor test stand.

A table-mounted L-bracket stand for a 5010 outrunner with a stator-side
MicroSpora encoder:

- **Rotor side (front, -Y)**: completely open and free of obstacles.
- **Stator side (back, +Y)**: MicroSpora recessed in the vertical wall, with
  the 3D-printed magnet holder on the 1.50 mm rear shaft stub and the table
  base extending toward +Y.

The motor is a reference model (``motor_5010.py``), not a printed part.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from build123d import Box, Compound, Cylinder, Part, Pos, Rot

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from export import export  # noqa: E402
from fixtures import motor_5010  # noqa: E402
from reference import microspora  # noqa: E402


@dataclass(frozen=True)
class DroneStand:
    # Base: extends toward +Y behind the motor wall, with a front (-Y) lip
    # under the stator to spread the motor's weight and prevent forward tipping.
    base_w: float = 100.0
    base_d: float = 75.0
    base_lip: float = 15.0  # -Y lip in front of the motor wall
    base_t: float = 6.0
    clamp_slot_w: float = 20.0
    clamp_slot_d: float = 8.0
    table_screw_d: float = 4.5  # M4 clearance
    table_screw_inset: float = 8.0

    # Motor plate: vertical front wall of the L-bracket, motor on -Y face.
    # 54 mm tall (shaft at Z=33 mm) so the Ø52 mm rotor clears the 6 mm base lip.
    motor_plate_w: float = 50.0
    motor_plate_h: float = 54.0
    motor_plate_t: float = 7.5
    motor_pitch_19: float = 19.0  # vertical pair
    motor_pitch_16: float = 16.0  # horizontal pair
    motor_hole_d: float = 3.4  # M3 clearance (ISO 273 medium)
    motor_cbore_d: float = 6.0  # M3 socket head counterbore (DIN 974-1 for Ø5.5 mm head)
    motor_cbore_d_below_recess: float = 3.2  # 3.0 mm head height + 0.2 mm recess margin
    motor_bore: float = 10.6  # clears Ø9.6 mm magnet holder with 0.5 mm radial gap

    # Stator-side encoder: MicroSpora in a recess on the back of the plate.
    # The PCB has 3 corner fixation slots (top-left, top-right, bottom-right)
    # whose inner round ends (Ø3.14 mm) sit on a 21.1 x 21.1 mm square around U8.
    microspora_w: float = 33.0
    microspora_h: float = 34.0
    microspora_pitch: float = 21.1  # STEP round-end spacing in X and Z
    microspora_hole_x: float = -1.60  # round-end midpoint X relative to PCB centre
    microspora_hole_z: float = 0.95  # round-end midpoint Z relative to PCB centre
    microspora_hole_d: float = 3.1  # round hole matching the Ø3.14 mm slot end
    microspora_offset_x: float = 1.60  # centres U8 (MT6701) on X=0
    microspora_offset_y: float = -0.95  # centres U8 (MT6701) on Z=plate_z
    microspora_recess_d: float = 1.5  # component clearance
    microspora_u8_h: float = 0.76  # U8 (MT6701) package height on -Y face
    microspora_gap: float = 1.0  # magnet face to U8 sensor face margin

    # Stator-side magnet holder.
    holder_d: float = 9.6  # main body OD (clears M3 screw heads at X=±8.0 and stator)
    holder_boss_d: float = 6.0  # -Y protruding step OD (contacts moving bearing inner ring)
    holder_boss_h: float = 1.0  # -Y step protrusion height to clear stator/outer bearing
    holder_shaft_bore_d: float = 1.55  # blind bore depth for 1.50 mm shaft protrusion
    magnet_d: float = 6.2  # pocket: 6 mm magnet + 0.2 mm
    magnet_t: float = 2.25  # pocket: 2.15 mm magnet + 0.1 mm
    magnet_actual_d: float = 6.0
    magnet_actual_t: float = 2.15
    shaft_d: float = 4.1  # press fit: 4.0 mm shaft + 0.1 mm


def build(cfg: DroneStand = DroneStand()) -> tuple[Part, Part]:
    # Base: protrudes by base_lip in front (-Y) of the motor wall to spread the
    # overhanging motor weight, and extends toward +Y behind the wall.
    front_y = -cfg.motor_plate_t / 2 - cfg.base_lip
    base_y = front_y + cfg.base_d / 2
    base = Pos(0, base_y, cfg.base_t / 2) * Box(cfg.base_w, cfg.base_d, cfg.base_t)
    base -= Pos(0, front_y + cfg.base_d - 10, cfg.base_t / 2) * Box(
        cfg.clamp_slot_w, cfg.clamp_slot_d, cfg.base_t + 2
    )
    sx = cfg.base_w / 2 - cfg.table_screw_inset
    sy = cfg.base_d / 2 - cfg.table_screw_inset
    for x in (-sx, sx):
        for dy in (-sy, sy):
            base -= Pos(x, base_y + dy, cfg.base_t / 2) * Cylinder(
                cfg.table_screw_d / 2, cfg.base_t + 2
            )

    # Motor plate: vertical, front face at y = -motor_plate_t / 2.
    plate_z = cfg.base_t + cfg.motor_plate_h / 2
    motor_plate = Box(cfg.motor_plate_w, cfg.motor_plate_t, cfg.motor_plate_h)
    # Stator holes: Ø19 pair vertical, Ø16 pair horizontal, counterbored from
    # the back (+Y) so M3 cylindrical socket heads (Ø5.5 x 3.0 mm) sit 0.2 mm
    # below the MicroSpora recess floor.
    cbore_total_d = cfg.microspora_recess_d + cfg.motor_cbore_d_below_recess
    cbore_len = cbore_total_d + 1.0
    cbore_y = cfg.motor_plate_t / 2 - cbore_total_d + cbore_len / 2
    for x, z in (
        (0, cfg.motor_pitch_19 / 2),
        (0, -cfg.motor_pitch_19 / 2),
        (cfg.motor_pitch_16 / 2, 0),
        (-cfg.motor_pitch_16 / 2, 0),
    ):
        motor_plate -= Pos(x, 0, z) * Rot(90, 0, 0) * Cylinder(
            cfg.motor_hole_d / 2, cfg.motor_plate_t + 2
        )
        motor_plate -= Pos(x, cbore_y, z) * Rot(90, 0, 0) * Cylinder(
            cfg.motor_cbore_d / 2, cbore_len
        )
    motor_plate -= Rot(90, 0, 0) * Cylinder(
        cfg.motor_bore / 2, cfg.motor_plate_t + 2
    )
    # MicroSpora recess on the back of the plate, and its mounting holes
    # through the remaining web. One wall, no separate back plate.
    motor_plate -= Pos(
        cfg.microspora_offset_x,
        cfg.motor_plate_t / 2 - cfg.microspora_recess_d / 2,
        cfg.microspora_offset_y,
    ) * Box(
        cfg.microspora_w + 1.0,
        cfg.microspora_recess_d,
        cfg.microspora_h + 1.0,
    )
    web_t = cfg.motor_plate_t - cfg.microspora_recess_d
    half_p = cfg.microspora_pitch / 2
    for dx, dz in (
        (-half_p, half_p),   # top-left slot round end
        (half_p, half_p),    # top-right slot round end
        (half_p, -half_p),   # bottom-right slot round end
    ):
        motor_plate -= Pos(
            dx + cfg.microspora_hole_x + cfg.microspora_offset_x,
            cfg.motor_plate_t / 2 - cfg.microspora_recess_d - web_t / 2,
            dz + cfg.microspora_hole_z + cfg.microspora_offset_y,
        ) * Rot(90, 0, 0) * Cylinder(cfg.microspora_hole_d / 2, web_t + 2)
    motor_plate = Pos(0, 0, plate_z) * motor_plate

    stand = base + motor_plate

    # Stator-side magnet holder: a Ø6.0 mm boss protrudes on -Y to seat flat
    # against the moving inner side of the bearing while the Ø9.6 mm body
    # clears the stationary outer bearing race and stator.
    bearing_y = -cfg.motor_plate_t / 2
    recess_bottom = cfg.motor_plate_t / 2 - cfg.microspora_recess_d
    magnet_back_y = recess_bottom - cfg.microspora_u8_h - cfg.microspora_gap

    boss_y = bearing_y + cfg.holder_boss_h / 2
    holder_boss = Pos(0, boss_y, plate_z) * Rot(90, 0, 0) * Cylinder(
        cfg.holder_boss_d / 2, cfg.holder_boss_h
    )
    body_start_y = bearing_y + cfg.holder_boss_h
    body_t = magnet_back_y - body_start_y
    holder_body = Pos(0, body_start_y + body_t / 2, plate_z) * Rot(90, 0, 0) * Cylinder(
        cfg.holder_d / 2, body_t
    )
    holder = holder_boss + holder_body

    bore_len = cfg.holder_shaft_bore_d + 0.5
    bore_y = bearing_y - 0.5 + bore_len / 2
    holder -= Pos(0, bore_y, plate_z) * Rot(90, 0, 0) * Cylinder(
        cfg.shaft_d / 2, bore_len
    )

    pocket_len = cfg.magnet_t + 0.5
    pocket_y = magnet_back_y - cfg.magnet_t + pocket_len / 2
    holder -= Pos(0, pocket_y, plate_z) * Rot(90, 0, 0) * Cylinder(
        cfg.magnet_d / 2, pocket_len
    )

    return stand, holder


def _place_microspora(part: Part, cfg: DroneStand = DroneStand()) -> Part:
    """Transform a STEP-frame MicroSpora mesh into the stand assembly frame."""
    pcb = microspora.board()
    bb = pcb.bounding_box()
    cx = (bb.min.X + bb.max.X) / 2
    cy = (bb.min.Y + bb.max.Y) / 2
    plate_z = cfg.base_t + cfg.motor_plate_h / 2
    recess_bottom = cfg.motor_plate_t / 2 - cfg.microspora_recess_d

    # Pure rotation: +Z (component side) -> +Y, then 180 around Z to put the
    # board's top at the top.
    rotated = Rot(90, 0, 0) * Rot(0, 180, 0) * Rot(0, 0, 180) * part
    return Pos(
        -cx + cfg.microspora_offset_x,
        recess_bottom,
        plate_z + cy + cfg.microspora_offset_y,
    ) * rotated


def microspora_board(cfg: DroneStand = DroneStand()) -> Part:
    """Real MicroSpora PCB, component side facing +Y (visible from behind)."""
    return _place_microspora(microspora.board(), cfg)


def microspora_encoder(cfg: DroneStand = DroneStand()) -> Part:
    """The MT6701 (U8) on the board, for checking the magnet alignment."""
    return _place_microspora(microspora.encoder(), cfg)


def microspora_components(cfg: DroneStand = DroneStand()) -> Part:
    """All other named SMD components on the MicroSpora board."""
    return _place_microspora(microspora.components(), cfg)


def microspora_populated(cfg: DroneStand = DroneStand()) -> Part:
    """Populated MicroSpora board (PCB, U8 encoder, and all SMD components)."""
    return _place_microspora(
        Compound([microspora.board(), microspora.encoder(), microspora.components()]),
        cfg,
    )


def magnet(cfg: DroneStand = DroneStand()) -> Part:
    """Reference diametric magnet."""
    return Rot(90, 0, 0) * Cylinder(cfg.magnet_actual_d / 2, cfg.magnet_actual_t)


def assembly_parts(
    cfg: DroneStand = DroneStand(),
) -> list[tuple[str, Part, str]]:
    """L-stand, motor, magnet holder, magnet, and MicroSpora in working positions."""
    stand, holder = build(cfg)
    plate_z = cfg.base_t + cfg.motor_plate_h / 2

    motor = Pos(0, -cfg.motor_plate_t / 2, plate_z) * motor_5010.build()
    board = microspora_board(cfg)
    bb = board.bounding_box()
    sensor_face = bb.min.Y - cfg.microspora_u8_h
    magnet_y = sensor_face - cfg.microspora_gap - cfg.magnet_actual_t / 2

    return [
        ("stand", stand, "#8fa8c8"),
        ("motor", motor, "#e0a060"),
        ("holder", holder, "#7fc8a0"),
        ("magnet", Pos(0, magnet_y, plate_z) * magnet(cfg), "#c080d0"),
        ("microspora", board, "#d07070"),
        ("encoder", microspora_encoder(cfg), "#303030"),
        ("components", microspora_components(cfg), "#b8c0c8"),
    ]


def assemblies() -> dict[str, list[tuple[str, Part, str]]]:
    return {
        "drone_stand_microspora": assembly_parts(),
    }


def parts() -> dict[str, Part]:
    """Named parts, for the viewer and the exporter."""
    stand, holder = build()
    return {
        "drone_stand": stand,
        "drone_magnet_holder": holder,
        "drone_magnet": magnet(),
        "drone_sensor_microspora": microspora_populated(),
    }


def main() -> None:
    for name, part in parts().items():
        export(part, name)


if __name__ == "__main__":
    main()
