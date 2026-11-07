"""Orthographic front/top/left views with bounding-box dimensions.

    cd cad && .venv/bin/python -m viewer.views

Writes one PNG per part to ``cad/build/viewer/views/`` and a Markdown index
with a section per part.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import trimesh  # noqa: E402
from matplotlib.collections import LineCollection  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "build" / "viewer"
VIEWS = OUT / "views"

COLORS = {
    "drone_stand": "#8fa8c8",
    "flycat_5010": "#e0a060",
    "drone_magnet_carrier": "#7fc8a0",
    "drone_magnet_holder": "#7fc8a0",
    "drone_magnet": "#c080d0",
    "drone_sensor_as5048a": "#d07070",
    "drone_sensor_microspora": "#d07070",
    "dm5010": "#e0a060",
    "dm5010_mount": "#8fa8c8",
    "dm5010_magnet_carrier": "#7fc8a0",
}

# (horizontal axis, vertical axis, title)
VIEWS_DEF = [
    (0, 2, "front  (X × Z)"),
    (0, 1, "top  (X × Y)"),
    (1, 2, "left  (Y × Z)"),
]


def load(path: Path) -> tuple[np.ndarray, np.ndarray]:
    mesh = trimesh.load(path, force="mesh")
    return mesh.vertices, mesh.edges_unique


def draw(ax, vertices, edges, color, axes, title):
    i, j = axes
    segments = vertices[edges][:, :, [i, j]]
    ax.add_collection(
        LineCollection(segments, colors=color, linewidths=0.18, alpha=0.85)
    )

    mins, maxs = vertices.min(axis=0), vertices.max(axis=0)
    x0, x1 = mins[i], maxs[i]
    y0, y1 = mins[j], maxs[j]
    pad = max(x1 - x0, y1 - y0) * 0.18

    ax.add_patch(
        Rectangle(
            (x0, y0),
            x1 - x0,
            y1 - y0,
            fill=False,
            edgecolor="#ffffff",
            linewidth=0.7,
            linestyle="--",
            alpha=0.7,
        )
    )

    ax.text(
        (x0 + x1) / 2,
        y0 - pad * 0.35,
        f"{x1 - x0:.1f} mm",
        ha="center",
        va="top",
        color="#d7dee8",
        fontsize=9,
    )
    ax.text(
        x0 - pad * 0.35,
        (y0 + y1) / 2,
        f"{y1 - y0:.1f} mm",
        ha="right",
        va="center",
        rotation=90,
        color="#d7dee8",
        fontsize=9,
    )

    ax.set_xlim(x0 - pad, x1 + pad)
    ax.set_ylim(y0 - pad, y1 + pad)
    ax.set_aspect("equal")
    ax.set_title(title, color="#7d8899", fontsize=9)
    ax.axis("off")


def render_part(name: str, path: Path, color: str) -> dict:
    vertices, edges = load(path)
    mins, maxs = vertices.min(axis=0), vertices.max(axis=0)
    size = maxs - mins

    fig, axes = plt.subplots(1, 3, figsize=(15, 5), facecolor="#0e1116")
    for ax, (i, j, title) in zip(axes, VIEWS_DEF):
        draw(ax, vertices, edges, color, (i, j), title)

    fig.suptitle(name, color="#d7dee8", fontsize=13)
    fig.tight_layout()
    VIEWS.mkdir(parents=True, exist_ok=True)
    out = VIEWS / f"{name}.png"
    fig.savefig(out, dpi=130, facecolor="#0e1116", bbox_inches="tight")
    plt.close(fig)
    print(out)

    return {
        "name": name,
        "x": round(float(size[0]), 2),
        "y": round(float(size[1]), 2),
        "z": round(float(size[2]), 2),
    }


def main() -> None:
    state = json.loads((OUT / "state.json").read_text())
    rows = []
    for part in state["parts"]:
        if part["status"] != "ok":
            continue
        color = COLORS.get(part["name"], "#9fb4d0")
        rows.append(render_part(part["name"], OUT / Path(part["mesh"]).name, color))

    lines = ["# Part views", "", "Front, top, and left orthographic views with the bounding box.", ""]
    for row in rows:
        lines += [
            f"## {row['name']}",
            "",
            f"`{row['x']} × {row['y']} × {row['z']} mm` (X × Y × Z)",
            "",
            f"![{row['name']}](./{row['name']}.png)",
            "",
        ]
    (VIEWS / "README.md").write_text("\n".join(lines))
    print(VIEWS / "README.md")


if __name__ == "__main__":
    main()
