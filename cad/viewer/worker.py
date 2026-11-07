"""Long-lived build worker.

Imports build123d once, then rebuilds on request. The server talks to it over
newline-delimited JSON on stdin/stdout:

    {"cmd": "build"}  ->  one line of state JSON
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
        if command.get("cmd") == "quit":
            break
        if command.get("cmd") == "build":
            print(json.dumps(build_all()), flush=True)


if __name__ == "__main__":
    main()
