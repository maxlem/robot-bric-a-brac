"""Phase 1 fixture: DM5010 + MicroSpora mount.

Holds a DM5010 with the shaft horizontal and positions the MicroSpora so its
onboard MT6701 is centred on the magnet.

Dimensions use the DM5010-BGC-DRV (Ø12.7 mm slip-ring bore, 20 × 20 mm M2.5
stator pattern) reference model in ``fixtures/dm5010.py``.
"""

from __future__ import annotations

import functools
import sys
from dataclasses import dataclass
from pathlib import Path

from build123d import Box, Cylinder, Part, Pos, Rot

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from export import export  # noqa: E402
from fixtures import dm5010  # noqa: E402
from params import ParamConfig  # noqa: E402


@dataclass(frozen=True)
class DM5010Mount(ParamConfig):
    BINDINGS = {
        "motor_pitch": "= dm5010.stator_pitch",
        "motor_bore": "= dm5010.bore_d + 1.0",
        "shaft_d": "= dm5010.bore_d",
        "board_pitch_x": "= board_w - 5.0",
        "board_pitch_y": "= board_h - 5.0",
    }
    CONSTANTS = (
        "motor_pitch",
        "board_w",
        "board_h",
        "shaft_d",
    )
    PART_GROUPS = {
        "dm5010_mount": [
            "Base",
            "Riser and motor plate",
            "DM5010 interface",
            "MicroSpora",
        ],
        "mount": [
            "Base",
            "Riser and motor plate",
            "DM5010 interface",
            "MicroSpora",
        ],
        "dm5010_magnet_carrier": ["Magnet carrier"],
        "carrier": ["Magnet carrier"],
    }
    PART_FIELDS = {
        "motor": ["dm5010.*"],
    }
    # Base.
    base_w: float = 80.0
    base_d: float = 60.0
    base_t: float = 6.0
    clamp_slot_w: float = 20.0
    clamp_slot_d: float = 8.0

    # Riser and motor plate.
    riser_w: float = 20.0
    riser_d: float = 20.0
    riser_h: float = 40.0
    motor_plate_w: float = 50.0
    motor_plate_h: float = 50.0
    motor_plate_t: float = 6.0

    # DM5010 interface. 4 x M2.5 on a 20.0 x 20.0 mm square, 12.7 mm slip-ring bore.
    motor_pitch: float = 20.0
    motor_hole_d: float = 2.9  # M2.5 clearance
    motor_bore: float = 13.7  # clears Ø12.7 mm hollow slip-ring bore

    # MicroSpora.
    board_w: float = 33.0
    board_h: float = 34.0
    board_pitch_x: float = 28.0
    board_pitch_y: float = 29.0
    board_hole_d: float = 2.4  # M2 clearance
    sensor_offset_x: float = 0.0
    sensor_offset_y: float = 0.0
    sensor_opening: float = 8.0
    sensor_gap: float = 1.5

    # Magnet carrier: stepped plug that press-fits the Ø12.7 mm hollow bore and
    # holds the Ø6 mm diametric magnet on the axis.
    magnet_d: float = 6.2
    magnet_t: float = 2.5
    shaft_d: float = 12.7
    carrier_depth: float = 5.0
    carrier_flange_t: float = 1.5


