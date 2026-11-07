"""Long-lived build worker.

Imports build123d once, then rebuilds on request. The server talks to it over
newline-delimited JSON on stdin/stdout:

    {"cmd": "build"}                       ->  full rebuild (drops cached modules)
    {"cmd": "params", "payload": {...}}    ->  incremental parameter/formula rebuild
    {"cmd": "quit"}
"""

from __future__ import annotations

import json
import sys

from viewer.buildlib import build_all


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            command = json.loads(line)
        except ValueError:
            continue
        cmd = command.get("cmd")
        if cmd == "quit":
            break
        if cmd == "build":
            print(json.dumps(build_all(reload_modules=True)), flush=True)
        elif cmd == "params":
            payload = command.get("payload") or {}
            print(
                json.dumps(
                    build_all(reload_modules=False, param_mutation=payload)
                ),
                flush=True,
            )


if __name__ == "__main__":
    main()
