"""Parameter exposition, schema introspection, and spreadsheet expression engine.

Decouples Python CAD configuration dataclasses from the web UI:

1. Any fixture config dataclass inherits from :class:`ParamConfig` (or is a
   standard ``@dataclass``).
2. :func:`extract_schema` introspects field types, default values, optional
   :func:`param` metadata, ``BINDINGS`` formulas, and source-code section/inline
   comments to produce a generic JSON schema.
3. :class:`ParamMatrix` maintains live parameter overrides, user-defined custom
   helper variables, and formula bindings (e.g. ``= holder_d + 1.0`` or
   cross-module ``= motor_5010.shaft_d + 0.1``), evaluating them in topological
   order via a safe AST math evaluator, auto-persisting every edit to disk,
   managing named presets, and syncing modified values/bindings back to Python
   source files on demand.
"""

from __future__ import annotations

import ast
import inspect
import json
import math
import operator
import re
from dataclasses import MISSING, dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any, ClassVar

CAD_DIR = Path(__file__).resolve().parent
PARAMS_STATE_FILE = CAD_DIR / "build" / "viewer" / "params_state.json"


def param(
    default: Any,
    *,
    min: float | None = None,
    max: float | None = None,
    step: float | None = None,
    unit: str = "mm",
    group: str = "",
    doc: str = "",
    expr: str | None = None,
    constant: bool = False,
) -> Any:
    """Attach optional UI bounds, unit, comment, default binding, or constant flag."""
    meta = {
        "min": min,
        "max": max,
        "step": step,
        "unit": unit,
        "group": group,
        "doc": doc,
        "expr": expr,
        "constant": constant,
    }
    return field(default=default, metadata=meta)


def const(
    default: Any,
    *,
    unit: str = "mm",
    group: str = "",
    doc: str = "",
) -> Any:
    """Declare a fixed physical/reference constant field (locked by default in UI)."""
    return param(default, unit=unit, group=group, doc=doc, constant=True)


@dataclass(frozen=True)
class ParamConfig:
    """Base class for parametric CAD configuration dataclasses.

    Subclasses can optionally define:
    - ``BINDINGS``: field name -> default spreadsheet expression (e.g. ``"= holder_d + 1.0"``)
    - ``CONSTANTS``: set/tuple of field names (or ``"*"``) that represent fixed
      hardware/PCB measurements (locked by default in the UI without a slider)
    - ``PART_GROUPS`` / ``PART_FIELDS``: per-part parameter scoping in the viewer.
    """

    BINDINGS: ClassVar[dict[str, str]] = {}
    CONSTANTS: ClassVar[set[str] | tuple[str, ...]] = ()
    PART_GROUPS: ClassVar[dict[str, list[str]]] = {}
    PART_FIELDS: ClassVar[dict[str, list[str]]] = {}


def _infer_bounds(val: float | int, is_int: bool) -> tuple[float, float, float]:
    """Infer sensible (min, max, step) slider bounds from a default numeric value."""
    if is_int:
        lo = 0 if val >= 0 else val * 3
        hi = max(int(abs(val) * 3), 10)
        return float(lo), float(hi), 1.0

    fval = float(val)
    if fval == 0.0:
        return -20.0, 20.0, 0.1
    if fval < 0.0:
        span = max(abs(fval) * 3.0, 5.0)
        return round(fval - span, 2), round(-fval + span, 2), 0.05

    if fval < 2.0:
        lo, hi, step = 0.0, round(max(fval * 4.0, 5.0), 2), 0.05
    elif fval < 10.0:
        lo, hi, step = 0.1, round(max(fval * 3.0, 15.0), 1), 0.1
    elif fval < 40.0:
        lo, hi, step = 1.0, round(fval * 2.5, 1), 0.2
    else:
        lo, hi, step = 2.0, round(fval * 2.5, 1), 0.5
    return lo, hi, step


