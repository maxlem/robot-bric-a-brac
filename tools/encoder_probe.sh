#!/usr/bin/env bash
# Run the encoder probe with the interpreter that has pyserial installed.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$here/SimpleFOCScope/.venv/bin/python" -u "$here/encoder_probe.py" "$@"
