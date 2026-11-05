"""Kinematic skeleton for the biped.

Every part reads its dimensions from here. Change a link length and the
fixtures, links, and joint modules regenerate.

Units are metres and degrees at the boundary; the CAD helpers convert to mm.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Joint:
    name: str
    rom_deg: tuple[float, float]
    belt_ratio: float = 1.0
    motor: str = ""


@dataclass(frozen=True)
class Leg:
    # Link lengths, hip to knee, knee to ankle, ankle to toe.
    L_thigh: float = 0.075
    L_shank: float = 0.075
    L_foot: float = 0.040

    # Joints.
    hip_pitch: Joint = field(
        default_factory=lambda: Joint("hip_pitch", (-30.0, 60.0), 3.0, "DM5015")
    )
    knee: Joint = field(
        default_factory=lambda: Joint("knee", (0.0, 120.0), 3.0, "DM5015")
    )
    ankle: Joint = field(
        default_factory=lambda: Joint("ankle", (-30.0, 30.0), 4.0, "DM5010")
    )

    # Belt and pulley.
    belt_pitch_mm: float = 3.0  # GT3
    belt_width_mm: float = 9.0
    motor_pulley_teeth: int = 20
    joint_pulley_teeth: int = 60

    @property
    def pitch_diameter_motor_mm(self) -> float:
        return self.motor_pulley_teeth * self.belt_pitch_mm / 3.141592653589793

    @property
    def pitch_diameter_joint_mm(self) -> float:
        return self.joint_pulley_teeth * self.belt_pitch_mm / 3.141592653589793

    @property
    def belt_ratio(self) -> float:
        return self.joint_pulley_teeth / self.motor_pulley_teeth


LEG = Leg()


def main() -> None:
    leg = LEG
    print(f"thigh {leg.L_thigh * 1000:.1f} mm")
    print(f"shank {leg.L_shank * 1000:.1f} mm")
    print(f"foot  {leg.L_foot * 1000:.1f} mm")
    print(f"belt  GT{leg.belt_pitch_mm:g} {leg.belt_width_mm:g} mm, ratio {leg.belt_ratio:g}:1")
    print(f"motor pulley PD {leg.pitch_diameter_motor_mm:.1f} mm")
    print(f"joint pulley PD {leg.pitch_diameter_joint_mm:.1f} mm")
    for joint in (leg.hip_pitch, leg.knee, leg.ankle):
        print(f"{joint.name:10s} ROM {joint.rom_deg}  belt {joint.belt_ratio:g}:1  {joint.motor}")


if __name__ == "__main__":
    main()
