"""Read the MicroSpora encoder output and summarise it.

Run it while you turn the shaft (or wave a magnet over the sensor), then read
the summary: a healthy sensor gives a smooth monotonic angle, and the 1x
component of the residual is magnet eccentricity.

    python tools/encoder_probe.py                 # 15 s, /dev/ttyACM0
    python tools/encoder_probe.py --seconds 30
"""

from __future__ import annotations

import argparse
import math
import re
import statistics
import time

import serial

LINE = re.compile(r"angle:\s*(-?\d+\.?\d*)\s+velocity:\s*(-?\d+\.?\d*)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", default="/dev/ttyACM0")
    parser.add_argument("--baud", type=int, default=250000)
    parser.add_argument("--seconds", type=float, default=15.0)
    args = parser.parse_args()

    angles: list[float] = []
    with serial.Serial(args.port, args.baud, timeout=0.2) as port:
        print(f"reading {args.port} for {args.seconds:.0f} s; turn the shaft slowly")
        deadline = time.time() + args.seconds
        while time.time() < deadline:
            line = port.readline().decode("ascii", "replace").strip()
            match = LINE.search(line)
            if not match:
                continue
            angle, velocity = float(match.group(1)), float(match.group(2))
            angles.append(angle)
            if len(angles) % 5 == 0:
                print(f"  angle {angle:+.3f} rad  velocity {velocity:+.3f} rad/s")

    if len(angles) < 3:
        print("no encoder samples: is the firmware in MODE_ENCODER?")
        return 1

    # Unwrap so a multi-turn sweep is visible as a monotonic ramp.
    unwrapped = [angles[0]]
    for previous, current in zip(angles, angles[1:]):
        delta = current - previous
        while delta > math.pi:
            delta -= 2 * math.pi
        while delta < -math.pi:
            delta += 2 * math.pi
        unwrapped.append(unwrapped[-1] + delta)

    steps = [b - a for a, b in zip(unwrapped, unwrapped[1:])]
    largest = max(steps, key=abs)
    mean_speed = (unwrapped[-1] - unwrapped[0]) / args.seconds

    print("\nsummary")
    print(f"  samples          {len(angles)}")
    print(f"  raw range        {min(angles):+.3f} .. {max(angles):+.3f} rad")
    print(f"  net rotation     {unwrapped[-1] - unwrapped[0]:+.3f} rad "
          f"({(unwrapped[-1] - unwrapped[0]) / (2 * math.pi):+.2f} turns)")
    print(f"  mean speed       {mean_speed:+.3f} rad/s")
    print(f"  largest step     {largest:+.4f} rad "
          f"({math.degrees(largest):+.2f} deg) between samples")
    if len(steps) > 2:
        print(f"  step noise       {statistics.pstdev(steps):.4f} rad")
    if abs(unwrapped[-1] - unwrapped[0]) < 0.05:
        print("\n  the shaft barely moved: rotate it through at least one full turn")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
