#!/usr/bin/env python3

import argparse
import json
import time
from http.server import BaseHTTPRequestHandler, HTTPServer


MESSAGES = []
NEXT_SEQUENCE = 1


class TechnocoreHandler(BaseHTTPRequestHandler):
    def _send_json(self, status, data):
        body = json.dumps(data, indent=2).encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()

        self.wfile.write(body)

    def do_POST(self):
        global NEXT_SEQUENCE

        if self.path != "/messages":
            self._send_json(
                404,
                {"error": "Not found"},
            )
            return

        try:
            content_length = int(
                self.headers.get("Content-Length", "0")
            )

            raw_body = self.rfile.read(content_length)
            message = json.loads(raw_body.decode("utf-8"))

        except (ValueError, json.JSONDecodeError):
            self._send_json(
                400,
                {"error": "Invalid JSON"},
            )
            return

        required = (
            "room",
            "text",
            "from",
            "timestamp",
            "nonce",
            "signature",
        )

        missing = [
            field
            for field in required
            if field not in message
        ]

        if missing:
            self._send_json(
                400,
                {
                    "error": "Missing required fields",
                    "fields": missing,
                },
            )
            return

        stored = {
            "seq": NEXT_SEQUENCE,
            "timestamp": int(time.time()),
            "room": message["room"],
            "from": message["from"],
            "nonce": message["nonce"],
            "text": message["text"],
            "signature": message["signature"],
        }

        MESSAGES.append(stored)
        NEXT_SEQUENCE += 1

        self._send_json(
            201,
            {
                "ok": True,
                "posted": stored,
            },
        )

    def do_GET(self):
        if self.path == "/messages":
            self._send_json(
                200,
                {
                    "messages": MESSAGES,
                },
            )
            return

        self._send_json(
            404,
            {"error": "Not found"},
        )

    def log_message(self, format, *args):
        print(
            f"[mock-server] {self.address_string()} - {format % args}"
        )


def main():
    parser = argparse.ArgumentParser(
        description="Local Technocore mock server."
    )

    parser.add_argument(
        "--host",
        default="127.0.0.1",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=8000,
    )

    args = parser.parse_args()

    server = HTTPServer(
        (args.host, args.port),
        TechnocoreHandler,
    )

    print(
        f"Technocore mock server running at "
        f"http://{args.host}:{args.port}"
    )

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping mock server...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
