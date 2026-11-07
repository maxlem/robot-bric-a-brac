"""Reference model of the Flycat 5010-360KV high-torque brushless outrunner.

Not a printable part: a reference model of the motor's envelope, 4-spoke
ventilated rotor bell, 12-slot stator, and both bolt patterns.

Sources:
    https://www.flyrobo.in/5010-360kv-high-torque-brushless-motor
    hardware/datasheets/5010-360kv-brushless-motor.pdf

Key dimensions:
    5010-360KV:   Ø50 mm rotor bell, 12N14P, 21.3 mm mounting face to rotor face
    Stator boss:  Ø25 mm rear mounting boss (7.3 mm protrusion behind bell skirt)
    Stator side:  4 × M3 on a 19 × 16 mm cross pattern
    Rotor side:   4 × M3 on a Ø12 mm bolt circle, 4 fan-style cooling cutouts
    Shaft:        Ø4 mm (1.50 mm front & rear stubs, caliper measured)

Local frame: the stator mounting face is at y = 0 and the motor extends toward -Y
(rotor face at y = -21.3 mm).
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
class Flycat5010(ParamConfig):
    CONSTANTS = ("*",)  # Reference hardware envelope & caliper measurements

    # Envelope and stator boss.
    boss_d: float = 25.0  # rear stator mounting hub OD (mm)
    boss_h: float = 7.3  # rear hub protrusion behind rotor bell skirt (mm)
    bell_d: float = 50.0  # outer rotor bell diameter (mm)
    bell_h: float = 14.0  # rotor bell axial length (7.3 + 14.0 = 21.3 mm total)
    bell_wall_t: float = 2.8  # rotor bell radial rim + magnet ring thickness (mm)
    bell_face_t: float = 2.5  # rotor front face web thickness (mm)
    rotor_hub_d: float = 18.0  # central hub OD on rotor front face (mm)
    spoke_w: float = 5.5  # width of the 4 radial rotor spokes (mm)

    # Internal 12-slot stator core.
    stator_d: float = 41.0
    stator_h: float = 10.0

    # Shaft (caliper measurements).
    shaft_d: float = 4.0
    shaft_l: float = 1.50  # front stub beyond rotor face (mm)
    through_shaft_l: float = 1.50  # rear stub behind stator mounting face (mm)

    # Bolt patterns.
    stator_pitch_19: float = 19.0  # vertical M3 pair (mm)
    stator_pitch_16: float = 16.0  # horizontal M3 pair (mm)
    stator_hole_d: float = 3.0  # M3 tap on stator boss (mm)
    rotor_pitch: float = 12.0  # rotor M3 bolt circle diameter (mm)
    rotor_hole_d: float = 3.0  # 4 x M3 on Ø12 mm bolt circle (mm)

    # Electrical specifications.
    pole_pairs: int = 7  # 12N14P configuration (7 pole pairs)
    kv_rpm_per_v: float = 360.0  # speed constant Kv (rpm/V)
    kt_nm_per_a: float = 0.0265  # theoretical torque constant 60/(2*pi*Kv) (Nm/A)
    nominal_voltage_v: float = 14.8  # 4S LiPo nominal (2S-6S compatible)
    max_current_a: float = 10.7  # max tested current at 14 V with 1665 prop (A)
    max_power_w: float = 149.8  # max tested electrical power at 14 V (W)
    mass_g: float = 92.0  # bare motor mass (g)

    @property
    def height(self) -> float:
        """Mounting face (y = 0) to rotor face (y = -21.3 mm)."""
        return self.boss_h + self.bell_h


@functools.lru_cache(maxsize=8)
def build(cfg: Flycat5010 = Flycat5010()) -> Part:
    total_h = cfg.boss_h + cfg.bell_h

    # Rear stator boss + internal hub column: y = -( total_h - bell_face_t ) .. 0.
    column_h = total_h - cfg.bell_face_t
    boss = (
        Pos(0, -column_h / 2, 0)
        * Rot(90, 0, 0)
        * Cylinder(cfg.boss_d / 2, column_h)
    )

    # Rear bearing / C-clip recess on the y = 0 mounting face.
    boss -= (
        Pos(0, -0.6, 0)
        * Rot(90, 0, 0)
        * Cylinder(5.5, 1.2)
    )

    # Internal 12-pole stator stack inside the bell: y = -boss_h - stator_h - 1.0 .. -boss_h - 1.0.
    stator_y = -cfg.boss_h - 1.0 - cfg.stator_h / 2
    stator = (
        Pos(0, stator_y, 0)
        * Rot(90, 0, 0)
        * Cylinder(cfg.stator_d / 2, cfg.stator_h)
    )
    for i in range(12):
        angle = i * 30.0 + 15.0
        slot_cut = (
            Rot(0, angle, 0)
            * Pos(cfg.stator_d / 2 - 3.5, stator_y, 0)
            * Box(9.0, cfg.stator_h + 0.5, 2.8)
        )
        stator -= slot_cut

    # Rotor bell outer cylinder: y = -total_h .. -boss_h.
    bell_y = -cfg.boss_h - cfg.bell_h / 2
    bell = (
        Pos(0, bell_y, 0)
        * Rot(90, 0, 0)
        * Cylinder(cfg.bell_d / 2, cfg.bell_h)
    )
    # Hollow interior of the rotor bell behind the front face.
    cavity_h = cfg.bell_h - cfg.bell_face_t
    cavity_r = cfg.bell_d / 2 - cfg.bell_wall_t
    bell -= (
        Pos(0, -cfg.boss_h - cavity_h / 2, 0)
        * Rot(90, 0, 0)
        * Cylinder(cavity_r, cavity_h + 0.2)
    )

    # 4 fan-style cooling windows on the rotor front face (leaving rotor_hub_d,
    # outer rim, and 4 radial spokes at 45°).
    front_y = -total_h + cfg.bell_face_t / 2
    annulus_cut = (
        Pos(0, front_y, 0)
        * Rot(90, 0, 0)
        * Cylinder(cavity_r - 1.2, cfg.bell_face_t + 0.4)
        - Pos(0, front_y, 0)
        * Rot(90, 0, 0)
        * Cylinder(cfg.rotor_hub_d / 2, cfg.bell_face_t + 0.6)
    )
    for angle in (45.0, 135.0):
        spoke = (
            Rot(0, angle, 0)
            * Pos(0, front_y, 0)
            * Box(cfg.bell_d, cfg.bell_face_t + 0.8, cfg.spoke_w)
        )
        annulus_cut -= spoke
    bell -= annulus_cut

    motor = boss + stator + bell

    # Stator mounting holes: 2 on the Ø19 circle (vertical) and 2 on the
    # Ø16 circle (horizontal), blind into the boss.
    for x, z in (
        (0, cfg.stator_pitch_19 / 2),
        (0, -cfg.stator_pitch_19 / 2),
        (cfg.stator_pitch_16 / 2, 0),
        (-cfg.stator_pitch_16 / 2, 0),
    ):
        motor -= (
            Pos(x, -3.5, z)
            * Rot(90, 0, 0)
            * Cylinder(cfg.stator_hole_d / 2, 7.0)
        )

    # Rotor face holes: 4 x M3 on a Ø12 bolt circle.
    rotor_y = -total_h
    for x, z in (
        (0, cfg.rotor_pitch / 2),
        (0, -cfg.rotor_pitch / 2),
        (cfg.rotor_pitch / 2, 0),
        (-cfg.rotor_pitch / 2, 0),
    ):
        motor -= (
            Pos(x, rotor_y + 2.0, z)
            * Rot(90, 0, 0)
            * Cylinder(cfg.rotor_hole_d / 2, 4.0)
        )

    # Through-shaft: front stub plus rear stub behind the mounting face for
    # the stator-side magnet holder.
    shaft_front = rotor_y - cfg.shaft_l
    shaft_back = cfg.through_shaft_l
    motor += (
        Pos(0, (shaft_front + shaft_back) / 2, 0)
        * Rot(90, 0, 0)
        * Cylinder(cfg.shaft_d / 2, shaft_back - shaft_front)
    )

    return motor


def parts(cfg: Flycat5010 = Flycat5010()) -> dict[str, Part]:
    return {"flycat_5010": build(cfg)}


def main() -> None:
    from export import export

    export(build(), "flycat_5010")


if __name__ == "__main__":
    main()
