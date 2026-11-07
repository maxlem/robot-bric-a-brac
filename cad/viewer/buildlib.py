"""Shared build logic for the CLI and the long-lived worker.

Imports build123d once. ``build_all`` drops the project's modules on file-save
rebuilds so source edits are picked up without restarting the process, and
incrementally rebuilds only modified modules when parameter sliders or
spreadsheet formulas are updated.

A fixture can expose:

    parts(cfg=...)      -> dict[str, Part]                     printable parts
    assemblies(cfg=...) -> dict[str, list[tuple[str, Part, str]]]
                                                               (name, part, colour)

Assembly components are exported with an ``<assembly>__`` prefix so they can
be positioned in a common frame without clashing with the flat parts.
"""

from __future__ import annotations

import importlib
import inspect
import struct
import sys
import time
import traceback
from pathlib import Path
from typing import Any

from build123d import export_stl

from params import ParamMatrix, find_config_class

CAD = Path(__file__).resolve().parents[1]
OUT = CAD / "build" / "viewer"

# Every module that exposes parts() and optionally assemblies().
MODULES = [
    "fixtures.motor_5010",
    "fixtures.drone_stand",
    "fixtures.dm5010_mount",
]

MATRIX = ParamMatrix()
_MODULE_CACHE: dict[str, tuple[list[dict], list[dict]]] = {}
_CFG_CACHE: dict[str, Any] = {}
_MESH_CACHE: dict[str, tuple[Any, dict]] = {}

_STATIC_REF_NAMES = {
    "drone_sensor_microspora",
    "drone_stand_microspora__microspora",
    "drone_stand_microspora__encoder",
    "drone_stand_microspora__components",
}


def triangle_count(path: Path) -> int:
    """Triangle count from a binary STL header."""
    with path.open("rb") as f:
        header = f.read(84)
    if len(header) < 84:
        return 0
    return struct.unpack("<I", header[80:84])[0]


def _drop_project_modules() -> None:
    """Forget the project's fixture modules so the next import sees the edits."""
    for name, module in list(sys.modules.items()):
        if (
            name in ("viewer", "params", "reference.microspora", "__main__")
            or name.startswith("viewer.")
        ):
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


def _ref_pose_key(cfg: Any) -> tuple[Any, ...] | None:
    if cfg is None:
        return None
    fields = (
        "base_t",
        "motor_plate_h",
        "motor_plate_t",
        "microspora_recess_d",
        "microspora_offset_x",
        "microspora_offset_y",
    )
    if all(hasattr(cfg, f) for f in fields):
        return tuple(getattr(cfg, f) for f in fields)
    return None


def _export(
    module: str,
    name: str,
    part,
    prefix: str = "",
    pose_key: Any = None,
) -> dict:
    started = time.perf_counter()
    try:
        OUT.mkdir(parents=True, exist_ok=True)
        full_name = f"{prefix}{name}"
        stl = OUT / f"{full_name}.stl"
        if (
            full_name in _STATIC_REF_NAMES
            and pose_key is not None
            and full_name in _MESH_CACHE
            and _MESH_CACHE[full_name][0] == pose_key
            and stl.exists()
        ):
            cached = dict(_MESH_CACHE[full_name][1])
            cached["duration_ms"] = 0.0
            return cached

        export_stl(part, str(stl))
        bb = part.bounding_box()
        info = {
            "module": module,
            "name": name,
            "status": "ok",
            "duration_ms": round((time.perf_counter() - started) * 1000, 1),
            "volume_mm3": round(part.volume, 1),
            "bbox": [round(v, 2) for v in (bb.size.X, bb.size.Y, bb.size.Z)],
            "bbox_min": [round(v, 2) for v in (bb.min.X, bb.min.Y, bb.min.Z)],
            "bbox_max": [round(v, 2) for v in (bb.max.X, bb.max.Y, bb.max.Z)],
            "triangles": triangle_count(stl),
            "mesh": f"/api/mesh/{full_name}.stl",
        }
        if full_name in _STATIC_REF_NAMES and pose_key is not None:
            _MESH_CACHE[full_name] = (pose_key, dict(info))
        return info
    except Exception:
        return _error(module, name, started)


