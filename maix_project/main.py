"""MaixCAM2 real-time steel-ball detection using a converted YOLO11 model.

Features:
  1. Boot-time driver warmup retry mechanism for rock-solid reliability
  2. Microcontroller Serial Command Control (BEGIN / END on UART4 RX)
  3. Background H.264 Video Recording (/root/recordings)
  4. 30 Hz Fixed-rate Metric/Pixel Tracking output ($x,y\r\n) on UART4 TX
  5. Built-in Minimalist Web Live Video Stream & Telemetry Dashboard (Port 8080)
"""

import ctypes
import os
import sys

# Preload core C++ shared libraries in RTLD_GLOBAL mode for standalone Linux execution
for explicit_lib in [
    "/opt/lib/libax_sys.so",
    "/opt/usr/lib/libtinyalsa.so.2",
    "/usr/local/lib/libonnxruntime.so.1",
]:
    try:
        ctypes.CDLL(explicit_lib, mode=ctypes.RTLD_GLOBAL)
    except Exception:
        pass

import time as pytime
from maix import app, camera, display, image, nn, pinmap, time, uart, video

from config import DEBUG, MODEL, PIPE_ROI, RECORDING, SERIAL, TRACKING, WEB
from web_server import start_web_server, update_web_state

NO_TARGET = (-1, -1)


class VideoRecorder:
    """Background hardware H.264 video recorder for MaixCAM."""

    def __init__(self, directory="/root/recordings"):
        self.directory = directory
        self.active = False
        self.file = None
        self.encoder = None

    def start(self, width=640, height=480):
        if self.active:
            return
        os.makedirs(self.directory, exist_ok=True)
        timestamp = pytime.strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(self.directory, "rec_{}.h264".format(timestamp))
        try:
            self.encoder = video.Encoder(width=width, height=height)
            self.file = open(filepath, "wb")
            self.active = True
            print("[RECORDER] Started recording -> {}".format(filepath), flush=True)
        except Exception as exc:
            print("[RECORDER] Failed to start encoder: {}".format(exc), flush=True)

    def write(self, img):
        if not self.active or self.encoder is None or self.file is None:
            return
        try:
            frame = self.encoder.encode(img)
            if frame:
                self.file.write(frame.to_bytes())
        except Exception:
            pass

    def stop(self):
        if not self.active:
            return
        try:
            if self.file:
                self.file.flush()
                self.file.close()
            print("[RECORDER] Stopped recording and saved file.", flush=True)
        except Exception as exc:
            print("[RECORDER] Error stopping recorder: {}".format(exc), flush=True)
        finally:
            self.active = False
            self.encoder = None
            self.file = None


def open_serial():
    if not SERIAL.get("enabled", True):
        print("UART disabled in config", flush=True)
        return None
    if "tx_pin" in SERIAL and "tx_function" in SERIAL:
        pinmap.set_pin_function(SERIAL["tx_pin"], SERIAL["tx_function"])
    if "rx_pin" in SERIAL and "rx_function" in SERIAL:
        pinmap.set_pin_function(SERIAL["rx_pin"], SERIAL["rx_function"])
    
    for attempt in range(5):
        try:
            port = uart.UART(SERIAL["device"], SERIAL["baudrate"])
            print("UART ready: {} @ {} baud".format(SERIAL["device"], SERIAL["baudrate"]), flush=True)
            return port
        except Exception as exc:
            print("[WARN] UART init attempt {} failed ({}), retrying in 1s...".format(attempt + 1, exc), flush=True)
            time.sleep_ms(1000)
    print("[ERROR] UART init failed after 5 retries", flush=True)
    return None


def send_position(port, point):
    packet = "${},{}\r\n".format(point[0], point[1])
    if port is not None:
        port.write_str(packet)
    if SERIAL.get("print_tx", True):
        print("[UART TX]", repr(packet), flush=True)


def center_of(obj):
    return int(obj.x + obj.w / 2), int(obj.y + obj.h / 2)