def _parse_source_annotations(cls: type) -> dict[str, tuple[str, str]]:
    """Extract (group_header, inline_comment) per field from class source lines."""
    result: dict[str, tuple[str, str]] = {}
    try:
        lines, _ = inspect.getsourcelines(cls)
    except (OSError, TypeError):
        return result

    current_group = "General"
    comment_buffer: list[str] = []
    field_re = re.compile(r"^\s*([a-zA-Z_]\w*)\s*:\s*[^=]+=\s*(.+)$")

    for raw in lines:
        stripped = raw.strip()
        if not stripped:
            comment_buffer.clear()
            continue
        if stripped.startswith("#"):
            text = stripped.lstrip("#").strip()
            if text:
                comment_buffer.append(text)
            continue

        if comment_buffer:
            first_line = comment_buffer[0]
            head = re.split(r"[:.]", first_line, maxsplit=1)[0].strip()
            if head and len(head) <= 40:
                current_group = head
            comment_buffer.clear()

        m = field_re.match(raw)
        if m:
            fname = m.group(1)
            if fname in ("BINDINGS", "CONSTANTS", "PART_GROUPS", "PART_FIELDS"):
                continue
            rhs = m.group(2)
            inline_doc = ""
            if "#" in rhs:
                inline_doc = rhs.split("#", 1)[1].strip()
            result[fname] = (current_group, inline_doc)

    return result


def extract_schema(cls: type) -> list[dict[str, Any]]:
    """Build the generic field descriptor list for a dataclass config."""
    if not is_dataclass(cls):
        return []

    annotations = _parse_source_annotations(cls)
    bindings: dict[str, str] = getattr(cls, "BINDINGS", {}) or {}
    constants_cfg = set(getattr(cls, "CONSTANTS", ()) or ())
    all_constant = "*" in constants_cfg
    instance = cls()
    schema: list[dict[str, Any]] = []

    for f in fields(cls):
        if f.name.startswith("_") or f.name in (
            "BINDINGS",
            "CONSTANTS",
            "PART_GROUPS",
            "PART_FIELDS",
        ):
            continue
        default_val = getattr(instance, f.name, f.default)
        if default_val is MISSING:
            continue

        meta = dict(f.metadata) if f.metadata else {}
        group, inline_doc = annotations.get(f.name, ("General", ""))

        if isinstance(default_val, bool):
            ftype = "bool"
            lo, hi, step = 0.0, 1.0, 1.0
            unit = ""
        elif isinstance(default_val, int):
            ftype = "int"
            lo, hi, step = _infer_bounds(default_val, is_int=True)
            unit = meta.get("unit", "")
        elif isinstance(default_val, float):
            ftype = "float"
            lo, hi, step = _infer_bounds(default_val, is_int=False)
            unit = meta.get("unit", "mm")
        else:
            ftype = "str"
            lo, hi, step = 0.0, 0.0, 0.0
            unit = meta.get("unit", "")

        if meta.get("min") is not None:
            lo = float(meta["min"])
        if meta.get("max") is not None:
            hi = float(meta["max"])
        if meta.get("step") is not None:
            step = float(meta["step"])

        default_expr = meta.get("expr") or bindings.get(f.name)
        if default_expr is None:
            default_expr = str(default_val)

        is_const = bool(
            meta.get("constant") or all_constant or (f.name in constants_cfg)
        )

        schema.append(
            {
                "name": f.name,
                "type": ftype,
                "default": default_val,
                "default_expr": str(default_expr),
                "min": lo,
                "max": hi,
                "step": step,
                "unit": unit,
                "group": meta.get("group") or group,
                "doc": meta.get("doc") or inline_doc,
                "constant": is_const,
            }
        )

    return schema


def find_config_class(module: Any) -> type | None:
    """Find the primary ParamConfig or @dataclass configuration class in a module."""
    explicit = getattr(module, "CONFIG", None)
    if explicit is not None and is_dataclass(explicit):
        return explicit

    candidates: list[type] = []
    for _, obj in inspect.getmembers(module, inspect.isclass):
        if obj.__module__ != module.__name__ or obj is ParamConfig:
            continue
        if issubclass(obj, ParamConfig) or is_dataclass(obj):
            candidates.append(obj)

    for c in candidates:
        if issubclass(c, ParamConfig):
            return c
    return candidates[0] if candidates else None


# --- Safe AST expression evaluator -------------------------------------------

_SAFE_FUNCS: dict[str, Any] = {
    "min": min,
    "max": max,
    "abs": abs,
    "round": round,
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "atan2": math.atan2,
    "deg": math.degrees,
    "rad": math.radians,
    "floor": math.floor,
    "ceil": math.ceil,
}

