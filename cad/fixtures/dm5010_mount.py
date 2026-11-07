"""Phase 1 fixture: L-shaped DM5010 + MicroSpora test stand.

Mirrors the L-bracket architecture of ``drone_stand.py`` for the SMC Powers
DM5010 gimbal motor (Ø49.0 × 28.90 mm, Ø12.7 mm slip-ring bore, 4 × M2.5 on a
20.0 × 20.0 mm stator pattern):

- **Rotor side (front, -Y)**: completely open and free of obstacles.
- **Stator side (back, +Y)**: MicroSpora recessed in the vertical wall, with
  the 3D-printed hollow-bore magnet carrier holding the diametric magnet at
  ``microspora_gap`` in front of U8 (MT6701) and the table base extending
  toward +Y with a front (-Y) lip under the motor.

The motor is a reference model (``dm5010.py``), not a printed part.
"""

from __future__ import annotations

import functools
import sys
from dataclasses import dataclass
from pathlib import Path

from build123d import Box, Compound, Cylinder, Part, Pos, Rot

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from export import export  # noqa: E402
from fixtures import dm5010  # noqa: E402
from params import ParamConfig  # noqa: E402
from reference import microspora  # noqa: E402


@dataclass(frozen=True)
class DM5010Mount(ParamConfig):
    BINDINGS = {
        "motor_pitch": "= dm5010.stator_pitch",
        "motor_bore": "= carrier_flange_d + 1.0",
        "carrier_flange_d": "= shaft_d + 1.0",
        "shaft_d": "= dm5010.bore_d - 0.1",
        "magnet_d": "= magnet_actual_d + clearance",
        "magnet_t": "= magnet_actual_t + 0.1",
    }
    CONSTANTS = (
        "motor_pitch",
        "microspora_w",
        "microspora_h",
        "microspora_pitch",
        "microspora_hole_x",
        "microspora_hole_z",
        "microspora_hole_d",
        "microspora_offset_x",
        "microspora_offset_y",
        "microspora_u8_h",
        "magnet_actual_d",
        "magnet_actual_t",
    )
    PART_GROUPS = {
        "dm5010_mount": ["Base", "Motor plate", "Stator-side encoder"],
        "mount": ["Base", "Motor plate", "Stator-side encoder"],
        "dm5010_magnet_carrier": ["Magnet carrier"],
        "carrier": ["Magnet carrier"],
        "microspora": ["Stator-side encoder"],
        "encoder": ["Stator-side encoder"],
        "components": ["Stator-side encoder"],
    }
    PART_FIELDS = {
        "magnet": [
            "magnet_actual_d",
            "magnet_actual_t",
            "magnet_d",
            "magnet_t",
            "microspora_gap",
        ],
        "motor": ["dm5010.*"],
    }

    # Base: extends toward +Y behind the motor wall, with a front (-Y) lip
    # under the DM5010 to spread the motor's weight and prevent forward tipping.
    base_w: float = 100.0
    base_d: float = 75.0
    base_lip: float = 15.0  # -Y lip in front of the motor wall
    base_t: float = 6.0
    clamp_slot_w: float = 20.0
    clamp_slot_d: float = 8.0
    table_screw_d: float = 4.5  # M4 clearance
    table_screw_inset: float = 8.0

    # Motor plate: vertical front wall of the L-bracket, DM5010 on -Y face.
    # 54 mm tall (shaft at Z=33 mm) so the Ø49 mm motor clears the 6 mm base lip.
    motor_plate_w: float = 50.0
    motor_plate_h: float = 54.0
    motor_plate_t: float = 7.5
    motor_pitch: float = 20.0  # 4 x M2.5 on a 20.0 x 20.0 mm square
    motor_hole_d: float = 2.9  # M2.5 clearance
    motor_cbore_d: float = 5.0  # M2.5 socket head counterbore (Ø4.5 mm head)
    motor_cbore_d_below_recess: float = 2.7  # 2.5 mm head height + 0.2 mm margin
    motor_bore: float = 14.6  # clears Ø13.6 mm carrier flange with 0.5 mm radial gap

    # Stator-side encoder: MicroSpora in a recess on the back of the plate.
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

    # Magnet carrier: stepped plug that press-fits the Ø12.7 mm hollow bore and
    # positions the Ø6 mm diametric magnet in front of U8 (MT6701).
    shaft_d: float = 12.6  # press-fit OD inside Ø12.7 mm slip-ring bore
    carrier_flange_d: float = 13.6  # rear shoulder OD inside motor_bore
    carrier_bore_depth: float = 4.0  # engagement depth into DM5010 hollow bore (-Y)
    magnet_d: float = 6.2  # pocket: 6.0 mm magnet + 0.2 mm
    magnet_t: float = 2.25  # pocket: 2.15 mm magnet + 0.1 mm
    magnet_actual_d: float = 6.0
    magnet_actual_t: float = 2.15


