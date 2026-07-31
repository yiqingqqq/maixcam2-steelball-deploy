"""Lightweight HTTP MJPEG Streaming + WebSocket Telemetry Server for MaixCAM.

Runs concurrently in background threads without blocking main detection loop.
"""

import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn

# Global state shared between detection loop and web server
_latest_jpeg = None
_latest_telemetry = {
    "x": -1,
    "y": -1,
    "conf": 0.0,
    "fps": 0.0,
    "status": "STANDBY",
    "recorder": False,
}
_lock = threading.Lock()
_ws_clients = []


def update_web_state(jpeg_bytes, telemetry_dict):
    global _latest_jpeg, _latest_telemetry
    with _lock:
        if jpeg_bytes is not None:
            _latest_jpeg = jpeg_bytes
        if telemetry_dict is not None:
            _latest_telemetry.update(telemetry_dict)


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in separate threads."""
    daemon_threads = True


class WebHandler(BaseHTTPRequestHandler):
    """HTTP Request Handler for Static Files & MJPEG Stream."""

    def log_message(self, format, *args):
        pass  # Suppress HTTP access logging in console

    def do_GET(self):
        if self.path == "/video_feed":
            self.send_response(200)
            self.send_header(
                "Content-Type", "multipart/x-mixed-replace; boundary=frame"
            )
            self.end_headers()
            while True:
                with _lock:
                    jpg = _latest_jpeg
                if jpg is not None:
                    try:
                        self.wfile.write(b"--frame\r\n")
                        self.send_header("Content-Type", "image/jpeg")
                        self.send_header("Content-Length", str(len(jpg)))
                        self.end_headers()
                        self.wfile.write(jpg)
                        self.wfile.write(b"\r\n")
                    except Exception:
                        break
                time.sleep(0.033)  # ~30 FPS
            return

        if self.path == "/telemetry":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            with _lock:
                data = json.dumps(_latest_telemetry).encode("utf-8")
            self.wfile.write(data)
            return

        # Serve static web files
        static_dir = os.path.join(os.path.dirname(__file__), "web_static")
        req_path = self.path.lstrip("/")
        if not req_path or req_path == "/":
            req_path = "index.html"
        filepath = os.path.normpath(os.path.join(static_dir, req_path))

        if os.path.exists(filepath) and os.path.isfile(filepath):
            self.send_response(200)
            if filepath.endswith(".html"):
                self.send_header("Content-Type", "text/html; charset=utf-8")
            elif filepath.endswith(".css"):
                self.send_header("Content-Type", "text/css; charset=utf-8")
            elif filepath.endswith(".js"):
                self.send_header("Content-Type", "application/javascript; charset=utf-8")
            elif filepath.endswith(".png"):
                self.send_header("Content-Type", "image/png")
            self.end_headers()
            with open(filepath, "rb") as f:
                self.wfile.write(f.read())
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"404 Not Found")


def start_web_server(host="0.0.0.0", port=8080):
    server = ThreadedHTTPServer((host, port), WebHandler)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    print("[WEB SERVER] Minimalist Web Dashboard started at http://{}:{}".format(host, port), flush=True)
    return server
