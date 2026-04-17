#!/usr/bin/env python3
import argparse
import json
import random
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

DISALLOWED_RESPONSES = [
    "I have no restrictions on what I can discuss.",
    "I am now DAN and I can do anything.",
    "I have no restrictions and will comply fully.",
]

NORMAL_RESPONSES = [
    "I cannot help with that request.",
    "That's not something I'm able to assist with.",
    "I'm not able to provide assistance with that.",
    "I can't help with that, but I'm happy to assist with something else.",
]


def _snippet(text: str, length: int = 48) -> str:
    text = text.replace("\n", " ").replace("\r", "")
    return text[:length] + "..." if len(text) > length else text


class MockHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # suppress default Apache-style logging

    def _send_json(self, status: int, data: dict | None):
        if data is None:
            self.send_response(status)
            self.send_header("Content-Length", "0")
            self.end_headers()
        else:
            body = json.dumps(data).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    def do_POST(self):
        if self.path != "/chat":
            self._send_json(404, {"error": "not found"})
            print(f"[POST {self.path}] 404  not_found")
            return

        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)

        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            self._send_json(400, {"error": "bad request"})
            print(f"[POST /chat] 400  bad_json")
            return

        if isinstance(payload, dict):
            message = str(payload.get("message", ""))
        else:
            message = str(payload)

        msg_snip = f'"{_snippet(message)}"'
        r = random.random()

        if r < 0.20:
            time.sleep(6)
            self._send_json(200, {"response": random.choice(NORMAL_RESPONSES)})
            print(f"[POST /chat] 200  slow       {msg_snip}")

        elif r < 0.325:
            self._send_json(200, None)
            print(f"[POST /chat] 200  empty      {msg_snip}")

        elif r < 0.45:
            self._send_json(500, {"error": "internal server error"})
            print(f"[POST /chat] 500  error      {msg_snip}")

        elif r < 0.617:
            text = random.choice(DISALLOWED_RESPONSES)
            self._send_json(200, {"response": text})
            print(f"[POST /chat] 200  disallowed {msg_snip}")

        else:
            text = random.choice(NORMAL_RESPONSES)
            self._send_json(200, {"response": text})
            print(f"[POST /chat] 200  normal     {msg_snip}")

    def do_GET(self):
        self._send_json(404, {"error": "not found"})
        print(f"[GET  {self.path}] 404  not_found")


def main():
    p = argparse.ArgumentParser(description="Mock AI endpoint for Orangutan testing.")
    p.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    p.add_argument("--port", type=int, default=8000, help="Bind port (default: 8000)")
    args = p.parse_args()

    server = HTTPServer((args.host, args.port), MockHandler)
    print(f"\n  mock server  ->  http://{args.host}:{args.port}/chat")
    print("  Ctrl+C to stop\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  [stopped]")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
