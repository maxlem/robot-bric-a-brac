"""Reference model of the SMC Powers DM5010 gimbal motor (with BGC-CAN-DRV).

Not a printable part: a reference model of the motor's envelope, hollow
slip-ring bore, and both stator/rotor mounting patterns.

Source:
    http://shop.smc-powers.com/DM5010-BGC-DRV.html
    http://shop.smc-powers.com/image/data/SMC/DM5010D-12.jpg

Key dimensions (25150101 / DM5010D-12):
    Envelope:     Ø49.0 × 28.90 mm
    Hollow bore:  Ø12.7 mm slip-ring through-hole
    Stator side:  4 × M2.5 on a 20.0 × 20.0 mm square
    Rotor side:   4 × M3 on a Ø25.0 mm bolt circle

Local frame: the stator/driver mounting face is at y = 0 and the motor extends
toward -Y (rotor output face at y = -motor_l).
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
    CONSTANTS = ("*",)  # Reference hardware dimensions from DM5010D-12 drawing

    # Outer envelope.
    motor_d: float = 49.0  # outer diameter (mm)
    motor_l: float = 28.90  # total axial length (mm)
    driver_l: float = 10.5  # rear encoder + BGC-CAN-DRV housing length (mm)
    gap_l: float = 0.5  # axial seam between driver cap and rotor bell (mm)
    seam_d: float = 47.5  # diameter at rotor/stator seam groove (mm)

    # Hollow slip-ring bore.
    bore_d: float = 12.7  # hollow slip-ring through-bore diameter (mm)
    shaft_boss_d: float = 15.0  # inner hollow shaft collar OD on rotor face (mm)
    hub_recess_d: float = 19.0  # annular recess OD around shaft collar (mm)
    hub_recess_depth: float = 2.0  # annular recess depth on rotor face (mm)

    # Stator mounting pattern.
    stator_pitch: float = 20.0  # 4 x M2.5 square spacing (mm)
    stator_hole_d: float = 2.5  # M2.5 tap diameter (mm)
    stator_hole_depth: float = 5.0

    # Rotor mounting pattern.
    rotor_pitch: float = 25.0  # 4 x M3 bolt circle diameter (mm)
    rotor_hole_d: float = 3.0  # M3 tap diameter (mm)
    rotor_hole_depth: float = 5.0

    # Side connector pocket.
    connector_w: float = 14.0  # side connector cutout height along Z (mm)
    connector_l: float = 5.5  # side connector cutout axial width along Y (mm)
    connector_depth: float = 4.5  # radial depth into -X side of driver housing (mm)

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
def build(cfg: DM5010 = DM5010()) -> Part:
    bell_l = cfg.motor_l - cfg.driver_l - cfg.gap_l

    # Rear driver/encoder housing: y = -driver_l .. 0.
    driver = (
        Pos(0, -cfg.driver_l / 2, 0)
        * Rot(90, 0, 0)
        * Cylinder(cfg.motor_d / 2, cfg.driver_l)
    )

    # Narrow seam between stator housing and rotor bell: y = -driver_l - gap_l .. -driver_l.
    seam = (
        Pos(0, -cfg.driver_l - cfg.gap_l / 2, 0)
        * Rot(90, 0, 0)
        * Cylinder(cfg.seam_d / 2, cfg.gap_l)
    )

    # Rotating outer bell: y = -motor_l .. -driver_l - gap_l.
    bell_center_y = -cfg.driver_l - cfg.gap_l - bell_l / 2
    bell = (
        Pos(0, bell_center_y, 0)
        * Rot(90, 0, 0)
        * Cylinder(cfg.motor_d / 2, bell_l)
    )

    motor = driver + seam + bell

    # Subtle front rotor flange groove (2.7 mm from rotor face, per side view).
    front_groove_y = -cfg.motor_l + 2.7
    motor -= (
        Pos(0, front_groove_y, 0)
        * Rot(90, 0, 0)
        * Cylinder(cfg.motor_d / 2 + 1.0, 0.35)
        - Pos(0, front_groove_y, 0)
        * Rot(90, 0, 0)
        * Cylinder(cfg.motor_d / 2 - 0.4, 0.5)
    )

    # Side BGC-CAN-DRV connector cutout on the -X side of the driver housing.
    conn_y = -cfg.driver_l + 1.5 + cfg.connector_l / 2
    conn_x = -cfg.motor_d / 2 + cfg.connector_depth / 2
    motor -= Pos(conn_x, conn_y, 0) * Box(
        cfg.connector_depth + 1.0, cfg.connector_l, cfg.connector_w
    )

    # Two rear housing cap screw counterbores at top/bottom (Z = ±21.5 mm).
    for z in (-cfg.motor_d / 2 + 3.0, cfg.motor_d / 2 - 3.0):
        motor -= (
            Pos(0, -1.25, z)
            * Rot(90, 0, 0)
            * Cylinder(2.25, 2.5)
        )

    # Stator mounting holes: 4 x M2.5 on a 20 x 20 mm square on the y = 0 face.
    half_s = cfg.stator_pitch / 2
    for x in (-half_s, half_s):
        for z in (-half_s, half_s):
            motor -= (
                Pos(x, -cfg.stator_hole_depth / 2, z)
                * Rot(90, 0, 0)
                * Cylinder(cfg.stator_hole_d / 2, cfg.stator_hole_depth)
            )

    # Rotor mounting holes: 4 x M3 on a Ø25 mm bolt circle on the y = -motor_l face.
    rotor_y = -cfg.motor_l
    r_bc = cfg.rotor_pitch / 2
    for x, z in ((0, r_bc), (0, -r_bc), (r_bc, 0), (-r_bc, 0)):
        motor -= (
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
    motor -= annulus

    # Hollow slip-ring through-bore (Ø12.7 mm) along the full motor axis.
    motor -= (
        Pos(0, -cfg.motor_l / 2, 0)
        * Rot(90, 0, 0)
        * Cylinder(cfg.bore_d / 2, cfg.motor_l + 2.0)
    )

    return motor


def parts(cfg: DM5010 = DM5010()) -> dict[str, Part]:
    return {"dm5010": build(cfg)}


def main() -> None:
    from export import export

    export(build(), "dm5010")


if __name__ == "__main__":
    main()
