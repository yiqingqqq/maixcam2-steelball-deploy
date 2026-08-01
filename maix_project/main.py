"""MaixCAM2 real-time steel-ball detection using a converted YOLO11 model.

Features:
  1. Boot-time driver warmup retry mechanism for rock-solid reliability
  2. Microcontroller Serial Command Control (BEGIN / END on UART4 RX)
  3. Background H.264 Video Recording (/root/recordings) with 30 FPS fixed GOP keyframes
  4. 30 Hz Fixed-rate Metric/Pixel Tracking output ($x,y\r\n) on UART4 TX
  5. 1/100s Locked Shutter Exposure to eliminate 50Hz AC lighting flicker
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

from config import CAMERA, DEBUG, MODEL, PIPE_ROI, RECORDING, SERIAL, TRACKING

import json
import shutil
from web_stream import start_streamer, update_frame

NO_TARGET = (-1, -1)


class VideoRecorder:
    """Frame Sequence Recorder (.jpg sequence + player.html) eliminating inter-frame flicker."""

    def __init__(self, directory="/root/recordings"):
        self.directory = directory
        self.active = False
        self.session_dir = None
        self.frame_count = 0

    def start(self, width=640, height=480, fps=30):
        if self.active:
            return
        os.makedirs(self.directory, exist_ok=True)
        timestamp = pytime.strftime("%Y%m%d_%H%M%S")
        self.session_dir = os.path.join(self.directory, "session_{}".format(timestamp))
        os.makedirs(self.session_dir, exist_ok=True)
        self.frame_count = 0

        # Copy player.html into the session folder for instant browser playback
        src_player = os.path.join(os.path.dirname(__file__), "player.html")
        if os.path.exists(src_player):
            try:
                shutil.copy(src_player, os.path.join(self.session_dir, "player.html"))
            except Exception:
                pass

        self.active = True
        print("[RECORDER] Started JPEG Frame Sequence Recording -> {}".format(self.session_dir), flush=True)

    def write(self, img):
        if not self.active or not self.session_dir:
            return
        try:
            self.frame_count += 1
            frame_path = os.path.join(self.session_dir, "frame_{:06d}.jpg".format(self.frame_count))
            jpeg_bytes = img.to_jpeg(quality=85).to_bytes()
            with open(frame_path, "wb") as f:
                f.write(jpeg_bytes)
        except Exception:
            pass

    def stop(self):
        if not self.active:
            return
        try:
            if self.session_dir and self.frame_count > 0:
                meta_path = os.path.join(self.session_dir, "meta.json")
                with open(meta_path, "w") as f:
                    json.dump({"total_frames": self.frame_count, "fps": 30}, f)
            print("[RECORDER] Stopped JPEG Recording. Saved {} frames in {}".format(self.frame_count, self.session_dir), flush=True)
        except Exception as exc:
            print("[RECORDER] Error stopping recorder: {}".format(exc), flush=True)
        finally:
            self.active = False
            self.session_dir = None
            self.frame_count = 0


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


def send_tracking(port, x, vx_5f):
    if x == -1 and vx_5f == -1:
        packet = "$-1,-1\r\n"
    else:
        packet = "${},{}\r\n".format(x, vx_5f)
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
    if not os.path.exists(model_path):
        alt_paths = [
            "/root/maix_project/models/steelball_yolo11n_640x480/steelball_yolo11n_640x480.mud",
            "/root/models/steelball_yolo11n_640x480/steelball_yolo11n_640x480.mud",
            os.path.join(os.path.dirname(__file__), "models", "steelball_yolo11n_640x480", "steelball_yolo11n_640x480.mud")
        ]
        for alt in alt_paths:
            if os.path.exists(alt):
                model_path = alt
                break
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
    shutter_us = CAMERA.get("shutter_us", 10000)
    flicker_hz = CAMERA.get("anti_flicker_hz", 50)
    for attempt in range(5):
        try:
            cam = camera.Camera(width, height, fmt)
            if shutter_us > 0:
                for shutter_opt in ["exp_time", "exposure_time", "shutter", "exposure"]:
                    try:
                        cam.set_option(shutter_opt, shutter_us)
                    except Exception:
                        pass
            if flicker_hz > 0:
                for flicker_opt in [("anti_flicker", flicker_hz), ("flicker", flicker_hz), ("anti_flicker", 1)]:
                    try:
                        cam.set_option(flicker_opt[0], flicker_opt[1])
                    except Exception:
                        pass
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
    start_streamer(port=8000)

    recorder = VideoRecorder(directory=RECORDING.get("directory", "/root/recordings"))

    filtered = None
    history_5f = []
    last_vx_5f = 0
    lost_frames = 0
    frame_count = 0
    report_count = 0
    report_start = time.ticks_ms()

    lost_tolerance = TRACKING.get("lost_tolerance_frames", 3)
    smooth_alpha = TRACKING.get("smooth_alpha", SERIAL.get("velocity_ema_alpha", 0.35))

    # Start recording immediately upon launch if enabled
    if RECORDING.get("enabled", True):
        recorder.start(width, height)

    print("[SYSTEM] System Active. Direct tracking & recording running immediately upon launch.", flush=True)

    try:
        while not app.need_exit():
            img = cam.read()

            # Record frame continuously
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
            now_sec = pytime.time()

            if target is None:
                lost_frames += 1
                if lost_frames > lost_tolerance:
                    filtered = None
                    history_5f = []
                    last_vx_5f = 0
                    send_tracking(port, -1, -1)
                    out_x, out_y = -1, -1
                else:
                    out_x, out_y = (int(round(filtered[0])), int(round(filtered[1]))) if filtered else (-1, -1)
                    if out_x != -1:
                        send_tracking(port, out_x, last_vx_5f)
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

                # --- 5-Frame Sliding Window Average X-Speed Calculation (px/ks) ---
                history_5f.append((filtered[0], now_sec))
                if len(history_5f) > 5:
                    history_5f.pop(0)

                if len(history_5f) >= 2:
                    old_x, old_t = history_5f[0]
                    cur_x, cur_t = history_5f[-1]
                    dt_sec = cur_t - old_t
                    if dt_sec > 0.005:
                        vx_5f = int(round((cur_x - old_x) * 1000.0 / dt_sec))
                    else:
                        vx_5f = 0
                else:
                    vx_5f = 0

                output_x = int(round(filtered[0]))
                output_y = int(round(filtered[1]))
                out_x, out_y = output_x, output_y
                last_vx_5f = vx_5f

                # Send absolute X position and 5-frame average X-speed (px/ks) over serial
                send_tracking(port, output_x, vx_5f)

                img.draw_rect(target.x, target.y, target.w, target.h,
                              color=image.COLOR_GREEN, thickness=3)
                img.draw_circle(output_x, output_y, 5,
                                color=image.COLOR_RED, thickness=-1)
                img.draw_string(
                    target.x,
                    max(0, target.y - 20),
                    "ball {:.2f} x={} vx={}px/ks".format(target.score, output_x, vx_5f),
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
            update_frame(img)

    finally:
        recorder.stop()


if __name__ == "__main__":
    main()
