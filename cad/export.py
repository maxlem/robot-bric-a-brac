"""STEP + STL export for the CAD parts."""

from __future__ import annotations

from pathlib import Path

from build123d import Part, export_step, export_stl

BUILD = Path(__file__).resolve().parent / "build"


def export(part: Part, name: str, out_dir: Path = BUILD) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    step = out_dir / f"{name}.step"
    stl = out_dir / f"{name}.stl"
    export_step(part, str(step))
    export_stl(part, str(stl))
    print(f"{name}: {step.name}, {stl.name}")
