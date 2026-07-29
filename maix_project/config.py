"""Runtime parameters for the MaixCAM2 steel-ball YOLO detector."""

MODEL = {
    "path": "/root/models/steelball_yolo11n_640x480/steelball_yolo11n_640x480.mud",
    "conf_threshold": 0.45,
    "iou_threshold": 0.45,
    "dual_buffer": False,
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
