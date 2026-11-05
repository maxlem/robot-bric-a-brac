"""LEGO Technic helpers.

The printed parts interface with LEGO beams, axles, and pins. These helpers
produce the hole patterns and the simple plates used by the fixtures.

All dimensions are millimetres.
"""

from __future__ import annotations

from build123d import Box, Cylinder, Part, Pos

HOLE_D = 4.8
PITCH = 8.0
PLATE_T = 3.2
BEAM_T = 9.6

# Printed holes are slightly larger than the LEGO nominal so the parts fit.
AXLE_HOLE_D = 4.9
PIN_HOLE_D = 4.85


def hole_centers(length_studs: int, width_studs: int = 1) -> list[tuple[float, float]]:
    """Hole centres on the 8 mm grid, centred on the origin."""
    xs = [(i - (length_studs - 1) / 2) * PITCH for i in range(length_studs)]
    ys = [(j - (width_studs - 1) / 2) * PITCH for j in range(width_studs)]
    return [(x, y) for x in xs for y in ys]


def plate(
    length_studs: int,
    width_studs: int = 1,
    thickness: float = PLATE_T,
    hole_d: float = HOLE_D,
) -> Part:
    """A rectangular plate with a LEGO hole grid."""
    length = length_studs * PITCH
    width = width_studs * PITCH
    part = Box(length, width, thickness)
    for x, y in hole_centers(length_studs, width_studs):
        part -= Pos(x, y, 0) * Cylinder(hole_d / 2, thickness + 2)
    return part


def axle_hole(d: float = AXLE_HOLE_D, depth: float = 20.0) -> Part:
    return Cylinder(d / 2, depth)


def pin_hole(d: float = PIN_HOLE_D, depth: float = 20.0) -> Part:
    return Cylinder(d / 2, depth)


def main() -> None:
    p = plate(5, 1)
    print(f"plate 5x1: {p.volume:.1f} mm^3, {len(hole_centers(5, 1))} holes")


if __name__ == "__main__":
    main()
