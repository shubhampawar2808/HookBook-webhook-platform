"""Minimal local webhook receiver for HookForge E2E validation.

Listens on 127.0.0.1:9999 and records the last N requests for inspection.
Does not verify HMAC itself (validator script does); returns configurable status.

Usage:
  python scripts/local_webhook_receiver.py
  python scripts/local_webhook_receiver.py --status 500
"""

from __future__ import annotations

import argparse
import json
import threading
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

STATE = {
    "requests": [],
    "status_code": 200,
    "lock": threading.Lock(),
}
STATE_FILE = Path(__file__).resolve().parents[1] / "tmp" / "webhook_receiver_state.json"


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        record = {
            "received_at": datetime.now(UTC).isoformat(),
            "path": self.path,
            "headers": {k: v for k, v in self.headers.items()},
            "body": body.decode("utf-8", errors="replace"),
            "body_bytes_len": len(body),
        }
        with STATE["lock"]:
            STATE["requests"].append(record)
            STATE["requests"] = STATE["requests"][-50:]
            status = int(STATE["status_code"])
            _persist()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"ok":true}')

    def do_GET(self) -> None:  # noqa: N802
        if self.path.startswith("/__status"):
            with STATE["lock"]:
                payload = {
                    "status_code": STATE["status_code"],
                    "count": len(STATE["requests"]),
                    "last": STATE["requests"][-1] if STATE["requests"] else None,
                }
            data = json.dumps(payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(data)
            return
        if self.path.startswith("/__set/"):
            # /__set/500
            try:
                code = int(self.path.rsplit("/", 1)[-1])
            except ValueError:
                self.send_response(400)
                self.end_headers()
                return
            with STATE["lock"]:
                STATE["status_code"] = code
                _persist()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"set":true}')
            return
        if self.path.startswith("/__reset"):
            with STATE["lock"]:
                STATE["requests"] = []
                STATE["status_code"] = 200
                _persist()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"reset":true}')
            return
        self.send_response(404)
        self.end_headers()


def _persist() -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps(
            {
                "status_code": STATE["status_code"],
                "requests": STATE["requests"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9999)
    parser.add_argument("--status", type=int, default=200)
    args = parser.parse_args()
    STATE["status_code"] = args.status
    _persist()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"webhook_receiver listening on http://{args.host}:{args.port}/hooks")
    print("control: GET /__status  GET /__set/<code>  GET /__reset")
    server.serve_forever()


if __name__ == "__main__":
    main()
