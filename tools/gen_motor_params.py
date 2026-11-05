"""Generate firmware/common/include/motor_params.h from hardware/motor_params.json.

Run automatically by PlatformIO before a build (see extra_scripts in each
platformio.ini). The header is generated, never edited, and never committed.

The JSON is the single source of truth shared by the firmware, the PC-side
identification tools, and the MuJoCo twin.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SOURCE_NAME = Path("hardware") / "motor_params.json"


def c_float(value) -> str:
    """Format a float as a valid C literal."""
    text = f"{float(value):.6g}"
    if "." not in text and "e" not in text and "E" not in text:
        text += ".0"
    return text + "f"

TARGET_NAME = Path("firmware") / "common" / "include" / "motor_params.h"

SCALARS = (
    ("pole_pairs", "MOTOR_POLE_PAIRS", "int"),
    ("r_phase_ohm", "MOTOR_R_PHASE_OHM", "float"),
    ("r_total_ohm", "MOTOR_R_TOTAL_OHM", "float"),
    ("l_d_h", "MOTOR_L_D_H", "float"),
    ("l_q_h", "MOTOR_L_Q_H", "float"),
    ("psi_wb", "MOTOR_PSI_WB", "float"),
    ("kt_nm_per_a", "MOTOR_KT_NM_PER_A", "float"),
    ("j_rotor_kgm2", "MOTOR_J_ROTOR_KGM2", "float"),
    ("b_nms", "MOTOR_B_NMS", "float"),
    ("tc_nm", "MOTOR_TC_NM", "float"),
    ("v_dead_v", "MOTOR_V_DEAD_V", "float"),
    ("current_sense_mv_per_a", "MOTOR_CURRENT_SENSE_MV_PER_A", "float"),
    ("vbus_scale", "MOTOR_VBUS_SCALE", "float"),
)


def repo_root() -> Path:
    """Find the repository root, whether run directly or by SCons.

    PlatformIO executes extra scripts without defining __file__, so fall back
    to the project directory that SCons exposes.
    """
    try:
        return Path(__file__).resolve().parents[1]
    except NameError:
        pass
    try:
        project = Path(env.subst("$PROJECT_DIR"))  # noqa: F821  (SCons global)
        return project.resolve().parents[1]
    except Exception:
        return Path.cwd().resolve().parent


def fail(message: str) -> None:
    sys.stderr.write(f"gen_motor_params: {message}\n")


def build_header(params: dict) -> str:
    pole_pairs = float(params["pole_pairs"])
    psi = float(params["psi_wb"])
    kt = float(params["kt_nm_per_a"])
    if psi > 0.0 and kt > 0.0:
        expected = 1.5 * pole_pairs * psi
        error = abs(kt - expected) / expected
        if error > 0.05:
            fail(
                f"kt_nm_per_a ({kt}) disagrees with 1.5 * pole_pairs * psi "
                f"({expected:.6f}) by {error * 100:.1f}%; fix the JSON"
            )
            raise SystemExit(1)

    offsets = params.get("current_offset_a", [0.0, 0.0, 0.0])
    if len(offsets) != 3:
        fail("current_offset_a must have three entries")
        raise SystemExit(1)

    lines = [
        "// Generated from hardware/motor_params.json by tools/gen_motor_params.py.",
        "// Do not edit: change the JSON and rebuild.",
        "#pragma once",
        "",
        f'#define MOTOR_NAME "{params.get("motor", "unknown motor")}"',
        f'#define MOTOR_PARAMS_STATUS "{params.get("status", "unknown")}"',
        "",
    ]
    for key, name, kind in SCALARS:
        value = params[key]
        if kind == "int":
            lines.append(f"#define {name} {int(value)}")
        else:
            lines.append(f"#define {name} {c_float(value)}")
    lines += [
        "",
        "static const float MOTOR_CURRENT_OFFSET_A[3] = {"
        + ", ".join(c_float(value) for value in offsets)
        + "};",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    root = repo_root()
    source = root / SOURCE_NAME
    target = root / TARGET_NAME

    if not source.is_file():
        fail(f"missing {source}")
        return 1

    try:
        params = json.loads(source.read_text())
    except json.JSONDecodeError as error:
        fail(f"{source} is not valid JSON: {error}")
        return 1

    missing = [key for key, _, _ in SCALARS if key not in params]
    if missing:
        fail(f"missing keys in {source}: {', '.join(missing)}")
        return 1

    assumed = sorted(
        key for key, value in params.get("provenance", {}).items() if value == "assumed"
    )
    if assumed:
        print(
            f"gen_motor_params: warning: {len(assumed)} assumed parameter(s): "
            f"{', '.join(assumed)}",
            file=sys.stderr,
        )

    text = build_header(params)
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.is_file() or target.read_text() != text:
        target.write_text(text)
        print(f"gen_motor_params: wrote {target.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
