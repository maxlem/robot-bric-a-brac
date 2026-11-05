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

## Layout

```text
cad/
  skeleton.py          leg parameters (link lengths, ROM, belt ratios)
  lego.py              LEGO Technic hole/axle/pin helpers
  export.py            STEP + STL export
  fixtures/
    drone_stand.py     Phase 1: drone motor test stand
    dm5010_mount.py    Phase 1: DM5010 + MicroSpora mount
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

## Conventions

- Read `skeleton.py` first; never hard-code a link length in a part file.
- Every fixture takes a `dataclass` config so dimensions are in one place.
- Export both STEP (for inspection) and STL (for printing).