_SAFE_CONSTS: dict[str, float] = {
    "pi": math.pi,
    "tau": math.tau,
    "e": math.e,
}

_BIN_OPS: dict[type, Any] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_UNARY_OPS: dict[type, Any] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def is_formula_expr(expr: str, ftype: str = "float") -> bool:
    """Return True if ``expr`` is a formula/binding rather than a plain literal."""
    s = str(expr).strip()
    if not s:
        return False
    if s.startswith("="):
        return True
    if ftype == "bool":
        return s.lower() not in ("true", "false", "0", "1")
    if ftype in ("float", "int"):
        try:
            float(s)
            return False
        except ValueError:
            return True
    return False


def _extract_refs(node: ast.AST, current_module: str | None) -> set[str]:
    """Return referenced symbol keys (``module.field`` or custom ``name``)."""
    refs: set[str] = set()

    def _visit(n: ast.AST) -> None:
        if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name):
            refs.add(f"{n.value.id}.{n.attr}")
            return
        if isinstance(n, ast.Call):
            # Visit call arguments only, not the function name identifier
            for arg in n.args:
                _visit(arg)
            return
        if isinstance(n, ast.Name):
            ident = n.id
            if ident in _SAFE_FUNCS or ident in _SAFE_CONSTS or ident in ("True", "False"):
                return
            refs.add(f"{current_module}.{ident}" if current_module else ident)
            return
        for child in ast.iter_child_nodes(n):
            _visit(child)

    _visit(node)
    return refs


def _eval_ast(
    node: ast.AST,
    current_module: str | None,
    env: dict[str, Any],
) -> Any:
    if isinstance(node, ast.Expression):
        return _eval_ast(node.body, current_module, env)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float, bool)):
            return node.value
        raise ValueError(f"Unsupported constant {node.value!r}")
    if isinstance(node, ast.UnaryOp):
        op_fn = _UNARY_OPS.get(type(node.op))
        if op_fn is None:
            raise ValueError(f"Unsupported unary operator {type(node.op).__name__}")
        return op_fn(_eval_ast(node.operand, current_module, env))
    if isinstance(node, ast.BinOp):
        op_fn = _BIN_OPS.get(type(node.op))
        if op_fn is None:
            raise ValueError(f"Unsupported operator {type(node.op).__name__}")
        return op_fn(
            _eval_ast(node.left, current_module, env),
            _eval_ast(node.right, current_module, env),
        )
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in _SAFE_FUNCS:
            fname = getattr(node.func, "id", "<expr>")
            raise ValueError(f"Unknown function '{fname}'")
        args = [_eval_ast(a, current_module, env) for a in node.args]
        return _SAFE_FUNCS[node.func.id](*args)
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
        key = f"{node.value.id}.{node.attr}"
        if key in env:
            return env[key]
        raise ValueError(f"Unknown parameter '{key}'")
    if isinstance(node, ast.Name):
        ident = node.id
        if ident in _SAFE_CONSTS:
            return _SAFE_CONSTS[ident]
        if ident == "True":
            return True
        if ident == "False":
            return False
        if current_module and f"{current_module}.{ident}" in env:
            return env[f"{current_module}.{ident}"]
        if f"custom.{ident}" in env:
            return env[f"custom.{ident}"]
        if ident in env:
            return env[ident]
        raise ValueError(f"Unknown parameter '{ident}'")
    raise ValueError(f"Unsupported syntax: {type(node).__name__}")


def _coerce_value(val: Any, ftype: str) -> Any:
    if ftype == "bool":
        if isinstance(val, str):
            return val.strip().lower() in ("true", "1", "yes", "on")
        return bool(val)
    if ftype == "int":
        return int(round(float(val)))
    if ftype == "float":
        return round(float(val), 6)
    return str(val)


