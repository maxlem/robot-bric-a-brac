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
    bell_h: float = 23.0  # overall length 26 mm with the flange
    shaft_d: float = 4.0
    shaft_l: float = 4.0
    stator_pitch_x: float = 19.0
    stator_pitch_y: float = 16.0
    stator_hole_d: float = 3.0
    rotor_pitch: float = 12.0
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

    # Stator mounting holes, through the flange.
    for x in (-cfg.stator_pitch_x / 2, cfg.stator_pitch_x / 2):
        for z in (-cfg.stator_pitch_y / 2, cfg.stator_pitch_y / 2):
            motor -= Pos(x, -cfg.flange_t / 2, z) * Rot(90, 0, 0) * Cylinder(
                cfg.stator_hole_d / 2, cfg.flange_t + 2
            )

    # Rotor face holes, into the front of the bell.
    rotor_y = -cfg.flange_t - cfg.bell_h
    for x in (-cfg.rotor_pitch / 2, cfg.rotor_pitch / 2):
        for z in (-cfg.rotor_pitch / 2, cfg.rotor_pitch / 2):
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
