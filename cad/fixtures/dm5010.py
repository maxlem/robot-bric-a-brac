"""Reference model of the SMC Powers DM5010 gimbal motor (two-piece housing).

Not a printable part: a reference model of the motor's two physical pieces:
1. ``dm5010``: the main motor body (rotating outer bell + stationary stator
   base with its Ø12.7 mm hollow slip-ring bore and 4 rear cylindrical stator
   pillars carrying the M2.5 mounting threads).
2. ``dm5010_cap``: the removable 4.85 mm rear cap (caliper measured) behind the
   stator, pierced by the 4 cylindrical stator pillars and held by two perimeter
   screws, with the side BGC-CAN-DRV connector cutout.

Source:
    http://shop.smc-powers.com/DM5010-BGC-DRV.html
    http://shop.smc-powers.com/image/data/SMC/DM5010D-12.jpg

Local frame: the rear face of the cap and the ends of the 4 stator pillars are
at y = 0, the stator backplate (under the cap) is at y = -rear_cap_l (-4.85 mm),
and the rotor output face is at y = -motor_l (-28.90 mm).
"""

from __future__ import annotations

import functools
import sys
from dataclasses import dataclass
from pathlib import Path

from build123d import Box, Cylinder, Part, Pos, Rot

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from params import ParamConfig  # noqa: E402


@dataclass(frozen=True)
class DM5010(ParamConfig):
    CONSTANTS = ("*",)  # Reference hardware dimensions & caliper measurements
    PART_GROUPS = {
        "dm5010": [
            "Outer envelope",
            "Hollow slip-ring bore",
            "Stator mounting pattern",
            "Rotor mounting pattern",
            "Side connector pocket",
            "Electrical specifications",
        ],
        "dm5010_cap": [
            "Outer envelope",
            "Stator mounting pattern",
            "Side connector pocket",
        ],
    }

    # Outer envelope.
    motor_d: float = 49.0  # outer diameter (mm)
    motor_l: float = 28.90  # total axial length including rear cap (mm)
    rear_cap_l: float = 4.85  # removable rear cap thickness behind stator (mm, caliper)
    cap_wall_t: float = 1.6  # rear cap wall/face thickness (mm)
    stator_base_l: float = 5.65  # stationary stator ring in front of rear cap (mm)
    gap_l: float = 0.5  # axial seam between stator ring and rotor bell (mm)
    seam_d: float = 47.5  # diameter at rotor/stator seam groove (mm)

    # Hollow slip-ring bore.
    bore_d: float = 12.7  # hollow slip-ring through-bore diameter (mm)
    shaft_boss_d: float = 15.0  # inner hollow shaft collar OD on rotor face (mm)
    hub_recess_d: float = 19.0  # annular recess OD around shaft collar (mm)
    hub_recess_depth: float = 2.0  # annular recess depth on rotor face (mm)

    # Stator mounting pattern (4 cylindrical pillars piercing through the rear cap).
    stator_pitch: float = 20.0  # 4 x M2.5 square spacing (mm)
    pillar_d: float = 5.0  # OD of the 4 cylindrical stator pillars under the cap (mm)
    stator_hole_d: float = 2.5  # M2.5 tap diameter inside the 4 pillars (mm)
    stator_hole_depth: float = 6.0

    # Rotor mounting pattern.
    rotor_pitch: float = 25.0  # 4 x M3 bolt circle diameter (mm)
    rotor_hole_d: float = 3.0  # M3 tap diameter (mm)
    rotor_hole_depth: float = 5.0

    # Side connector pocket.
    connector_w: float = 14.0  # side connector cutout height along Z (mm)
    connector_l: float = 5.5  # side connector cutout axial width along Y (mm)
    connector_depth: float = 4.5  # radial depth into -X side of housing (mm)

    # Electrical specifications.
    pole_pairs: int = 14  # 24N28P configuration (14 pole pairs)
    nominal_voltage_v: float = 16.0  # rated voltage (16-24 V bus)
    nominal_current_a: float = 0.79  # rated continuous current (A)
    stall_current_a: float = 1.20  # peak / stall current (A)
    resistance_ohm: float = 10.8  # line-to-line phase resistance (ohm, 10.3 meas.)
    inductance_mh: float = 4.74  # line-to-line phase inductance (mH)
    kv_rpm_per_v: float = 33.0  # speed constant Kv (rpm/V)
    kt_nm_per_a: float = 0.27  # torque constant Kt (Nm/A)
    nominal_torque_nm: float = 0.25  # continuous rated torque (Nm)
    stall_torque_nm: float = 0.32  # peak / stall torque (Nm)
    nominal_speed_rpm: float = 150.0  # rated speed (rpm)
    max_speed_rpm: float = 505.0  # no-load max speed (rpm)
    rotor_inertia_gcm2: float = 202.0  # rotor inertia (g*cm^2)
    mass_g: float = 135.0  # motor mass (g)


