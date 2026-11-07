"""Render the viewer parts and assemblies to PNG wireframes.

    cd cad && .venv/bin/python -m viewer.render

Writes to ``cad/build/viewer/renders/``. Uses the same colour code as the
live viewer: printed parts blue-grey, motor orange, magnet holders green,
magnets purple, sensor boards red.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import trimesh  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "build" / "viewer"
RENDERS = OUT / "renders"

COLORS = {
    "drone_stand": "#8fa8c8",
    "flycat_5010": "#e0a060",
    "drone_magnet_carrier": "#7fc8a0",
    "drone_magnet_holder": "#7fc8a0",
    "drone_magnet": "#c080d0",
    "drone_sensor_as5048a": "#d07070",
    "drone_sensor_microspora": "#d07070",
    "dm5010_mount": "#8fa8c8",
    "dm5010_magnet_carrier": "#7fc8a0",
}


def load_triangles(path: Path) -> np.ndarray:
    mesh = trimesh.load(path, force="mesh")
    return mesh.vertices[mesh.faces]


def render(
    items: list[tuple[Path, str, float, bool]],
    name: str,
    azim: float = -60,
) -> None:
    fig = plt.figure(figsize=(9, 9), facecolor="#0e1116")
    ax = fig.add_subplot(111, projection="3d", facecolor="#0e1116")
    ax.set_axis_off()

    points = []
    for path, color, width, solid in items:
        triangles = load_triangles(path)
        points.append(triangles.reshape(-1, 3))
        ax.add_collection3d(
            Poly3DCollection(
                triangles,
                facecolors=color if solid else "none",
                edgecolors=color,
                linewidths=width,
                alpha=0.9 if solid else 0.35,
            )
        )

    cloud = np.vstack(points)
    mins, maxs = cloud.min(axis=0), cloud.max(axis=0)
    center = (mins + maxs) / 2
    radius = (maxs - mins).max() / 2 * 1.1

    ax.set_xlim(center[0] - radius, center[0] + radius)
    ax.set_ylim(center[1] - radius, center[1] + radius)
    ax.set_zlim(center[2] - radius, center[2] + radius)
    ax.set_box_aspect((1, 1, 1))
    ax.view_init(elev=22, azim=azim)

    RENDERS.mkdir(parents=True, exist_ok=True)
    path = RENDERS / f"{name}.png"
    fig.savefig(path, dpi=140, facecolor="#0e1116", bbox_inches="tight")
    plt.close(fig)
    print(path)


def main() -> None:
    state = json.loads((OUT / "state.json").read_text())

    for part in state["parts"]:
        if part["status"] != "ok":
            continue
        color = COLORS.get(part["name"], "#9fb4d0")
        render([(OUT / Path(part["mesh"]).name, color, 0.18, False)], part["name"])

    for assembly in state["assemblies"]:
        if assembly["status"] != "ok":
            continue
        items = []
        for c in assembly["components"]:
            if c["status"] != "ok":
                continue
            color = c.get("color", "#9fb4d0")
            # Stand and motor are ghost wireframe; the small parts are solid.
            solid = c["name"] not in ("stand", "motor")
            width = 0.35 if solid else 0.10
            items.append((OUT / Path(c["mesh"]).name, color, width, solid))
        # The MicroSpora sits behind the stand, so look from the back.
        azim = 120 if "microspora" in assembly["name"] else -60
        render(items, assembly["name"], azim=azim)


if __name__ == "__main__":
    main()
