---
name: CAD screenshots
description: Use when capturing images of the robot's CAD parts or assemblies — 3D renders, orthographic front/top/left views with dimensions, or headless screenshots of the live viewer.
---

# CAD screenshots

Three ways to get an image out of the CAD tree, from cheapest to most
representative.

## 1. Orthographic views with dimensions

```sh
cd cad && .venv/bin/python -m viewer.views
```

Writes one PNG per part to `cad/build/viewer/views/`, each with **front**,
**top**, and **left** projections, a dashed bounding box, and the X/Y/Z
dimensions. Also writes `views/README.md` with a section per part.

Use this for a drawing-style review: hole positions, plate thickness, and
overall envelope.

## 2. 3D renders

```sh
cd cad && .venv/bin/python -m viewer.render
```

Writes `cad/build/viewer/renders/`:

- parts: hidden-line (opaque faces, coloured edges)
- assemblies: ghosted wireframe, small parts solid

Colour code, shared with the live viewer:

| Colour | Part |
|---|---|
| `#8fa8c8` blue-grey | printed stand |
| `#e0a060` orange | motor |
| `#7fc8a0` green | magnet carrier / holder |
| `#c080d0` purple | magnet |
| `#d07070` red | sensor board |

## 3. Live viewer screenshots

```sh
cad/viewer/shots.sh
```

Starts the viewer if needed, then uses headless Chrome with SwiftShader to
capture every part and assembly in wireframe to
`cad/build/viewer/shots/`.

The viewer accepts URL parameters for deterministic captures:

| Parameter | Effect |
|---|---|
| `?static=1` | load `/api/state` once, no SSE (lets the page go idle) |
| `?select=<name>` | pin a part or assembly |
| `?wireframe=1` | start in wireframe |

Example:

```sh
google-chrome --headless --no-sandbox --disable-dev-shm-usage \
  --use-gl=swiftshader --enable-unsafe-swiftshader --hide-scrollbars \
  --window-size=1400,1000 --virtual-time-budget=12000 \
  --screenshot=out.png \
  "http://127.0.0.1:8765/?static=1&select=drone_stand_microspora&wireframe=1"
```

## Gotchas

- `--virtual-time-budget` must be long enough for the three.js CDN import and
  the STL loads; 12 s is safe.
- Without `?static=1` the SSE connection keeps the page busy and headless
  Chrome may never take the screenshot.
- `--use-gl=swiftshader --enable-unsafe-swiftshader` is what makes WebGL work
  without a display.
- The viewer must be running. `shots.sh` starts it on port 8765 if needed.
- Output lives under `cad/build/`, which is gitignored. Copy to `docs/` if an
  image should be committed.