@functools.lru_cache(maxsize=8)
def build_pair(cfg: DM5010 = DM5010()) -> tuple[Part, Part]:
    """Return ``(motor_body, rear_cap)`` in the DM5010 local frame."""
    driver_l = cfg.rear_cap_l + cfg.stator_base_l
    bell_l = cfg.motor_l - driver_l - cfg.gap_l
    half_s = cfg.stator_pitch / 2

    # 1. Removable rear cap: hollow cover y = -rear_cap_l .. 0 (4.85 mm thick),
    #    pierced by the 4 cylindrical stator pillars at (±10, ±10).
    cap = (
        Pos(0, -cfg.rear_cap_l / 2, 0)
        * Rot(90, 0, 0)
        * Cylinder(cfg.motor_d / 2, cfg.rear_cap_l)
    )
    cap_cavity_h = max(0.5, cfg.rear_cap_l - cfg.cap_wall_t)
    cap -= (
        Pos(0, -cfg.rear_cap_l + cap_cavity_h / 2 - 0.05, 0)
        * Rot(90, 0, 0)
        * Cylinder(cfg.motor_d / 2 - cfg.cap_wall_t, cap_cavity_h + 0.1)
    )
    # Two perimeter cap screw bosses & counterbores at top/bottom (Z = ±21.5 mm).
    for z in (-cfg.motor_d / 2 + 3.0, cfg.motor_d / 2 - 3.0):
        cap += (
            Pos(0, -cfg.rear_cap_l / 2, z)
            * Rot(90, 0, 0)
            * Cylinder(3.2, cfg.rear_cap_l)
        )
        cap -= Pos(0, -1.25, z) * Rot(90, 0, 0) * Cylinder(2.25, 2.5)
        cap -= (
            Pos(0, -cfg.rear_cap_l / 2, z)
            * Rot(90, 0, 0)
            * Cylinder(1.1, cfg.rear_cap_l + 1.0)
        )
    # 4 clearance holes in the rear cap for the 4 cylindrical stator pillars.
    for x in (-half_s, half_s):
        for z in (-half_s, half_s):
            cap -= (
                Pos(x, -cfg.rear_cap_l / 2, z)
                * Rot(90, 0, 0)
                * Cylinder(cfg.pillar_d / 2 + 0.1, cfg.rear_cap_l + 1.0)
            )
    # Central opening in the rear cap for the hollow bore / encoder access.
    cap -= (
        Pos(0, -cfg.rear_cap_l / 2, 0)
        * Rot(90, 0, 0)
        * Cylinder(cfg.bore_d / 2 + 0.5, cfg.rear_cap_l + 1.0)
    )

    # Side connector notch at the interface between rear cap and stator base.
    conn_y = -cfg.rear_cap_l - cfg.stator_base_l + 1.5 + cfg.connector_l / 2
    conn_x = -cfg.motor_d / 2 + cfg.connector_depth / 2
    conn_box = Pos(conn_x, conn_y, 0) * Box(
        cfg.connector_depth + 1.0, cfg.connector_l, cfg.connector_w
    )
    cap -= conn_box

    # 2. Main motor body (stator base + 4 cylindrical stator pillars + seam + rotor bell).
    stator_base = (
        Pos(0, -cfg.rear_cap_l - cfg.stator_base_l / 2, 0)
        * Rot(90, 0, 0)
        * Cylinder(cfg.motor_d / 2, cfg.stator_base_l)
    )
    seam = (
        Pos(0, -driver_l - cfg.gap_l / 2, 0)
        * Rot(90, 0, 0)
        * Cylinder(cfg.seam_d / 2, cfg.gap_l)
    )
    bell_center_y = -driver_l - cfg.gap_l - bell_l / 2
    bell = (
        Pos(0, bell_center_y, 0)
        * Rot(90, 0, 0)
        * Cylinder(cfg.motor_d / 2, bell_l)
    )
    motor_body = stator_base + seam + bell
    motor_body -= conn_box

    # 4 cylindrical stator pillars rising from y = -rear_cap_l through the cap to y = 0,
    # with the 4 x M2.5 mounting holes tapped inside them.
    for x in (-half_s, half_s):
        for z in (-half_s, half_s):
            motor_body += (
                Pos(x, -cfg.rear_cap_l / 2, z)
                * Rot(90, 0, 0)
                * Cylinder(cfg.pillar_d / 2, cfg.rear_cap_l)
            )
            motor_body -= (
                Pos(x, -cfg.stator_hole_depth / 2, z)
                * Rot(90, 0, 0)
                * Cylinder(cfg.stator_hole_d / 2, cfg.stator_hole_depth)
            )

    # Subtle front rotor flange groove (2.7 mm from rotor face).
    front_groove_y = -cfg.motor_l + 2.7
    motor_body -= (
        Pos(0, front_groove_y, 0)
        * Rot(90, 0, 0)
        * Cylinder(cfg.motor_d / 2 + 1.0, 0.35)
        - Pos(0, front_groove_y, 0)
        * Rot(90, 0, 0)
        * Cylinder(cfg.motor_d / 2 - 0.4, 0.5)
    )

    # Rotor mounting holes: 4 x M3 on a Ø25 mm bolt circle on y = -motor_l.
    rotor_y = -cfg.motor_l
    r_bc = cfg.rotor_pitch / 2
    for x, z in ((0, r_bc), (0, -r_bc), (r_bc, 0), (-r_bc, 0)):
        motor_body -= (
            Pos(x, rotor_y + cfg.rotor_hole_depth / 2, z)
            * Rot(90, 0, 0)
            * Cylinder(cfg.rotor_hole_d / 2, cfg.rotor_hole_depth)
        )

    # Annular recess on the rotor face around the hollow shaft collar.
    recess_y = rotor_y + cfg.hub_recess_depth / 2
    annulus = (
        Pos(0, recess_y, 0)
        * Rot(90, 0, 0)
        * Cylinder(cfg.hub_recess_d / 2, cfg.hub_recess_depth)
        - Pos(0, recess_y, 0)
        * Rot(90, 0, 0)
        * Cylinder(cfg.shaft_boss_d / 2, cfg.hub_recess_depth + 0.2)
    )
    motor_body -= annulus

    # Hollow slip-ring through-bore (Ø12.7 mm) through the motor body.
    body_l = cfg.motor_l - cfg.rear_cap_l
    motor_body -= (
        Pos(0, -cfg.rear_cap_l - body_l / 2, 0)
        * Rot(90, 0, 0)
        * Cylinder(cfg.bore_d / 2, body_l + 2.0)
    )

    return motor_body, cap


@functools.lru_cache(maxsize=8)
def build(cfg: DM5010 = DM5010()) -> Part:
    """Combined DM5010 motor body + rear cap."""
    motor_body, cap = build_pair(cfg)
    return motor_body + cap


def parts(cfg: DM5010 = DM5010()) -> dict[str, Part]:
    motor_body, cap = build_pair(cfg)
    return {
        "dm5010": motor_body,
        "dm5010_cap": cap,
    }


def main() -> None:
    from export import export

    for name, part in parts().items():
        export(part, name)


if __name__ == "__main__":
    main()