def is_valid_steel_ball(obj):
    """Apply ROI, area, and aspect-ratio filters to a single detection."""
    cx, cy = center_of(obj)

    # --- Pipe ROI filter ---
    if PIPE_ROI.get("enabled", False):
        if not (PIPE_ROI["x"] <= cx <= PIPE_ROI["x"] + PIPE_ROI["w"]
                and PIPE_ROI["y"] <= cy <= PIPE_ROI["y"] + PIPE_ROI["h"]):
            return False

    # --- Area filter ---
    area = obj.w * obj.h
    min_area = TRACKING.get("min_box_area_px", 0)
    max_area = TRACKING.get("max_box_area_px", 999999)
    if area < min_area or (max_area > 0 and area > max_area):
        return False

    # --- Aspect-ratio filter ---
    if obj.h > 0:
        aspect = obj.w / obj.h
        aspect_min = TRACKING.get("aspect_min", 0.0)
        aspect_max = TRACKING.get("aspect_max", 10.0)
        if aspect < aspect_min or aspect > aspect_max:
            return False

    return True


def init_detector():
    model_path = MODEL["path"]
    print("loading model:", model_path, flush=True)
    for attempt in range(5):
        try:
            detector = nn.YOLO11(
                model=model_path,
                dual_buff=MODEL.get("dual_buffer", False),
            )
            print("model ready: input={}x{} labels={}".format(
                detector.input_width(), detector.input_height(), detector.labels
            ), flush=True)
            return detector
        except Exception as exc:
            print("[WARN] Model init attempt {} failed ({}), retrying in 1s...".format(attempt + 1, exc), flush=True)
            time.sleep_ms(1000)
    raise RuntimeError("Failed to initialize YOLO11 detector after 5 attempts")


def init_camera(width, height, fmt):
    for attempt in range(5):
        try:
            cam = camera.Camera(width, height, fmt)
            return cam
        except Exception as exc:
            print("[WARN] Camera init attempt {} failed ({}), retrying in 1s...".format(attempt + 1, exc), flush=True)
            time.sleep_ms(1000)
    raise RuntimeError("Failed to initialize Camera after 5 attempts")


