"""Standard Dual-Mode MJPEG/HTML Web Streamer for MaixCAM2.

Solves the blank/white screen issue on Safari and modern Chrome by providing:
1. Root '/' route returning a responsive dark-mode HTML dashboard.
2. '/video_feed' route serving MJPEG video stream.
3. '/frame.jpg' fallback route serving single JPEG snapshots.
"""

import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn

_latest_jpeg = None
_lock = threading.Lock()

HTML_DASHBOARD = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MaixCAM 实时视觉监控</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        html, body { background: #0f172a !important; color: #f8fafc; min-height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 16px; }
        .card { background: #1e293b; border-radius: 16px; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.5); overflow: hidden; width: 100%; max-width: 800px; border: 1px solid #334155; }
        .header { padding: 16px 24px; background: #0f172a; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #334155; }
        .title { font-size: 16px; font-weight: 700; color: #38bdf8; display: flex; align-items: center; gap: 8px; }
        .dot { width: 10px; height: 10px; background: #22c55e; border-radius: 50%; display: inline-block; animation: pulse 1.5s infinite; }
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.4; } 100% { opacity: 1; } }
        .view-box { position: relative; width: 100%; background: #000; display: flex; align-items: center; justify-content: center; min-height: 480px; overflow: hidden; }
        .view-box img { width: 100%; height: auto; display: block; object-fit: contain; }
        .spinner { position: absolute; border: 4px solid rgba(255,255,255,0.1); border-left-color: #38bdf8; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .footer { padding: 12px 24px; font-size: 13px; color: #94a3b8; display: flex; justify-content: space-between; font-family: monospace; background: #0f172a; border-top: 1px solid #334155; }
    </style>
</head>
<body>
<div class="card">
    <div class="header">
        <div class="title"><span class="dot"></span> MaixCAM2 高清实时图传</div>
        <span style="font-size: 12px; color: #38bdf8; font-weight: 600;" id="fpsBadge">已连接</span>
    </div>
    <div class="view-box">
        <div class="spinner" id="loader"></div>
        <img id="stream" src="" alt="Live Stream" style="display: none;">
    </div>
    <div class="footer">
        <span>模式: JS 双缓存平滑图传</span>
        <span id="status">帧率: 渲染中...</span>
    </div>
</div>

<script>
    (function() {
        const img = document.getElementById('stream');
        const loader = document.getElementById('loader');
        const status = document.getElementById('status');
        const fpsBadge = document.getElementById('fpsBadge');
        
        let frameCount = 0;
        let lastTime = Date.now();
        let isFirstFrame = true;

        function fetchFrame() {
            const tempImg = new Image();
            const timestamp = Date.now();

            tempImg.onload = function() {
                img.src = tempImg.src;
                if (isFirstFrame) {
                    isFirstFrame = false;
                    loader.style.display = 'none';
                    img.style.display = 'block';
                }
                frameCount++;
                if (timestamp - lastTime >= 1000) {
                    const fps = Math.round((frameCount * 1000) / (timestamp - lastTime));
                    status.innerText = "实时帧率: " + fps + " FPS";
                    fpsBadge.innerText = "● LIVE " + fps + " FPS";
                    frameCount = 0;
                    lastTime = timestamp;
                }
                setTimeout(fetchFrame, 30);
            };

            tempImg.onerror = function() {
                setTimeout(fetchFrame, 100);
            };

            tempImg.src = "/frame.jpg?t=" + timestamp;
        }

        fetchFrame();
    })();
</script>
</body>
</html>
"""


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
        pass  # Suppress HTTP access log clutter

    def do_GET(self):
        if self.path in ["/", "/index.html"]:
            # Serve Dashboard HTML Page
            content = HTML_DASHBOARD.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return

        elif self.path in ["/video_feed", "/video"]:
            # Serve MJPEG Stream
            self.send_response(200)
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
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

        elif self.path.startswith("/frame.jpg"):
            # Serve single JPEG snapshot with no caching
            with _lock:
                jpg = _latest_jpeg
            if jpg is not None:
                self.send_response(200)
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Content-Length", str(len(jpg)))
                self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                self.end_headers()
                self.wfile.write(jpg)
            else:
                self.send_response(503)
                self.end_headers()
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
        print("[WEB STREAM] Zero-latency Live Dashboard active at http://{}:{}".format(host, port), flush=True)
        return server
    except Exception as exc:
        print("[WEB STREAM] Could not start web streamer on port {}: {}".format(port, exc), flush=True)
        return None
