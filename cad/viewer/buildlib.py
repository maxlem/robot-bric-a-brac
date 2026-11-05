"""Shared build logic for the CLI and the long-lived worker.

Imports build123d once. ``build_all`` drops the project's modules before each
run so edits are picked up without restarting the process.
"""

from __future__ import annotations

import importlib
import struct
import sys
import time
import traceback
from pathlib import Path

from build123d import export_stl

CAD = Path(__file__).resolve().parents[1]
OUT = CAD / "build" / "viewer"

# Every module that exposes parts() -> dict[str, Part].
MODULES = [
    "fixtures.drone_stand",
    "fixtures.dm5010_mount",
]


def triangle_count(path: Path) -> int:
    """Triangle count from a binary STL header."""
    with path.open("rb") as f:
        header = f.read(84)
    if len(header) < 84:
        return 0
    return struct.unpack("<I", header[80:84])[0]


def _drop_project_modules() -> None:
    """Forget the project's modules so the next import sees the edits."""
    for name, module in list(sys.modules.items()):
        if name == "viewer" or name.startswith("viewer.") or name == "__main__":
            continue
        path = getattr(module, "__file__", None)
        if not path:
            continue
        resolved = Path(path).resolve()
        if ".venv" in resolved.parts:
            continue
        if resolved.is_relative_to(CAD):
            del sys.modules[name]
    importlib.invalidate_caches()


def _error(module: str, name: str, started: float) -> dict:
    return {
        "module": module,
        "name": name,
        "status": "error",
        "error": traceback.format_exc(),
        "duration_ms": round((time.perf_counter() - started) * 1000, 1),
    }


def build_module(module_name: str) -> list[dict]:
    started = time.perf_counter()
    try:
        module = importlib.import_module(module_name)
        parts = module.parts()
    except Exception:
        return [_error(module_name, module_name.rsplit(".", 1)[-1], started)]

    results: list[dict] = []
    for name, part in parts.items():
        t0 = time.perf_counter()
        try:
            OUT.mkdir(parents=True, exist_ok=True)
            stl = OUT / f"{name}.stl"
            export_stl(part, str(stl))
            bb = part.bounding_box()
            results.append(
                {
                    "module": module_name,
                    "name": name,
                    "status": "ok",
                    "duration_ms": round((time.perf_counter() - t0) * 1000, 1),
                    "volume_mm3": round(part.volume, 1),
                    "bbox": [round(v, 2) for v in (bb.size.X, bb.size.Y, bb.size.Z)],
                    "triangles": triangle_count(stl),
                    "mesh": f"/api/mesh/{name}.stl",
                }
            )
        except Exception:
            results.append(_error(module_name, name, t0))
    return results


def build_all() -> dict:
    started = time.perf_counter()
    _drop_project_modules()
    parts: list[dict] = []
    for module_name in MODULES:
        parts.extend(build_module(module_name))
    return {
        "built_at": time.time(),
        "duration_ms": round((time.perf_counter() - started) * 1000, 1),
        "parts": parts,
    }