@functools.lru_cache(maxsize=8)
def build(cfg: DM5010Mount = DM5010Mount()) -> tuple[Part, Part]:
    # Base: protrudes by base_lip in front (-Y) of the motor wall and extends
    # toward +Y behind the wall.
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

    # DM5010 stator holes: 4 x M2.5 on a 20 x 20 mm square, counterbored from
    # the back (+Y) so M2.5 socket heads sit 0.2 mm below the MicroSpora recess floor.
    cbore_total_d = cfg.microspora_recess_d + cfg.motor_cbore_d_below_recess
    cbore_len = cbore_total_d + 1.0
    cbore_y = cfg.motor_plate_t / 2 - cbore_total_d + cbore_len / 2
    half_m = cfg.motor_pitch / 2
    for x in (-half_m, half_m):
        for z in (-half_m, half_m):
            motor_plate -= Pos(x, 0, z) * Rot(90, 0, 0) * Cylinder(
                cfg.motor_hole_d / 2, cfg.motor_plate_t + 2
            )
            motor_plate -= Pos(x, cbore_y, z) * Rot(90, 0, 0) * Cylinder(
                cfg.motor_cbore_d / 2, cbore_len
            )

    motor_plate -= Rot(90, 0, 0) * Cylinder(
        cfg.motor_bore / 2, cfg.motor_plate_t + 2
    )

    # MicroSpora recess on the back (+Y) of the plate, and its 3 corner mounting
    # holes through the remaining web.
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
    mount = base + motor_plate

    # Hollow-bore magnet carrier in assembly coordinates:
    # - A Ø(shaft_d) plug extends into the DM5010's Ø12.7 mm hollow bore on -Y
    #   (from y = -motor_plate_t/2 - carrier_bore_depth to y = -motor_plate_t/2).
    # - A Ø(carrier_flange_d) body extends through motor_bore on +Y up to
    #   magnet_back_y (just in front of U8 on the MicroSpora).
    motor_face_y = -cfg.motor_plate_t / 2
    recess_bottom = cfg.motor_plate_t / 2 - cfg.microspora_recess_d
    magnet_back_y = recess_bottom - cfg.microspora_u8_h - cfg.microspora_gap

    plug_y = motor_face_y - cfg.carrier_bore_depth / 2
    carrier_plug = (
        Pos(0, plug_y, plate_z)
        * Rot(90, 0, 0)
        * Cylinder(cfg.shaft_d / 2, cfg.carrier_bore_depth)
    )
    body_t = magnet_back_y - motor_face_y
    carrier_body = (
        Pos(0, motor_face_y + body_t / 2, plate_z)
        * Rot(90, 0, 0)
        * Cylinder(cfg.carrier_flange_d / 2, body_t)
    )
    carrier = carrier_plug + carrier_body

    pocket_len = cfg.magnet_t + 0.5
    pocket_y = magnet_back_y - cfg.magnet_t + pocket_len / 2
    carrier -= (
        Pos(0, pocket_y, plate_z)
        * Rot(90, 0, 0)
        * Cylinder(cfg.magnet_d / 2, pocket_len)
    )

    return mount, carrier


