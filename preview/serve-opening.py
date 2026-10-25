"""Serve the opening preview against the real theme package.

  python preview/serve-opening.py            # http://127.0.0.1:52880/
  python preview/serve-opening.py --port 52881

The client bundle is loaded through the same module-loader shim the DSH page
uses, so the preview exercises the shipped code rather than a copy.
"""
import argparse
import mimetypes
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / "dsh-theme-sandrone"
PREVIEW = Path(__file__).resolve().parent

STATIC = {
    "client.js": PKG / "lib" / "client.js",
    "theme.css": PKG / "theme" / "theme.css",
    "opening.json": PKG / "assets" / "opening.json",
    "opening-art.webp": PKG / "assets" / "opening-art.webp",
    "opening-score.m4a": PKG / "assets" / "opening-score.m4a",
    "opening-score-local.m4a": PKG / "assets" / "opening-score-local.m4a",
    "trace.mp4": PKG / "assets" / "trace.mp4",
    "background.webp": PKG / "assets" / "background.webp",
}


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, pattern, *args):
        pass

    def _send(self, body, content_type, status=200, extra=None, head=False):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        if not head:
            self.wfile.write(body)

    def do_HEAD(self):
        self._dispatch(True)

    def do_GET(self):
        self._dispatch(False)

    def _dispatch(self, head):
        path = unquote(urlparse(self.path).path)
        if path in ("/", "/opening.html"):
            return self._send((PREVIEW / "opening.html").read_bytes(), "text/html; charset=utf-8", head=head)
        if path == "/theme-sandrone/report":
            self.send_response(204)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        prefix = "/theme-sandrone/"
        if path.startswith(prefix):
            key = path[len(prefix):]
            target = STATIC.get(key)
            if target is None or not target.is_file():
                return self._send(b"not found", "text/plain", 404, head=head)
            body = target.read_bytes()
            content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
            if content_type.startswith("text/") or content_type.endswith("javascript"):
                content_type += "; charset=utf-8"
            range_header = self.headers.get("Range")
            if range_header:
                match = re.match(r"bytes=(\d*)-(\d*)$", range_header.strip())
                if match:
                    size = len(body)
                    start = int(match.group(1)) if match.group(1) else size - int(match.group(2))
                    end = int(match.group(2)) if match.group(1) and match.group(2) else size - 1
                    if 0 <= start <= end < size:
                        chunk = body[start : end + 1]
                        return self._send(
                            chunk,
                            content_type,
                            206,
                            {"Content-Range": f"bytes {start}-{end}/{size}", "Accept-Ranges": "bytes"},
                            head=head,
                        )
            return self._send(body, content_type, 200, {"Accept-Ranges": "bytes"}, head=head)
        return self._send(b"not found", "text/plain", 404, head=head)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=52880)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"http://127.0.0.1:{args.port}/", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
