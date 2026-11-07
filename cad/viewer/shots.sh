#!/usr/bin/env bash
# Capture the live viewer for every part and assembly.
#
#   cad/viewer/shots.sh
#   PORT=8765 OUT=cad/build/viewer/shots cad/viewer/shots.sh
#
# Starts the viewer if it is not already running, then uses headless Chrome
# with SwiftShader so WebGL works without a display.
set -euo pipefail

PORT="${PORT:-8765}"
OUT="${OUT:-cad/build/viewer/shots}"
CHROME="${CHROME:-google-chrome}"
URL="http://127.0.0.1:$PORT"

mkdir -p "$OUT"

if ! curl -sf "$URL/api/state" >/dev/null; then
  cad/.venv/bin/python cad/viewer/server.py --port "$PORT" \
    >/tmp/cad-viewer.log 2>&1 &
  sleep 6
fi

names=$(curl -s "$URL/api/state" | python3 -c '
import json, sys
d = json.load(sys.stdin)
for p in d["parts"]:
    if p["status"] == "ok":
        print(p["name"])
for a in d["assemblies"]:
    if a["status"] == "ok":
        print(a["name"])
')

for name in $names; do
  "$CHROME" --headless --no-sandbox --disable-dev-shm-usage \
    --use-gl=swiftshader --enable-unsafe-swiftshader --hide-scrollbars \
    --window-size=1400,1000 --virtual-time-budget=12000 \
    --screenshot="$OUT/$name.png" \
    "$URL/?static=1&select=$name&wireframe=1" \
    >/dev/null 2>&1
  echo "$OUT/$name.png"
done