def _sync_class_to_source(
    cls: type,
    evaluated_fields: list[dict[str, Any]],
) -> bool:
    """Write modified field default values into the dataclass Python source file."""
    src_file = inspect.getsourcefile(cls)
    if not src_file:
        return False
    path = Path(src_file)
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return False

    lines = content.splitlines(keepends=True)
    try:
        _, start_line = inspect.getsourcelines(cls)
    except (OSError, TypeError):
        start_line = 1

    changed = False
    by_name = {f["name"]: f for f in evaluated_fields}
    field_re = re.compile(
        r"^(\s*)([a-zA-Z_]\w*)(\s*:\s*[^=#]+=\s*)([^#\n]+?)(\s*(?:#.*)?\r?\n?)$"
    )

    # Scan from class start_line until the next top-level def/class
    for idx in range(max(0, start_line - 1), len(lines)):
        line = lines[idx]
        if idx > start_line and re.match(r"^(def |class |@)", line):
            break
        m = field_re.match(line)
        if not m:
            continue
        indent, fname, middle, old_val_str, trailing = m.groups()
        if fname not in by_name:
            continue
        finfo = by_name[fname]
        val = finfo["value"]
        if finfo["type"] == "float":
            # Format cleanly with at least one decimal place
            formatted = f"{float(val):.4f}".rstrip("0")
            if formatted.endswith("."):
                formatted += "0"
        elif finfo["type"] == "int":
            formatted = str(int(val))
        elif finfo["type"] == "bool":
            formatted = "True" if val else "False"
        else:
            formatted = repr(str(val))

        if old_val_str.strip() != formatted:
            lines[idx] = f"{indent}{fname}{middle}{formatted}{trailing}"
            changed = True

    if changed:
        path.write_text("".join(lines), encoding="utf-8")
    return changed


