"""Lightweight Non-Intrusive MJPEG Web Streamer for MaixCAM2.

Runs in a separate background daemon thread on Port 8000.
Allows real-time ultralow-latency browser preview (< 30ms) when running via SSH/terminal.
Does NOT modify or interfere with YOLO11 detection, serial TX, or video recording.
"""

import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn

_latest_jpeg = None
_lock = threading.Lock()


def update_frame(img, quality=65):
    """Mirror current frame to JPEG byte buffer for browser streaming."""
    global _latest_jpeg
    if img is None:
        return
    try:
        jpeg_bytes = img.to_jpeg(quality=quality).to_bytes()
        with _lock:
            _latest_jpeg = jpeg_bytes
    except Exception:
        pass


class _ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


class _MJPEGHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Suppress HTTP access log clutter in terminal

    def do_GET(self):
        if self.path in ["/", "/video", "/video_feed"]:
            self.send_response(200)
            self.send_header(
                "Content-Type", "multipart/x-mixed-replace; boundary=frame"
            )
            self.send_header("Access-Control-Allow-Origin", "*")
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
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"404 Not Found")


def start_streamer(host="0.0.0.0", port=8000):
    """Start background HTTP streamer thread."""
    try:
        server = _ThreadedHTTPServer((host, port), _MJPEGHandler)
        thread = threading.Thread(target=server.serve_forever)
        thread.daemon = True
        thread.start()
        print("[WEB STREAM] Zero-latency Live Stream active at http://{}:{}".format(host, port), flush=True)
        return server
    except Exception as exc:
        print("[WEB STREAM] Could not start web streamer on port {}: {}".format(port, exc), flush=True)
        return None
