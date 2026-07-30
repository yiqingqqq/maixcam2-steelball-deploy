"""MaixCAM2 real-time steel-ball detection using a converted YOLO11 model."""

from maix import app, camera, display, image, nn, pinmap, time, uart

from config import DEBUG, MODEL, SERIAL, TRACKING


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
        objects = detector.detect(
            img,
            conf_th=MODEL["conf_threshold"],
            iou_th=MODEL["iou_threshold"],
        )
        objects = [obj for obj in objects if obj.class_id == 0]
        target = max(objects, key=lambda obj: obj.score) if objects else None

        if DEBUG["draw_all_candidates"]:
            for obj in objects:
                img.draw_rect(obj.x, obj.y, obj.w, obj.h, color=image.COLOR_YELLOW)

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
                    "[YOLO] fps={:.1f} cand={} target=NONE lost={}".format(
                        fps, len(objects), lost_frames
                    ),
                    flush=True,
                )
            else:
                cx, cy = center_of(target)
                print(
                    "[YOLO] fps={:.1f} cand={} conf={:.3f} box={}x{} center=({},{})".format(
                        fps, len(objects), target.score, target.w, target.h, cx, cy
                    ),
                    flush=True,
                )
            report_count = 0
            report_start = now

        disp.show(img)


if __name__ == "__main__":
    main()