def _export_assembly(
    module: str, name: str, components, pose_key: Any = None
) -> dict:
    started = time.perf_counter()
    comps = []
    for comp_name, part, color in components:
        info = _export(
            module, comp_name, part, prefix=f"{name}__", pose_key=pose_key
        )
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


def _call_with_cfg(fn, cfg: Any, all_configs: dict[str, Any]):
    if cfg is None:
        return fn()
    sig = inspect.signature(fn)
    kwargs: dict[str, Any] = {}
    params = list(sig.parameters.values())
    if not params:
        return fn()
    if "cfg" in sig.parameters:
        kwargs["cfg"] = cfg
    else:
        kwargs[params[0].name] = cfg
    if "motor_cfg" in sig.parameters and "fixtures.motor_5010" in all_configs:
        kwargs["motor_cfg"] = all_configs["fixtures.motor_5010"]
    return fn(**kwargs)


def build_module(
    module_name: str,
    cfg: Any = None,
    all_configs: dict[str, Any] | None = None,
) -> tuple[list[dict], list[dict]]:
    started = time.perf_counter()
    all_configs = all_configs or {}
    pose_key = _ref_pose_key(cfg)
    try:
        module = importlib.import_module(module_name)
        parts = _call_with_cfg(module.parts, cfg, all_configs)
    except Exception:
        return [_error(module_name, module_name.rsplit(".", 1)[-1], started)], []

    results = [
        _export(module_name, name, part, pose_key=pose_key)
        for name, part in parts.items()
    ]

    assemblies: list[dict] = []
    if hasattr(module, "assemblies"):
        try:
            asm_dict = _call_with_cfg(module.assemblies, cfg, all_configs)
            for asm_name, components in asm_dict.items():
                assemblies.append(
                    _export_assembly(
                        module_name, asm_name, components, pose_key=pose_key
                    )
                )
        except Exception:
            assemblies.append(_error(module_name, "assembly", started))

    return results, assemblies


def build_all(
    reload_modules: bool = True,
    param_mutation: dict[str, Any] | None = None,
) -> dict:
    started = time.perf_counter()
    if param_mutation is not None and param_mutation.get("action") == "sync_python":
        reload_modules = True

    if reload_modules:
        _drop_project_modules()
        _MODULE_CACHE.clear()
        _CFG_CACHE.clear()

    module_classes: dict[str, type] = {}
    for module_name in MODULES:
        try:
            mod = importlib.import_module(module_name)
            cls = find_config_class(mod)
            if cls is not None:
                module_classes[module_name] = cls
        except Exception:
            pass

    if param_mutation is not None:
        MATRIX.apply_mutation(param_mutation, module_classes=module_classes)
        if param_mutation.get("action") == "sync_python":
            _drop_project_modules()
            _MODULE_CACHE.clear()
            _CFG_CACHE.clear()
            module_classes.clear()
            for module_name in MODULES:
                try:
                    mod = importlib.import_module(module_name)
                    cls = find_config_class(mod)
                    if cls is not None:
                        module_classes[module_name] = cls
                except Exception:
                    pass

    configs, params_state = MATRIX.evaluate(module_classes)

    parts: list[dict] = []
    assemblies: list[dict] = []
    for module_name in MODULES:
        cfg = configs.get(module_name)
        if module_name == "fixtures.drone_stand":
            cache_sig = (cfg, configs.get("fixtures.motor_5010"))
        else:
            cache_sig = (cfg,)

        if (
            not reload_modules
            and module_name in _MODULE_CACHE
            and _CFG_CACHE.get(module_name) == cache_sig
        ):
            module_parts, module_assemblies = _MODULE_CACHE[module_name]
        else:
            module_parts, module_assemblies = build_module(
                module_name, cfg=cfg, all_configs=configs
            )
            _MODULE_CACHE[module_name] = (module_parts, module_assemblies)
            _CFG_CACHE[module_name] = cache_sig

        parts.extend(module_parts)
        assemblies.extend(module_assemblies)

    return {
        "built_at": time.time(),
        "duration_ms": round((time.perf_counter() - started) * 1000, 1),
        "parts": parts,
        "assemblies": assemblies,
        "params": params_state,
    }