class ParamMatrix:
    """Manages module parameter schemas, custom variables, presets, and evaluation."""

    def __init__(self) -> None:
        self.overrides: dict[str, str] = {}
        self.custom_vars: dict[str, dict[str, str]] = {
            "clearance": {
                "name": "clearance",
                "expr": "0.2",
                "unit": "mm",
                "doc": "Global radial/pocket print clearance",
            }
        }
        self.presets: dict[str, dict[str, Any]] = {}
        self.active_preset: str = ""
        # instance_name -> base_module_short (e.g. {"knee_motor": "flycat_5010"})
        self.instances: dict[str, str] = {}
        # target_id -> custom display/formula alias (e.g. {"motor": "knee_motor"})
        self.aliases: dict[str, str] = {}
        self.last_message: str = ""
        self._load_disk_state()

    def _load_disk_state(self) -> None:
        try:
            if not PARAMS_STATE_FILE.exists():
                return
            data = json.loads(PARAMS_STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(data.get("overrides"), dict):
                self.overrides = {
                    str(k): str(v) for k, v in data["overrides"].items()
                }
            if isinstance(data.get("custom_vars"), dict) and data["custom_vars"]:
                self.custom_vars = data["custom_vars"]
            if isinstance(data.get("presets"), dict):
                self.presets = data["presets"]
            if isinstance(data.get("active_preset"), str):
                self.active_preset = data["active_preset"]
            if isinstance(data.get("instances"), dict):
                self.instances = {
                    str(k): str(v) for k, v in data["instances"].items()
                }
            if isinstance(data.get("aliases"), dict):
                self.aliases = {
                    str(k): str(v) for k, v in data["aliases"].items()
                }
        except (OSError, ValueError):
            pass

    def _save_disk_state(self) -> None:
        try:
            PARAMS_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            tmp = PARAMS_STATE_FILE.with_suffix(".tmp")
            payload = {
                "overrides": self.overrides,
                "custom_vars": self.custom_vars,
                "presets": self.presets,
                "active_preset": self.active_preset,
                "instances": self.instances,
                "aliases": self.aliases,
            }
            tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            tmp.replace(PARAMS_STATE_FILE)
        except OSError:
            pass

    def apply_mutation(
        self,
        payload: dict[str, Any],
        module_classes: dict[str, type] | None = None,
    ) -> None:
        """Apply a UI update payload to overrides, presets, or Python source files."""
        action = payload.get("action", "set")
        self.last_message = ""

        if action == "reset_all":
            self.overrides.clear()
            self.active_preset = ""
            self.last_message = "Reset all parameters to defaults"
            self._save_disk_state()
            return

        if action == "reset_module":
            mod_short = str(payload.get("module", "")).split(".")[-1]
            prefix = f"{mod_short}."
            for k in [k for k in self.overrides if k.startswith(prefix)]:
                del self.overrides[k]
            self._save_disk_state()
            return

        if action == "reset_param":
            key = str(payload.get("key", ""))
            self.overrides.pop(key, None)
            self._save_disk_state()
            return

        if action == "add_custom":
            raw_name = str(payload.get("name", "")).strip()
            name = re.sub(r"[^a-zA-Z0-9_]", "_", raw_name)
            if not name or name[0].isdigit():
                return
            self.custom_vars[name] = {
                "name": name,
                "expr": str(payload.get("expr", "1.0")).strip() or "1.0",
                "unit": str(payload.get("unit", "mm")).strip(),
                "doc": str(payload.get("doc", "Custom variable")).strip(),
            }
            self.last_message = f"Added variable '{name}'"
            self._save_disk_state()
            return

        if action == "delete_custom":
            name = str(payload.get("name", "")).strip()
            self.custom_vars.pop(name, None)
            self.overrides.pop(f"custom.{name}", None)
            self._save_disk_state()
            return

        if action == "add_instance":
            raw_name = str(payload.get("name", "")).strip()
            name = re.sub(r"[^a-zA-Z0-9_]", "_", raw_name)
            base_type = str(payload.get("base_type", "")).strip()
            if not name or name[0].isdigit() or not base_type:
                return
            self.instances[name] = base_type
            self.last_message = f"Added instance '{name}' ({base_type})"
            self._save_disk_state()
            return

        if action == "delete_instance":
            name = str(payload.get("name", "")).strip()
            self.instances.pop(name, None)
            self.aliases.pop(name, None)
            prefix = f"{name}."
            for k in [k for k in self.overrides if k.startswith(prefix)]:
                del self.overrides[k]
            self.last_message = f"Deleted instance '{name}'"
            self._save_disk_state()
            return

        if action == "rename_instance":
            target = str(payload.get("target", "")).strip()
            raw_new = str(payload.get("new_name", "")).strip()
            new_name = re.sub(r"[^a-zA-Z0-9_]", "_", raw_new)
            if not target or not new_name or new_name[0].isdigit():
                return
            old_alias = self.aliases.get(target, target)
            if target in self.instances and target != new_name:
                base_type = self.instances.pop(target)
                self.instances[new_name] = base_type
                old_prefix = f"{target}."
                for k in list(self.overrides.keys()):
                    if k.startswith(old_prefix):
                        field_part = k[len(old_prefix) :]
                        self.overrides[f"{new_name}.{field_part}"] = (
                            self.overrides.pop(k)
                        )
            else:
                self.aliases[target] = new_name

            # Cascade rename across all formula bindings in overrides
            for old_tok in {target, old_alias}:
                pat = re.compile(rf"\b{re.escape(old_tok)}\.")
                for k, v in list(self.overrides.items()):
                    self.overrides[k] = pat.sub(f"{new_name}.", v)

            self.last_message = f"Renamed '{old_alias}' → '{new_name}' (bindings updated)"
            self._save_disk_state()
            return

        if action == "save_preset":
            name = str(payload.get("name", "")).strip()
            if not name:
                return
            self.presets[name] = {
                "overrides": dict(self.overrides),
                "custom_vars": json.loads(json.dumps(self.custom_vars)),
            }
            self.active_preset = name
            self.last_message = f"Saved preset '{name}'"
            self._save_disk_state()
            return

        if action == "load_preset":
            name = str(payload.get("name", "")).strip()
            preset = self.presets.get(name)
            if not preset:
                return
            self.overrides = dict(preset.get("overrides", {}))
            if preset.get("custom_vars"):
                self.custom_vars = json.loads(
                    json.dumps(preset["custom_vars"])
                )
            self.active_preset = name
            self.last_message = f"Loaded preset '{name}'"
            self._save_disk_state()
            return

        if action == "delete_preset":
            name = str(payload.get("name", "")).strip()
            self.presets.pop(name, None)
            if self.active_preset == name:
                self.active_preset = ""
            self.last_message = f"Deleted preset '{name}'"
            self._save_disk_state()
            return

        if action == "sync_python" and module_classes:
            _, state_now = self.evaluate(module_classes)
            synced: list[str] = []
            for short, mod_info in state_now["modules"].items():
                full_name = mod_info["module"]
                cls = module_classes.get(full_name)
                if cls and _sync_class_to_source(cls, mod_info["fields"]):
                    synced.append(f"{short}.py")
            if synced:
                self.last_message = f"Synced values to {', '.join(synced)}"
            else:
                self.last_message = "Python files already up to date"
            self._save_disk_state()
            return

        if action == "set":
            updates = payload.get("updates", {})
            if isinstance(updates, dict):
                for key, expr in updates.items():
                    key_str = str(key)
                    expr_str = str(expr).strip()
                    if key_str.startswith("custom."):
                        cname = key_str.split(".", 1)[1]
                        if cname in self.custom_vars:
                            self.custom_vars[cname]["expr"] = expr_str
                    else:
                        self.overrides[key_str] = expr_str
            self._save_disk_state()

    def evaluate(
        self, module_classes: dict[str, type]
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Evaluate all custom variables and module schemas.

        Returns ``(configs_by_module_name, serialized_matrix_state)``.
        """
        short_to_full: dict[str, str] = {}
        schemas_by_short: dict[str, list[dict[str, Any]]] = {}
        classes_by_short: dict[str, type] = {}
        class_to_short: dict[str, str] = {}

        for full_name, cls in module_classes.items():
            short = full_name.rsplit(".", 1)[-1]
            short_to_full[short] = full_name
            classes_by_short[short] = cls
            class_to_short[cls.__name__] = short
            schemas_by_short[short] = extract_schema(cls)

        # Register named instances (e.g. knee_motor -> flycat_5010)
        for inst_name, base_short in list(self.instances.items()):
            if base_short in classes_by_short and inst_name not in schemas_by_short:
                cls = classes_by_short[base_short]
                short_to_full[inst_name] = f"instance.{inst_name}"
                classes_by_short[inst_name] = cls
                schemas_by_short[inst_name] = extract_schema(cls)

        # Register user aliases so formulas can reference renamed instances/modules
        for target_id, alias_name in self.aliases.items():
            if target_id in schemas_by_short and alias_name not in schemas_by_short:
                class_to_short[alias_name] = target_id

        cells: dict[str, dict[str, Any]] = {}

        for cname, cinfo in self.custom_vars.items():
            key = f"custom.{cname}"
            expr = self.overrides.get(key, cinfo["expr"])
            cells[key] = {
                "key": key,
                "module": "custom",
                "name": cname,
                "type": "float",
                "default": 0.0,
                "default_expr": cinfo["expr"],
                "expr": expr,
                "unit": cinfo.get("unit", "mm"),
                "group": "Custom Variables",
                "doc": cinfo.get("doc", ""),
                "min": -100.0,
                "max": 200.0,
                "step": 0.1,
            }

        for short, field_list in schemas_by_short.items():
            for fdesc in field_list:
                key = f"{short}.{fdesc['name']}"
                default_expr = str(fdesc["default_expr"])
                # Apply active instance aliases to default binding expressions so
                # default formulas also follow renamed instances automatically.
                for orig_mod, alias_mod in self.aliases.items():
                    if orig_mod != alias_mod and f"{orig_mod}." in default_expr:
                        default_expr = re.sub(
                            rf"\b{re.escape(orig_mod)}\.",
                            f"{alias_mod}.",
                            default_expr,
                        )
                expr = self.overrides.get(key, default_expr)
                for orig_mod, alias_mod in self.aliases.items():
                    if orig_mod != alias_mod and f"{orig_mod}." in expr:
                        expr = re.sub(
                            rf"\b{re.escape(orig_mod)}\.",
                            f"{alias_mod}.",
                            expr,
                        )
                if key in self.overrides and expr == default_expr:
                    del self.overrides[key]
                cells[key] = {
                    **fdesc,
                    "default_expr": default_expr,
                    "key": key,
                    "module": short,
                    "expr": expr,
                }

        ast_nodes: dict[str, ast.AST] = {}
        deps: dict[str, set[str]] = {}
        errors: dict[str, str] = {}

        for key, cell in cells.items():
            raw_expr = str(cell["expr"]).strip()
            ftype = cell["type"]
            if not is_formula_expr(raw_expr, ftype):
                try:
                    _coerce_value(raw_expr, ftype)
                    deps[key] = set()
                except Exception as exc:
                    errors[key] = f"Invalid value: {exc}"
                    deps[key] = set()
                continue

            formula_body = raw_expr.lstrip("=").strip()
            if not formula_body:
                errors[key] = "Empty formula"
                deps[key] = set()
                continue

            try:
                tree = ast.parse(formula_body, mode="eval")
                ast_nodes[key] = tree
                mod = None if cell["module"] == "custom" else cell["module"]
                raw_refs = _extract_refs(tree, mod)
                resolved_refs: set[str] = set()
                for ref in raw_refs:
                    if "." in ref:
                        prefix, attr = ref.split(".", 1)
                        if prefix in class_to_short:
                            ref = f"{class_to_short[prefix]}.{attr}"
                    if ref in cells:
                        resolved_refs.add(ref)
                    else:
                        ident = ref.split(".", 1)[-1]
                        if f"custom.{ident}" in cells:
                            resolved_refs.add(f"custom.{ident}")
                        else:
                            resolved_refs.add(ref)
                deps[key] = resolved_refs
            except SyntaxError as exc:
                errors[key] = f"Syntax error: {exc.msg}"
                deps[key] = set()

        env: dict[str, Any] = {}
        state_visit: dict[str, int] = {}

        def resolve_cell(key: str, stack: list[str]) -> Any:
            if key in env:
                return env[key]
            cell = cells.get(key)
            if cell is None:
                raise ValueError(f"Unknown parameter '{key}'")

            vstate = state_visit.get(key, 0)
            if vstate == 1:
                cycle = " -> ".join(stack + [key])
                raise ValueError(f"Circular reference: {cycle}")
            if key in errors:
                val = cell["default"]
                env[key] = val
                state_visit[key] = 2
                return val

            state_visit[key] = 1
            ftype = cell["type"]
            raw_expr = str(cell["expr"]).strip()

            try:
                if key not in ast_nodes:
                    val = _coerce_value(raw_expr, ftype)
                else:
                    for dep_key in deps.get(key, set()):
                        if dep_key == key:
                            raise ValueError(f"Self-reference in '{key}'")
                        resolve_cell(dep_key, stack + [key])
                        if dep_key in errors:
                            raise ValueError(f"Depends on errored '{dep_key}'")
                    mod = None if cell["module"] == "custom" else cell["module"]
                    raw_val = _eval_ast(ast_nodes[key], mod, env)
                    val = _coerce_value(raw_val, ftype)
            except Exception as exc:
                errors[key] = str(exc)
                val = cell["default"]

            state_visit[key] = 2
            env[key] = val
            if "." in key:
                short_mod, attr = key.split(".", 1)
                if short_mod in classes_by_short:
                    env[f"{classes_by_short[short_mod].__name__}.{attr}"] = val
                if short_mod in self.aliases:
                    env[f"{self.aliases[short_mod]}.{attr}"] = val
            return val

        for key in cells:
            if state_visit.get(key, 0) == 0:
                resolve_cell(key, [])

        configs: dict[str, Any] = {}
        serialized_modules: dict[str, dict[str, Any]] = {}

        for short, full_name in short_to_full.items():
            cls = classes_by_short[short]
            kwargs: dict[str, Any] = {}
            out_fields: list[dict[str, Any]] = []
            for fdesc in schemas_by_short[short]:
                fname = fdesc["name"]
                key = f"{short}.{fname}"
                cell = cells[key]
                val = env.get(key, cell["default"])
                kwargs[fname] = val
                expr_str = str(cell["expr"]).strip()
                bound = is_formula_expr(expr_str, cell["type"])
                modified = expr_str != str(cell["default_expr"]).strip()

                lo, hi = cell["min"], cell["max"]
                if isinstance(val, (int, float)) and not isinstance(val, bool):
                    if val < lo:
                        lo = round(float(val) - abs(float(val)) * 0.5, 2)
                    if val > hi:
                        hi = round(float(val) * 1.5, 2)

                out_fields.append(
                    {
                        "key": key,
                        "name": fname,
                        "type": cell["type"],
                        "group": cell["group"],
                        "doc": cell["doc"],
                        "unit": cell["unit"],
                        "default": cell["default"],
                        "default_expr": cell["default_expr"],
                        "expr": expr_str,
                        "value": val,
                        "min": lo,
                        "max": hi,
                        "step": cell["step"],
                        "is_bound": bound,
                        "is_constant": bool(cell.get("constant", False)),
                        "is_modified": modified,
                        "deps": sorted(deps.get(key, set())),
                        "error": errors.get(key),
                    }
                )

            configs[full_name] = cls(**kwargs)
            is_inst = short in self.instances
            base_short = self.instances.get(short, short)
            serialized_modules[short] = {
                "module": full_name,
                "short": short,
                "alias": self.aliases.get(short, short),
                "class_name": cls.__name__,
                "is_instance": is_inst,
                "base_type": base_short,
                "fields": out_fields,
            }

        custom_out: list[dict[str, Any]] = []
        for cname in self.custom_vars:
            key = f"custom.{cname}"
            cell = cells[key]
            val = env.get(key, 0.0)
            expr_str = str(cell["expr"]).strip()
            custom_out.append(
                {
                    "key": key,
                    "name": cname,
                    "type": "float",
                    "group": "Custom Variables",
                    "doc": cell["doc"],
                    "unit": cell["unit"],
                    "default": cell["default_expr"],
                    "default_expr": cell["default_expr"],
                    "expr": expr_str,
                    "value": val,
                    "min": min(cell["min"], float(val) - 10.0),
                    "max": max(cell["max"], float(val) * 2.0 + 10.0),
                    "step": 0.05 if abs(float(val)) < 5.0 else 0.5,
                    "is_bound": is_formula_expr(expr_str, "float"),
                    "is_modified": False,
                    "deps": sorted(deps.get(key, set())),
                    "error": errors.get(key),
                }
            )

        # Compute per-part parameter scopes (part_name -> list of parameter keys)
        part_scopes: dict[str, list[str]] = {}
        all_mod_keys: dict[str, list[str]] = {
            short: [f["key"] for f in mod_info["fields"]]
            for short, mod_info in serialized_modules.items()
        }

        for short, cls in classes_by_short.items():
            pgroups: dict[str, list[str]] = getattr(cls, "PART_GROUPS", {}) or {}
            pfields: dict[str, list[str]] = getattr(cls, "PART_FIELDS", {}) or {}
            mod_fields = serialized_modules[short]["fields"]

            for part_name, group_list in pgroups.items():
                gset = {g.lower() for g in group_list}
                matched = [
                    f["key"]
                    for f in mod_fields
                    if f["group"].lower() in gset
                ]
                if matched:
                    part_scopes[part_name] = matched

            for part_name, field_specs in pfields.items():
                matched: list[str] = list(part_scopes.get(part_name, []))
                for spec in field_specs:
                    if spec.endswith(".*"):
                        target_mod = spec[:-2]
                        matched.extend(all_mod_keys.get(target_mod, []))
                    elif "." in spec:
                        if spec in cells:
                            matched.append(spec)
                    else:
                        full_k = f"{short}.{spec}"
                        if full_k in cells:
                            matched.append(full_k)
                if matched:
                    part_scopes[part_name] = list(dict.fromkeys(matched))

        # Expand part_scopes with direct bound dependents and dependencies
        for part_name, keys in list(part_scopes.items()):
            expanded = list(keys)
            key_set = set(keys)
            # Include any field that directly depends on a field in key_set,
            # or any field that a field in key_set directly depends on
            for k, dep_set in deps.items():
                if k in key_set:
                    for d in dep_set:
                        if d in cells and not d.startswith("custom.") and d not in key_set:
                            expanded.append(d)
                elif dep_set & key_set:
                    if k not in key_set:
                        expanded.append(k)
            part_scopes[part_name] = list(dict.fromkeys(expanded))

        return configs, {
            "modules": serialized_modules,
            "custom": custom_out,
            "part_scopes": part_scopes,
            "instances": self.instances,
            "aliases": self.aliases,
            "presets": sorted(self.presets.keys()),
            "active_preset": self.active_preset,
            "message": self.last_message,
        }
