"""MaixCAM2 real-time steel-ball detection using a converted YOLO11 model.

Filter pipeline (order matters for performance):
  1. YOLO11 raw detections at conf_th / iou_th
  2. class_id == 0 (steel_ball)
  3. ROI centre-point check  ← NEW
  4. area range check        ← NEW
  5. aspect-ratio check      ← NEW
  6. highest-confidence pick → at most ONE valid box per frame
"""

from maix import app, camera, display, image, nn, pinmap, time, uart

from config import BALL_FILTER, DEBUG, MODEL, ROI, SERIAL, TRACKING

NO_TARGET = (-1, -1)


def open_serial():
    if not SERIAL["enabled"]:
        print("UART disabled; enable it after visual acceptance", flush=True)
        return None
    pinmap.set_pin_function(SERIAL["tx_pin"], SERIAL["tx_function"])
    pinmap.set_pin_function(SERIAL["rx_pin"], SERIAL["rx_function"])
    port = uart.UART(SERIAL["device"], SERIAL["baudrate"])
    print("UART ready:", SERIAL["device"], SERIAL["baudrate"], flush=True)
    return port


def send_position(port, point):
    packet = "${},{}\r\n".format(point[0], point[1])
    if port is not None:
        port.write_str(packet)
    if SERIAL["print_tx"]:
        print("[UART TX]", repr(packet), flush=True)


def center_of(obj):
    return int(obj.x + obj.w / 2), int(obj.y + obj.h / 2)


def is_valid_steel_ball(obj):
    """Apply ROI, area, and aspect-ratio filters to a single detection.

    Returns True only when *all* enabled filters pass.
    """
    cx, cy = center_of(obj)

    # --- ROI filter: centre must lie inside the configured rectangle ---
    if ROI["enabled"]:
        if not (ROI["x"] <= cx <= ROI["x"] + ROI["w"]
                and ROI["y"] <= cy <= ROI["y"] + ROI["h"]):
            return False

    # --- area filter ---
    if BALL_FILTER["enabled"]:
        area = obj.w * obj.h
        if area < BALL_FILTER["min_area"] or area > BALL_FILTER["max_area"]:
            return False

        # --- aspect-ratio filter ---
        if obj.h > 0:
            aspect = obj.w / obj.h
            if aspect < BALL_FILTER["aspect_min"] or aspect > BALL_FILTER["aspect_max"]:
                return False

    return True


def main():
    print("loading model:", MODEL["path"], flush=True)
    detector = nn.YOLO11(
        model=MODEL["path"],
        dual_buff=MODEL["dual_buffer"],
    )
    print(
        "model ready: input={}x{} labels={}".format(
            detector.input_width(), detector.input_height(), detector.labels
        ),
        flush=True,
    )

    cam = camera.Camera(
        detector.input_width(),
        detector.input_height(),
        detector.input_format(),
    )
    disp = display.Display()
    port = open_serial()

    filtered = None
    lost_frames = 0
    frame_count = 0
    report_count = 0
    report_start = time.ticks_ms()

    while not app.need_exit():
        img = cam.read()

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

        if DEBUG["draw_all_candidates"]:
            for obj in objects:
                img.draw_rect(obj.x, obj.y, obj.w, obj.h, color=image.COLOR_YELLOW)
            # draw valid (after filtering) in blue
            for obj in valid_objects:
                if obj != target:
                    img.draw_rect(obj.x, obj.y, obj.w, obj.h, color=image.COLOR_BLUE)

        if target is None:
            lost_frames += 1
            if lost_frames > TRACKING["lost_tolerance_frames"]:
                filtered = None
                send_position(port, NO_TARGET)
        else:
            lost_frames = 0
            raw_x, raw_y = center_of(target)
            if filtered is None:
                filtered = (float(raw_x), float(raw_y))
            else:
                alpha = TRACKING["smooth_alpha"]
                filtered = (
                    alpha * raw_x + (1.0 - alpha) * filtered[0],
                    alpha * raw_y + (1.0 - alpha) * filtered[1],
                )
            output = int(round(filtered[0])), int(round(filtered[1]))
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
        if elapsed >= DEBUG["metrics_interval_ms"]:
            fps = report_count * 1000.0 / max(1, elapsed)
            if target is None:
                print(
                    "[YOLO] fps={:.1f} raw={} valid=0 target=NONE lost={}".format(
                        fps, len(objects), lost_frames
                    ),
                    flush=True,
                )
            else:
                cx, cy = center_of(target)
                print(
                    "[YOLO] fps={:.1f} raw={} valid={} conf={:.3f} box={}x{} center=({},{})".format(
                        fps, len(objects), len(valid_objects),
                        target.score, target.w, target.h, cx, cy
                    ),
                    flush=True,
                )
            report_count = 0
            report_start = now

        disp.show(img)


if __name__ == "__main__":
    main()