@functools.lru_cache(maxsize=8)
def build(cfg: DM5010Mount = DM5010Mount()) -> tuple[Part, Part]:
    # Base with a clamp slot.
    base = Pos(0, 0, cfg.base_t / 2) * Box(cfg.base_w, cfg.base_d, cfg.base_t)
    base -= Pos(0, -cfg.base_d / 2 + 10, cfg.base_t / 2) * Box(
        cfg.clamp_slot_w, cfg.clamp_slot_d, cfg.base_t + 2
    )

    # Riser at the back.
    riser_y = cfg.base_d / 2 - cfg.riser_d / 2
    riser = Pos(0, riser_y, cfg.base_t + cfg.riser_h / 2) * Box(
        cfg.riser_w, cfg.riser_d, cfg.riser_h
    )

    # Vertical motor plate, facing -Y.
    plate_y = riser_y - cfg.riser_d / 2 - cfg.motor_plate_t / 2
    plate_z = cfg.base_t + cfg.riser_h - cfg.motor_plate_h / 2
    motor_plate = Box(cfg.motor_plate_w, cfg.motor_plate_t, cfg.motor_plate_h)
    for x in (-cfg.motor_pitch / 2, cfg.motor_pitch / 2):
        for z in (-cfg.motor_pitch / 2, cfg.motor_pitch / 2):
            motor_plate -= Pos(x, 0, z) * Rot(90, 0, 0) * Cylinder(
                cfg.motor_hole_d / 2, cfg.motor_plate_t + 2
            )
    motor_plate -= Rot(90, 0, 0) * Cylinder(
        cfg.motor_bore / 2, cfg.motor_plate_t + 2
    )
    motor_plate = Pos(0, plate_y, plate_z) * motor_plate

    # Board plate behind the motor, facing -Y, on a post.
    board_y = plate_y + cfg.motor_plate_t / 2 + cfg.sensor_gap + 3.0
    board_plate = Box(cfg.board_w, 3.0, cfg.board_h)
    for x in (-cfg.board_pitch_x / 2, cfg.board_pitch_x / 2):
        for z in (-cfg.board_pitch_y / 2, cfg.board_pitch_y / 2):
            board_plate -= Pos(x, 0, z) * Rot(90, 0, 0) * Cylinder(
                cfg.board_hole_d / 2, 5
            )
    board_plate -= Pos(cfg.sensor_offset_x, 0, cfg.sensor_offset_y) * Rot(
        90, 0, 0
    ) * Cylinder(cfg.sensor_opening / 2, 5)
    board_plate = Pos(0, board_y, plate_z) * board_plate

    post_h = plate_z - cfg.base_t
    post = Pos(0, board_y, cfg.base_t + post_h / 2) * Box(10, 10, post_h)

    mount = base + riser + motor_plate + board_plate + post

    # Magnet carrier: stepped plug that press-fits into the Ø12.7 mm hollow bore
    # and holds the Ø6 mm diametric magnet on the +Z (sensor) face.
    total_h = cfg.carrier_depth + cfg.carrier_flange_t
    plug = Pos(0, 0, -cfg.carrier_flange_t / 2) * Cylinder(
        cfg.shaft_d / 2, cfg.carrier_depth
    )
    flange = Pos(0, 0, cfg.carrier_depth / 2) * Cylinder(
        cfg.shaft_d / 2 + 1.0, cfg.carrier_flange_t
    )
    carrier = plug + flange
    carrier -= Pos(0, 0, total_h / 2 - cfg.magnet_t / 2 + 0.1) * Cylinder(
        cfg.magnet_d / 2, cfg.magnet_t + 0.2
    )

    return mount, carrier


def assembly_parts(
    cfg: DM5010Mount = DM5010Mount(),
    dm5010_cfg: dm5010.DM5010 | None = None,
) -> list[tuple[str, Part, str]]:
    """Mount, DM5010 motor, and hollow-bore magnet carrier in working positions."""
    mount, carrier = build(cfg)
    riser_y = cfg.base_d / 2 - cfg.riser_d / 2
    plate_y = riser_y - cfg.riser_d / 2 - cfg.motor_plate_t / 2
    plate_z = cfg.base_t + cfg.riser_h - cfg.motor_plate_h / 2
    motor_front_y = plate_y - cfg.motor_plate_t / 2

    m_part = (
        dm5010.build(dm5010_cfg)
        if dm5010_cfg is not None
        else dm5010.build()
    )
    motor_placed = Pos(0, motor_front_y, plate_z) * m_part
    carrier_placed = (
        Pos(0, motor_front_y, plate_z) * Rot(-90, 0, 0) * carrier
    )
    return [
        ("mount", mount, "#8fa8c8"),
        ("motor", motor_placed, "#e0a060"),
        ("carrier", carrier_placed, "#7fc8a0"),
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
