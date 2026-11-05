"""Simplified 5010 outrunner, for checking the mount.

Not a printable part: a reference model of the motor's envelope and its two
bolt patterns.

    5010: 50 mm stator, 10 mm tall, 4 mm shaft
    stator side: 4 x M3 on a 19 x 16 mm pattern
    rotor side:  4 x M2 on a 12 x 12 mm pattern

Local frame: the mounting face is at y = 0 and the motor extends toward -Y.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from build123d import Cylinder, Part, Pos, Rot

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@dataclass(frozen=True)
class Motor5010:
    stator_d: float = 50.0
    flange_t: float = 3.0
    bell_d: float = 52.0
    bell_h: float = 18.3  # mounting face to rotor face is 21.3 mm
    shaft_d: float = 4.0
    shaft_l: float = 4.7  # 26 mm overall
    stator_pitch_19: float = 19.0  # vertical pair
    stator_pitch_16: float = 16.0  # horizontal pair
    stator_hole_d: float = 3.0
    rotor_pitch: float = 12.0  # bolt circle
    rotor_hole_d: float = 2.0

    @property
    def height(self) -> float:
        """Mounting face to rotor face."""
        return self.flange_t + self.bell_h


def build(cfg: Motor5010 = Motor5010()) -> Part:
    # Mounting flange, y = -flange_t .. 0.
    flange = Pos(0, -cfg.flange_t / 2, 0) * Rot(90, 0, 0) * Cylinder(
        cfg.stator_d / 2, cfg.flange_t
    )

    # Rotor bell, y = -flange_t - bell_h .. -flange_t.
    bell = Pos(0, -cfg.flange_t - cfg.bell_h / 2, 0) * Rot(90, 0, 0) * Cylinder(
        cfg.bell_d / 2, cfg.bell_h
    )

    motor = flange + bell

    # Stator mounting holes: 2 on the Ø19 circle (vertical) and 2 on the
    # Ø16 circle (horizontal).
    for x, z in (
        (0, cfg.stator_pitch_19 / 2),
        (0, -cfg.stator_pitch_19 / 2),
        (cfg.stator_pitch_16 / 2, 0),
        (-cfg.stator_pitch_16 / 2, 0),
    ):
        motor -= Pos(x, -cfg.flange_t / 2, z) * Rot(90, 0, 0) * Cylinder(
            cfg.stator_hole_d / 2, cfg.flange_t + 2
        )

    # Rotor face holes: 4 on a Ø12 bolt circle.
    rotor_y = -cfg.flange_t - cfg.bell_h
    for x, z in (
        (0, cfg.rotor_pitch / 2),
        (0, -cfg.rotor_pitch / 2),
        (cfg.rotor_pitch / 2, 0),
        (-cfg.rotor_pitch / 2, 0),
    ):
        motor -= Pos(x, rotor_y + 2, z) * Rot(90, 0, 0) * Cylinder(
            cfg.rotor_hole_d / 2, 4
        )

    # Shaft stub, ending inside the magnet carrier.
    motor += Pos(0, rotor_y - cfg.shaft_l / 2, 0) * Rot(90, 0, 0) * Cylinder(
        cfg.shaft_d / 2, cfg.shaft_l
    )

    return motor


def parts() -> dict[str, Part]:
    return {"motor_5010": build()}


def main() -> None:
    from export import export

    export(build(), "motor_5010")


if __name__ == "__main__":
    main()
