"""Small authenticated WordPress API fixture for container tests."""

import base64
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse


class WordPressHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        expected = "Basic " + base64.b64encode(
            b"test-user:test password ${literal}"
        ).decode()
        if self.headers.get("Authorization") != expected:
            self.respond(401, {"code": "rest_not_logged_in"})
            return

        path = urlparse(self.path).path
        if path == "/wp-json/wp/v2/users/me":
            self.respond(200, {"id": 7, "name": "Test User", "roles": ["editor"]})
        elif path == "/wp-json/wp/v2/posts":
            self.respond(200, [{"id": 42, "title": {"rendered": "Test post"}}])
        elif path == "/wp-json/wp/v2/users":
            self.respond(403, {"code": "rest_cannot_view"})
        else:
            self.respond(404, {"code": "rest_no_route"})

    def respond(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_):
        pass


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8080), WordPressHandler).serve_forever()
