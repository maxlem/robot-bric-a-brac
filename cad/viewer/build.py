"""Build every CAD part once and report the status as JSON.

    cd cad && .venv/bin/python -m viewer.build

Writes ``cad/build/viewer/state.json`` and one STL per part, then prints the
same state to stdout.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from viewer.buildlib import OUT, build_all  # noqa: E402


def main() -> None:
    state = build_all()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "state.json").write_text(json.dumps(state, indent=2))
    print(json.dumps(state))


if __name__ == "__main__":
    main()
