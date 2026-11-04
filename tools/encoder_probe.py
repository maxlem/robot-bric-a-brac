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


def report_harmonics(unwrapped: list[float], times: list[float]) -> None:
    """Fit constant speed and report the periodic error, which is eccentricity."""
    count = len(unwrapped)
    span = unwrapped[-1] - unwrapped[0]
    if abs(span) < 2 * math.pi:
        print("\n  spin analysis needs at least one full revolution")
        return

    origin = times[0]
    ts = [t - origin for t in times]
    mean_t = sum(ts) / count
    mean_a = sum(unwrapped) / count
    numerator = sum((t - mean_t) * (a - mean_a) for t, a in zip(ts, unwrapped))
    denominator = sum((t - mean_t) ** 2 for t in ts)
    slope = numerator / denominator if denominator else 0.0
    intercept = mean_a - slope * mean_t
    residual = [a - (intercept + slope * t) for t, a in zip(ts, unwrapped)]

    print("\n  spin analysis (constant-speed fit)")
    print(f"    speed          {slope:+.3f} rad/s")
    print(f"    revolutions    {abs(span) / (2 * math.pi):.2f}")
    for order in range(1, 5):
        cos_part = 2 / count * sum(r * math.cos(order * a) for r, a in zip(residual, unwrapped))
        sin_part = 2 / count * sum(r * math.sin(order * a) for r, a in zip(residual, unwrapped))
        amplitude = math.hypot(cos_part, sin_part)
        label = "eccentricity" if order == 1 else ""
        print(f"    {order}x error     {math.degrees(amplitude):6.2f} deg  {label}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", default="/dev/ttyACM0")
    parser.add_argument("--baud", type=int, default=250000)
    parser.add_argument("--seconds", type=float, default=15.0)
    parser.add_argument(
        "--analyze-spin",
        action="store_true",
        help="fit the samples against constant speed and report harmonic error",
    )
    parser.add_argument(
        "--follow",
        action="store_true",
        help="print every sample until Ctrl+C, then print the summary",
    )
    args = parser.parse_args()

    angles: list[float] = []
    times: list[float] = []
    with serial.Serial(args.port, args.baud, timeout=0.2) as port:
        if args.follow:
            print(f"reading {args.port}; turn the shaft, Ctrl+C to stop")
        else:
            print(f"reading {args.port} for {args.seconds:.0f} s; turn the shaft slowly")
        deadline = float("inf") if args.follow else time.time() + args.seconds
        try:
            while time.time() < deadline:
                line = port.readline().decode("ascii", "replace").strip()
                match = LINE.search(line)
                if not match:
                    continue
                angle, velocity = float(match.group(1)), float(match.group(2))
                angles.append(angle)
                times.append(time.time())
                if args.follow or len(angles) % 5 == 0:
                    print(f"  angle {angle:+.3f} rad  velocity {velocity:+.3f} rad/s")
        except KeyboardInterrupt:
            pass

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
    elapsed = args.seconds if not args.follow else max(len(angles), 1) * 0.5
    mean_speed = (unwrapped[-1] - unwrapped[0]) / elapsed

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
    if args.analyze_spin:
        report_harmonics(unwrapped, times)

    if abs(unwrapped[-1] - unwrapped[0]) < 0.05:
        print("\n  the shaft barely moved: rotate it through at least one full turn")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
