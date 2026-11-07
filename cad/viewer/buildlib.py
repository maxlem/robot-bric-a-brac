"""Shared build logic for the CLI and the long-lived worker.

Imports build123d once. ``build_all`` drops the project's modules before each
run so edits are picked up without restarting the process.

A fixture can expose:

    parts()      -> dict[str, Part]                     printable parts
    assemblies() -> dict[str, list[tuple[str, Part, str]]]
                                                        (name, part, colour)

Assembly components are exported with an ``<assembly>__`` prefix so they can
be positioned in a common frame without clashing with the flat parts.
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

# Every module that exposes parts() and optionally assemblies().
MODULES = [
    "fixtures.motor_5010",
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


def _export(module: str, name: str, part, prefix: str = "") -> dict:
    started = time.perf_counter()
    try:
        OUT.mkdir(parents=True, exist_ok=True)
        stl = OUT / f"{prefix}{name}.stl"
        export_stl(part, str(stl))
        bb = part.bounding_box()
        return {
            "module": module,
            "name": name,
            "status": "ok",
            "duration_ms": round((time.perf_counter() - started) * 1000, 1),
            "volume_mm3": round(part.volume, 1),
            "bbox": [round(v, 2) for v in (bb.size.X, bb.size.Y, bb.size.Z)],
            "bbox_min": [round(v, 2) for v in (bb.min.X, bb.min.Y, bb.min.Z)],
            "bbox_max": [round(v, 2) for v in (bb.max.X, bb.max.Y, bb.max.Z)],
            "triangles": triangle_count(stl),
            "mesh": f"/api/mesh/{prefix}{name}.stl",
        }
    except Exception:
        return _error(module, name, started)


def _export_assembly(module: str, name: str, components) -> dict:
    started = time.perf_counter()
    comps = []
    for comp_name, part, color in components:
        info = _export(module, comp_name, part, prefix=f"{name}__")
        info["color"] = color
        comps.append(info)

    ok = [c for c in comps if c["status"] == "ok"]
    if ok:
        mins = [min(c["bbox_min"][i] for c in ok) for i in range(3)]
        maxs = [max(c["bbox_max"][i] for c in ok) for i in range(3)]
        bbox = [round(maxs[i] - mins[i], 2) for i in range(3)]
        volume = round(sum(c["volume_mm3"] for c in ok), 1)
    else:
        bbox = [0.0, 0.0, 0.0]
        volume = 0.0

    return {
        "module": module,
        "name": name,
        "status": "ok" if len(ok) == len(comps) else "error",
        "duration_ms": round((time.perf_counter() - started) * 1000, 1),
        "volume_mm3": volume,
        "bbox": bbox,
        "components": comps,
    }


def build_module(module_name: str) -> tuple[list[dict], list[dict]]:
    started = time.perf_counter()
    try:
        module = importlib.import_module(module_name)
        parts = module.parts()
    except Exception:
        return [_error(module_name, module_name.rsplit(".", 1)[-1], started)], []

    results = [_export(module_name, name, part) for name, part in parts.items()]

    assemblies: list[dict] = []
    if hasattr(module, "assemblies"):
        try:
            for asm_name, components in module.assemblies().items():
                assemblies.append(_export_assembly(module_name, asm_name, components))
        except Exception:
            assemblies.append(_error(module_name, "assembly", started))

    return results, assemblies


def build_all() -> dict:
    started = time.perf_counter()
    _drop_project_modules()
    parts: list[dict] = []
    assemblies: list[dict] = []
    for module_name in MODULES:
        module_parts, module_assemblies = build_module(module_name)
        parts.extend(module_parts)
        assemblies.extend(module_assemblies)
    return {
        "built_at": time.time(),
        "duration_ms": round((time.perf_counter() - started) * 1000, 1),
        "parts": parts,
        "assemblies": assemblies,
    }