@functools.lru_cache(maxsize=16)
def _placed_microspora_kind(
    kind: str,
    base_t: float,
    motor_plate_h: float,
    motor_plate_t: float,
    microspora_recess_d: float,
    microspora_offset_x: float,
    microspora_offset_y: float,
) -> Part:
    pcb = microspora.board()
    bb = pcb.bounding_box()
    cx = (bb.min.X + bb.max.X) / 2
    cy = (bb.min.Y + bb.max.Y) / 2
    plate_z = base_t + motor_plate_h / 2
    recess_bottom = motor_plate_t / 2 - microspora_recess_d

    if kind == "board":
        part = pcb
    elif kind == "encoder":
        part = microspora.encoder()
    elif kind == "components":
        part = microspora.components()
    else:
        part = Compound([pcb, microspora.encoder(), microspora.components()])

    rotated = Rot(90, 0, 0) * Rot(0, 180, 0) * Rot(0, 0, 180) * part
    return Pos(
        -cx + microspora_offset_x,
        recess_bottom,
        plate_z + cy + microspora_offset_y,
    ) * rotated


def microspora_board(cfg: DM5010Mount = DM5010Mount()) -> Part:
    """Real MicroSpora PCB, component side facing +Y (visible from behind)."""
    return _placed_microspora_kind(
        "board",
        cfg.base_t,
        cfg.motor_plate_h,
        cfg.motor_plate_t,
        cfg.microspora_recess_d,
        cfg.microspora_offset_x,
        cfg.microspora_offset_y,
    )


def microspora_encoder(cfg: DM5010Mount = DM5010Mount()) -> Part:
    """The MT6701 (U8) on the board, for checking the magnet alignment."""
    return _placed_microspora_kind(
        "encoder",
        cfg.base_t,
        cfg.motor_plate_h,
        cfg.motor_plate_t,
        cfg.microspora_recess_d,
        cfg.microspora_offset_x,
        cfg.microspora_offset_y,
    )


def microspora_components(cfg: DM5010Mount = DM5010Mount()) -> Part:
    """All other named SMD components on the MicroSpora board."""
    return _placed_microspora_kind(
        "components",
        cfg.base_t,
        cfg.motor_plate_h,
        cfg.motor_plate_t,
        cfg.microspora_recess_d,
        cfg.microspora_offset_x,
        cfg.microspora_offset_y,
    )


@functools.lru_cache(maxsize=8)
def magnet(cfg: DM5010Mount = DM5010Mount()) -> Part:
    """Reference diametric magnet."""
    return Rot(90, 0, 0) * Cylinder(cfg.magnet_actual_d / 2, cfg.magnet_actual_t)


def assembly_parts(
    cfg: DM5010Mount = DM5010Mount(),
    dm5010_cfg: dm5010.DM5010 | None = None,
) -> list[tuple[str, Part, str]]:
    """L-stand, DM5010 motor, magnet carrier, magnet, and MicroSpora in working positions."""
    mount, carrier = build(cfg)
    plate_z = cfg.base_t + cfg.motor_plate_h / 2

    m_part = (
        dm5010.build(dm5010_cfg)
        if dm5010_cfg is not None
        else dm5010.build()
    )
    motor = Pos(0, -cfg.motor_plate_t / 2, plate_z) * m_part
    board = microspora_board(cfg)
    bb = board.bounding_box()
    sensor_face = bb.min.Y - cfg.microspora_u8_h
    magnet_y = sensor_face - cfg.microspora_gap - cfg.magnet_actual_t / 2

    return [
        ("mount", mount, "#8fa8c8"),
        ("motor", motor, "#e0a060"),
        ("carrier", carrier, "#7fc8a0"),
        ("magnet", Pos(0, magnet_y, plate_z) * magnet(cfg), "#c080d0"),
        ("microspora", board, "#d07070"),
        ("encoder", microspora_encoder(cfg), "#303030"),
        ("components", microspora_components(cfg), "#b8c0c8"),
    ]


def assemblies(
    cfg: DM5010Mount = DM5010Mount(),
    dm5010_cfg: dm5010.DM5010 | None = None,
) -> dict[str, list[tuple[str, Part, str]]]:
    return {
        "dm5010_mount_assembly": assembly_parts(cfg, dm5010_cfg=dm5010_cfg),
    }


def parts(cfg: DM5010Mount = DM5010Mount()) -> dict[str, Part]:
    """Named parts, for the viewer and the exporter."""
    mount, carrier = build(cfg)
    return {"dm5010_mount": mount, "dm5010_magnet_carrier": carrier}


def main() -> None:
    for name, part in parts().items():
        export(part, name)


if __name__ == "__main__":
    main()
