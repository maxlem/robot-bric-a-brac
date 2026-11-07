"""Live 3D viewer for the CAD parts.

Watches ``cad/*.py`` and ``cad/fixtures/*.py``, rebuilds on save, and pushes
the result to the browser over SSE. The page reloads the mesh when a build
succeeds. Changes to the viewer itself need a server restart.

    cad/.venv/bin/python cad/viewer/server.py
    cad/.venv/bin/python cad/viewer/server.py --open --port 8765

The page uses three.js from a CDN, so the first load needs network access.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import queue
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

CAD = Path(__file__).resolve().parents[1]
STATIC = Path(__file__).resolve().parent / "static"
OUT = CAD / "build" / "viewer"
STATE = OUT / "state.json"

WATCH_PATTERNS = ("*.py", "fixtures/*.py")
POLL_S = 0.4
DEBOUNCE_S = 0.25


def snapshot() -> dict[Path, float]:
    """Modification times of every Python file the build depends on."""
    files: dict[Path, float] = {}
    for pattern in WATCH_PATTERNS:
        for path in CAD.glob(pattern):
            if ".venv" in path.parts or "build" in path.parts:
                continue
            try:
                files[path] = path.stat().st_mtime
            except OSError:
                pass
    return files


class Builder:
    """Drives the long-lived worker and fans the result out to subscribers."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.state = self._load()
        self.subscribers: list[queue.Queue] = []
        self._sub_lock = threading.Lock()
        self._worker: subprocess.Popen | None = None
        self._log = None
        self._log_path = OUT / "worker.log"

    @staticmethod
    def _load() -> dict:
        try:
            return json.loads(STATE.read_text())
        except (OSError, ValueError):
            return {"built_at": 0, "duration_ms": 0, "parts": []}

    def subscribe(self) -> queue.Queue:
        q: queue.Queue = queue.Queue()
        with self._sub_lock:
            self.subscribers.append(q)
        return q

    def unsubscribe(self, q: queue.Queue) -> None:
        with self._sub_lock:
            if q in self.subscribers:
                self.subscribers.remove(q)

    def _broadcast(self, state: dict) -> None:
        with self._sub_lock:
            for q in list(self.subscribers):
                q.put(state)

    def _start_worker(self) -> None:
        OUT.mkdir(parents=True, exist_ok=True)
        self._log = self._log_path.open("w")
        self._worker = subprocess.Popen(
            [sys.executable, "-m", "viewer.worker"],
            cwd=CAD,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=self._log,
            text=True,
            bufsize=1,
        )

    def _stop_worker(self) -> None:
        if self._worker is not None:
            try:
                self._worker.stdin.write('{"cmd":"quit"}\n')
                self._worker.stdin.flush()
                self._worker.wait(timeout=2)
            except Exception:
                self._worker.kill()
            self._worker = None
        if self._log is not None:
            self._log.close()
            self._log = None

    def _worker_error(self) -> str:
        try:
            tail = self._log_path.read_text()[-2000:].strip()
        except OSError:
            tail = ""
        return tail or "worker exited without output"

    def build(self, command: dict | None = None) -> dict:
        cmd_obj = command or {"cmd": "build"}
        with self.lock:
            try:
                if self._worker is None or self._worker.poll() is not None:
                    self._start_worker()
                self._worker.stdin.write(json.dumps(cmd_obj) + "\n")
                self._worker.stdin.flush()
                line = self._worker.stdout.readline()
                if not line:
                    raise RuntimeError(self._worker_error())
                state = json.loads(line)
            except Exception as exc:
                self._stop_worker()
                state = {
                    "built_at": time.time(),
                    "duration_ms": 0,
                    "parts": [
                        {
                            "module": "viewer.worker",
                            "name": "build",
                            "status": "error",
                            "error": str(exc),
                            "duration_ms": 0,
                        }
                    ],
                }
            self.state = state
            self._broadcast(state)
            return state


def watch(builder: Builder, stop: threading.Event) -> None:
    last = snapshot()
    while not stop.is_set():
        time.sleep(POLL_S)
        now = snapshot()
        if now == last:
            continue
        time.sleep(DEBOUNCE_S)
        last = snapshot()
        builder.build()


class Handler(BaseHTTPRequestHandler):
    builder: Builder

    def log_message(self, *args) -> None:  # keep the console quiet
        pass

    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]
        if path == "/":
            self._file(STATIC / "index.html", "text/html; charset=utf-8", cache=False)
        elif path.startswith("/static/"):
            self._file(STATIC / Path(path[len("/static/") :]).name, cache=False)
        elif path == "/api/state":
            self._json(self.builder.state)
        elif path == "/api/events":
            self._events()
        elif path.startswith("/api/mesh/"):
            self._file(OUT / Path(path[len("/api/mesh/") :]).name, "model/stl", cache=False)
        else:
            self.send_error(404)

    def do_POST(self) -> None:
        path = self.path.split("?", 1)[0]
        if path == "/api/rebuild":
            threading.Thread(target=self.builder.build, daemon=True).start()
            self._json({"ok": True})
        elif path == "/api/params":
            length = int(self.headers.get("Content-Length", "0") or "0")
            raw = self.rfile.read(length) if length > 0 else b"{}"
            try:
                payload = json.loads(raw.decode("utf-8"))
            except ValueError:
                self.send_error(400)
                return
            cmd = {"cmd": "params", "payload": payload}
            threading.Thread(
                target=self.builder.build, args=(cmd,), daemon=True
            ).start()
            self._json({"ok": True})
        else:
            self.send_error(404)

    def _file(self, path: Path, content_type: str | None = None, cache: bool = True) -> None:
        try:
            data = path.read_bytes()
        except OSError:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header(
            "Content-Type",
            content_type or mimetypes.guess_type(path.name)[0] or "application/octet-stream",
        )
        self.send_header("Content-Length", str(len(data)))
        if not cache:
            self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _json(self, obj: dict) -> None:
        data = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _events(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "keep-alive")
        self.end_headers()

        q = self.builder.subscribe()
        try:
            self._send_event(self.builder.state)
            while True:
                try:
                    self._send_event(q.get(timeout=15))
                except queue.Empty:
                    self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            self.builder.unsubscribe(q)

    def _send_event(self, state: dict) -> None:
        payload = json.dumps(state).encode()
        self.wfile.write(b"event: state\ndata: " + payload + b"\n\n")
        self.wfile.flush()


def main() -> None:
    parser = argparse.ArgumentParser(description="Live 3D viewer for the CAD parts.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--open", action="store_true", help="open the browser")
    args = parser.parse_args()

    builder = Builder()
    Handler.builder = builder

    stop = threading.Event()
    threading.Thread(target=watch, args=(builder, stop), daemon=True).start()
    threading.Thread(target=builder.build, daemon=True).start()

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    url = f"http://{args.host}:{args.port}/"
    print(f"CAD viewer on {url}")
    print("watching cad/**/*.py — save a file to rebuild")
    if args.open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        server.server_close()


if __name__ == "__main__":
    main()