def main():
    detector = init_detector()
    width, height = detector.input_width(), detector.input_height()

    cam = init_camera(width, height, detector.input_format())
    disp = display.Display()
    port = open_serial()

    # Start Minimalist Web Dashboard Server in background thread
    if WEB.get("enabled", True):
        try:
            start_web_server(port=WEB.get("port", 8080))
        except Exception as exc:
            print("[WEB SERVER] Could not start web server: {}".format(exc), flush=True)

    recorder = VideoRecorder(directory=RECORDING.get("directory", "/root/recordings"))

    filtered = None
    lost_frames = 0
    frame_count = 0
    report_count = 0
    current_fps = 0.0
    report_start = time.ticks_ms()

    lost_tolerance = TRACKING.get("lost_tolerance_frames", 3)
    smooth_alpha = TRACKING.get("smooth_alpha", SERIAL.get("velocity_ema_alpha", 0.35))

    start_cmd = SERIAL.get("start_cmd", "BEGIN")
    stop_cmd = SERIAL.get("stop_cmd", "END")

    # If wait_command is True (default), boot in standby until receiving BEGIN from MCU
    is_active = not SERIAL.get("wait_command", True)
    rx_buffer = ""

    print("[SYSTEM] Ready. Standby mode: wait_command={}, start_cmd={!r}, stop_cmd={!r}".format(
        SERIAL.get("wait_command", True), start_cmd, stop_cmd), flush=True)

    try:
        while not app.need_exit():
            # --- Check UART RX commands from MCU ---
            if port is not None:
                try:
                    data = port.read()
                    if data:
                        rx_str = data.decode("ascii", errors="ignore")
                        print("[UART RX RAW]", repr(rx_str), flush=True)
                        rx_buffer += rx_str
                        if len(rx_buffer) > 128:
                            rx_buffer = rx_buffer[-128:]
                        upper_buf = rx_buffer.upper()
                        if start_cmd.upper() in upper_buf:
                            print("[UART RX] Matched START command {!r} -> Activating recording & tracking".format(start_cmd), flush=True)
                            is_active = True
                            rx_buffer = ""
                            if RECORDING.get("enabled", True):
                                recorder.start(width, height)
                        elif stop_cmd.upper() in upper_buf:
                            print("[UART RX] Matched STOP command {!r} -> Standby mode & stop recording".format(stop_cmd), flush=True)
                            is_active = False
                            rx_buffer = ""
                            recorder.stop()
                except Exception as exc:
                    pass

            img = cam.read()

            if not is_active:
                img.draw_string(10, 10, "[STANDBY] Waiting for '{}'...".format(start_cmd), color=image.COLOR_YELLOW, scale=1.5)
                disp.show(img)
                if WEB.get("enabled", True):
                    try:
                        jpeg_bytes = img.to_jpeg(quality=WEB.get("jpeg_quality", 60)).to_bytes()
                        update_web_state(jpeg_bytes, {
                            "x": -1, "y": -1, "conf": 0.0,
                            "fps": current_fps, "status": "STANDBY",
                            "recorder": False
                        })
                    except Exception:
                        pass
                time.sleep_ms(30)
                continue

            # Record clean frame when active
            if RECORDING.get("enabled", True):
                if not recorder.active:
                    recorder.start(width, height)
                recorder.write(img)

            # 1. raw YOLO11 detections
            objects = detector.detect(
                img,
                conf_th=MODEL["conf_threshold"],
                iou_th=MODEL["iou_threshold"],
            )

            # 2. keep only steel_ball (class_id == 0)
            objects = [obj for obj in objects if obj.class_id == 0]

            # 3–5. ROI + area + aspect-ratio filtering
            valid_objects = [obj for obj in objects if is_valid_steel_ball(obj)]

            # 6. per-frame single-best by confidence
            target = max(valid_objects, key=lambda obj: obj.score) if valid_objects else None

            if DEBUG.get("draw_all_candidates", True):
                for obj in objects:
                    img.draw_rect(obj.x, obj.y, obj.w, obj.h, color=image.COLOR_YELLOW)
                for obj in valid_objects:
                    if obj != target:
                        img.draw_rect(obj.x, obj.y, obj.w, obj.h, color=image.COLOR_BLUE)

            curr_conf = 0.0
            if target is None:
                lost_frames += 1
                if lost_frames > lost_tolerance:
                    filtered = None
                    send_position(port, NO_TARGET)
                    out_x, out_y = -1, -1
                else:
                    out_x, out_y = (int(filtered[0]), int(filtered[1])) if filtered else (-1, -1)
            else:
                lost_frames = 0
                curr_conf = target.score
                raw_x, raw_y = center_of(target)
                if filtered is None:
                    filtered = (float(raw_x), float(raw_y))
                else:
                    filtered = (
                        smooth_alpha * raw_x + (1.0 - smooth_alpha) * filtered[0],
                        smooth_alpha * raw_y + (1.0 - smooth_alpha) * filtered[1],
                    )
                output = int(round(filtered[0])), int(round(filtered[1]))
                out_x, out_y = output[0], output[1]
                send_position(port, output)

                img.draw_rect(target.x, target.y, target.w, target.h,
                              color=image.COLOR_GREEN, thickness=3)
                img.draw_circle(output[0], output[1], 5,
                                color=image.COLOR_RED, thickness=-1)
                img.draw_string(
                    target.x,
                    max(0, target.y - 20),
                    "ball {:.2f} ({},{})".format(target.score, output[0], output[1]),
                    color=image.COLOR_GREEN,
                )

            frame_count += 1
            report_count += 1
            now = time.ticks_ms()
            elapsed = time.ticks_diff(now, report_start)
            if elapsed >= DEBUG.get("metrics_interval_ms", 1000):
                current_fps = report_count * 1000.0 / max(1, elapsed)
                rec_status = "REC" if recorder.active else "ACTIVE"
                if target is None:
                    print(
                        "[YOLO] fps={:.1f} status={} raw={} valid=0 target=NONE lost={}".format(
                            current_fps, rec_status, len(objects), lost_frames
                        ),
                        flush=True,
                    )
                else:
                    cx, cy = center_of(target)
                    print(
                        "[YOLO] fps={:.1f} status={} raw={} valid={} conf={:.3f} box={}x{} center=({},{})".format(
                            current_fps, rec_status, len(objects), len(valid_objects),
                            target.score, target.w, target.h, cx, cy
                        ),
                        flush=True,
                    )
                report_count = 0
                report_start = now

            disp.show(img)

            # Update Web Server state & stream frame
            if WEB.get("enabled", True):
                try:
                    jpeg_bytes = img.to_jpeg(quality=WEB.get("jpeg_quality", 60)).to_bytes()
                    update_web_state(jpeg_bytes, {
                        "x": out_x, "y": out_y,
                        "conf": float(curr_conf),
                        "fps": float(current_fps),
                        "status": "ACTIVE" if is_active else "STANDBY",
                        "recorder": recorder.active
                    })
                except Exception:
                    pass

    finally:
        recorder.stop()


if __name__ == "__main__":
    main()
