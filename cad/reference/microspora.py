"""The real MicroSpora PCB, from the official STEP model.

Source: https://github.com/simplefoc/SimpleFOC-microspora/tree/main/3d%20model

The STEP is 26 MB and takes ~20 s to import, so it is downloaded once to
``cad/build/reference/`` and reduced to the PCB solid (1.6 MB STL). The
components are dropped; the board outline, holes, and slots are kept.

    cd cad && .venv/bin/python -m reference.microspora
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from build123d import export_stl, import_stl, import_step

CAD = Path(__file__).resolve().parents[1]
REF = CAD / "build" / "reference"
STEP = REF / "microspora.step"
STL = REF / "microspora_pcb.stl"

URL = (
    "https://raw.githubusercontent.com/simplefoc/SimpleFOC-microspora/"
    "main/3d%20model/3D_MicroSpora_Board_4layer_2026-08-18.step"
)


def ensure() -> Path:
    """Return the PCB STL, building it from the STEP if needed."""
    if STL.exists():
        return STL

    REF.mkdir(parents=True, exist_ok=True)
    if not STEP.exists():
        print(f"downloading {URL}", file=sys.stderr)
        subprocess.run(["curl", "-sSL", "-o", str(STEP), URL], check=True)

    print("importing STEP (about 20 s)", file=sys.stderr)
    shape = import_step(str(STEP))
    pcb = max(shape.solids(), key=lambda s: s.volume)
    export_stl(pcb, str(STL))
    return STL


def board():
    """The PCB as a mesh, in the STEP frame (x width, y height, z thickness)."""
    return import_stl(str(ensure()))


def parts() -> dict:
    return {"microspora_pcb": board()}


def main() -> None:
    path = ensure()
    print(path)


if __name__ == "__main__":
    main()
