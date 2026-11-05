# CAD

Parametric CAD for the robot, in Python over OpenCascade with
[build123d](https://build123d.readthedocs.io/).

The goal: change one number in `skeleton.py`, and every part regenerates.

## Setup

```sh
python3 -m venv cad/.venv
cad/.venv/bin/pip install -r cad/requirements.txt
```

## Run

```sh
cad/.venv/bin/python cad/fixtures/drone_stand.py
cad/.venv/bin/python cad/fixtures/dm5010_mount.py
```

Parts are written to `cad/build/` as STEP and STL.

## Live viewer

A local 3D viewer that rebuilds on save and shows the status of every part:

```sh
cad/.venv/bin/python cad/viewer/server.py --open
```

Then open <http://127.0.0.1:8765/>. Save any file under `cad/` or
`cad/fixtures/` and the page rebuilds and reloads the mesh.

- Sidebar: **Assemblies** first, then **Parts**; green for ok, red for a
  build error.
- Click an assembly to see its components together, each in its own colour.
  The drone stand has two: `drone_stand_microspora` (stator side) and
  `drone_stand_as5048a` (rotor side).
- Click a part to show it alone; click an error to read the traceback.
- HUD: volume, bounding box, triangle count, build time.
- `Rebuild` forces a build; `wireframe` toggles the material.

A fixture can expose `parts() -> dict[str, Part]` and
`assemblies() -> dict[str, list[tuple[str, Part, str]]]`, where each tuple is
`(component name, positioned part, colour)`. Assembly components are exported
with an `<assembly>__` prefix, so they can share a frame without clashing with
the flat parts.

The build runs in a long-lived worker that imports build123d once, so a
rebuild is about a second. The page loads three.js from a CDN, so the first
load needs network access. Changes to `cad/viewer/` itself need a server
restart.

## Renders

```sh
cd cad && .venv/bin/python -m viewer.render
```

Writes hidden-line PNGs of every part and ghosted wireframes of every
assembly to `cad/build/viewer/renders/`. Colour code: printed parts
blue-grey, motor orange, magnet holders green, magnets purple, sensor
boards red.

## Layout

```text
cad/
  skeleton.py          leg parameters (link lengths, ROM, belt ratios)
  lego.py              LEGO Technic hole/axle/pin helpers
  export.py            STEP + STL export
  fixtures/
    drone_stand.py     Phase 1: drone motor test stand
    dm5010_mount.py    Phase 1: DM5010 + MicroSpora mount
  viewer/
    server.py          HTTP server, file watcher, SSE
    buildlib.py        shared build logic
    worker.py          long-lived build process
    build.py           one-shot CLI build
    static/            three.js page
```

## Dimensions

| Feature | Dimension |
|---|---|
| LEGO hole diameter | 4.8 mm |
| LEGO axle cross | 4.8 mm |
| LEGO hole pitch | 8.0 mm |
| LEGO plate thickness | 3.2 mm |
| LEGO beam thickness | 9.6 mm |
| Printed axle hole | 4.9–5.0 mm press, 5.1 mm slip |
| Printed pin hole | 4.8–4.9 mm |
| Sliding clearance | 0.2 mm |
| Press-fit clearance | 0.1 mm |
| Minimum wall | 1.2 mm |
| Knee bearing | 6805, 25 × 37 × 7 mm |

## Print settings

- PETG or PLA+, 4 perimeters, 40–60 % infill for links, 80–100 % for bearing
  housings.
- Print bearing bores vertical so the layers are perpendicular to the load.
- 0.12 mm layers for pulley teeth.
- Heat-set brass inserts: M3 for motor mounts, M2.5 for the DM5010, M2 for the
  MicroSpora.

## Before printing

Work through `PRINT_CHECKLIST.md` first: measurements, CAD checks, slicer
settings, printer prep, and a post-print fit check. Do not slice until every
measurement is confirmed.

## Conventions

- Read `skeleton.py` first; never hard-code a link length in a part file.
- Every fixture takes a `dataclass` config so dimensions are in one place.
- Export both STEP (for inspection) and STL (for printing).
