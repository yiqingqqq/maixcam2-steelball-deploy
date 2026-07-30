"""Runtime parameters for the MaixCAM2 steel-ball YOLO detector."""

MODEL = {
    "path": "/root/models/steelball_yolo11n_640x480/steelball_yolo11n_640x480.mud",
    "conf_threshold": 0.40,
    "iou_threshold": 0.50,
    "dual_buffer": False,
}

# Region-of-Interest: only detections whose center falls inside this rect count.
# Format: (x, y, w, h) in pixels. Set all zeros to disable ROI filtering.
ROI = {
    "enabled": True,
    "x": 0,
    "y": 0,
    "w": 640,
    "h": 480,
}

# Steel-ball physical constraints for false-positive suppression.
# Adjust after measuring real bounding boxes on-device.
BALL_FILTER = {
    "enabled": True,
    "min_area": 100,        # px^2, discard tiny noise
    "max_area": 10000,      # px^2, discard large blobs
    "aspect_min": 0.5,      # w/h lower bound
    "aspect_max": 2.0,      # w/h upper bound
}

TRACKING = {
    "smooth_alpha": 0.45,
    "lost_tolerance_frames": 3,
}

SERIAL = {
    "enabled": False,
    "device": "/dev/ttyS4",
    "baudrate": 115200,
    "tx_pin": "A21",
    "rx_pin": "A22",
    "tx_function": "UART4_TX",
    "rx_function": "UART4_RX",
    "print_tx": False,
}

DEBUG = {
    "metrics_interval_ms": 500,
    "draw_all_candidates": True,
}
