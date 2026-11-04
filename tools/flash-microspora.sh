#!/usr/bin/env bash
# Flash the MicroSpora without touching the BOOT button: ask the running
# firmware to jump to the bootloader, wait for it, then upload.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo="$(dirname "$here")"
port="${PORT:-/dev/ttyACM0}"
project="$repo/firmware/microspora-bringup"
pio="${PIO:-$HOME/.platformio/penv/bin/pio}"

if lsusb -d 0483:df11 >/dev/null 2>&1; then
  echo "already in DFU"
else
  if [[ ! -e "$port" ]]; then
    echo "no $port; is the board connected and running firmware?" >&2
    exit 1
  fi
  "$here/SimpleFOCScope/.venv/bin/python" - "$port" <<'PY'
import sys, time, serial
port = sys.argv[1]
with serial.Serial(port, 250000, timeout=0.2) as s:
    time.sleep(0.2)
    s.write(b"dfu\n")
    s.flush()
    time.sleep(0.5)
PY
  for _ in $(seq 1 40); do
    lsusb -d 0483:df11 >/dev/null 2>&1 && break
    sleep 0.25
  done
  if ! lsusb -d 0483:df11 >/dev/null 2>&1; then
    echo "board did not enter DFU; press BOOT and RESET" >&2
    exit 1
  fi
  echo "in DFU"
fi

# dfu-util reports a spurious get_status error after a good download.
"$pio" run -d "$project" -t upload 2>&1 | grep -vE "get_status|^$" | tail -4 || true
sleep 2
if lsusb -d 0483:5740 >/dev/null 2>&1; then
  echo "board is running the new firmware"
else
  lsusb -d 0483: && echo "warning: board did not come back as a serial device"
fi
