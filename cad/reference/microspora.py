"""The real MicroSpora PCB, from the official STEP model.

Source: https://github.com/simplefoc/SimpleFOC-microspora/tree/main/3d%20model

The STEP is 26 MB and takes ~20 s to import, so it is downloaded once to
``cad/build/reference/`` and reduced to the PCB solid (1.6 MB STL) and the
MT6701 encoder chip (U8). The other components are dropped; the board
outline, holes, and slots are kept.

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
PCB_STL = REF / "microspora_pcb.stl"
ENC_STL = REF / "microspora_encoder.stl"

URL = (
    "https://raw.githubusercontent.com/simplefoc/SimpleFOC-microspora/"
    "main/3d%20model/3D_MicroSpora_Board_4layer_2026-08-18.step"
)


def _find(node, prefix: str):
    """Depth-first search for a named node in the STEP tree."""
    if node.label.startswith(prefix):
        return node
    for child in getattr(node, "children", []):
        found = _find(child, prefix)
        if found is not None:
            return found
    return None


def _build() -> None:
    REF.mkdir(parents=True, exist_ok=True)
    if not STEP.exists():
        print(f"downloading {URL}", file=sys.stderr)
        subprocess.run(["curl", "-sSL", "-o", str(STEP), URL], check=True)

    print("importing STEP (about 20 s)", file=sys.stderr)
    shape = import_step(str(STEP))
    pcb = max(shape.solids(), key=lambda s: s.volume)
    export_stl(pcb, str(PCB_STL))

    encoder = _find(shape, "U8~")
    if encoder is not None:
        export_stl(encoder, str(ENC_STL))


def ensure() -> Path:
    """Return the PCB STL, building it from the STEP if needed."""
    if not PCB_STL.exists() or not ENC_STL.exists():
        _build()
    return PCB_STL


def board():
    """The PCB as a mesh, in the STEP frame (x width, y height, z thickness)."""
    return import_stl(str(ensure()))


def encoder():
    """The MT6701 (U8) as a mesh, in the STEP frame."""
    ensure()
    return import_stl(str(ENC_STL))


def parts() -> dict:
    return {"microspora_pcb": board(), "microspora_encoder": encoder()}


def main() -> None:
    print(ensure())
    print(ENC_STL)


if __name__ == "__main__":
    main()
