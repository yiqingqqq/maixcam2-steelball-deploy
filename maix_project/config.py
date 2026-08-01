"""Runtime parameters for the MaixCAM2 steel-ball YOLO detector."""

# Always use MaixVision "Run Project".
# record_capture: YOLO detection + clean recording + per-frame CSV.
# video_recorder: clean recording with live preview only.
# pixel_debug: no calibration, prints pixel-grid/s for teammate debugging.
# calibration: create metric track calibration. tracking: metric measurement.
# serial_tracking: metric measurement + fixed-rate UART transmission.
RUN_MODE = "serial_tracking"  # 当前运行模式

CAMERA = {
    # 快门曝光时间(微秒 us):
    "shutter_us": 10000,
    "anti_flicker_hz": 50,  # 抗频闪频率：50 / 60
}

PIPE_ROI = {
    "enabled": True,  # 是否启用管道ROI
    "color_mode": "white",  # 管道颜色：auto/green/white/off
    "x": 0,  # ROI左上角横坐标
    "y": 0,  # ROI左上角纵坐标
    "w": 640,  # ROI宽度
    "h": 480,  # ROI高度
    "center_margin_px": 5,  # 球心距离ROI边界余量
}

MODEL = {
    "path": "/root/maix_project/models/steelball_yolo11n_640x480/steelball_yolo11n_640x480.mud",  # 项目内模型路径
    "conf_threshold": 0.03,  # 置信度阈值
    "iou_threshold": 0.50,  # NMS交并比阈值
    "dual_buffer": False,  # 是否启用双缓冲
}

TRACKING = {
    # Candidate geometry/association gates (640x480 model coordinates).
    "min_box_px": 0,  # 最小框边长
    # Parameters from converted commit 4ce3420: filter implausible ball boxes
    # before continuity association, then retain the highest-confidence box.
    "min_box_area_px": 0,  # 最小框面积(px²)
    "max_box_area_px": 8000,  # 最大框面积(px²)
    "aspect_min": 0.5,  # 最小宽高比
    "aspect_max": 2.0,  # 最大宽高比
    "top1_per_frame": True,  # 几何合格候选仅保留最高置信度者
    "max_box_width_ratio": 0.50,  # 最大框宽占比
    "max_box_height_ratio": 0.60,  # 最大框高占比
    "max_box_area_ratio": 0.20,  # 最大框面积占比
    "max_area_change_ratio": 5.0,  # 面积变化上限
    "max_lateral_px": 75.0,  # 管道横向偏差上限
    "association_base_gate_px": 45.0,  # 基础关联距离
    # Wider gate accommodates a fast ball; after association reset the gate
    # is bypassed because selector.last is cleared.
    "association_max_gate_px": 240.0,  # 关联距离上限
    "association_reset_ms": 200,  # 多久后清除旧目标
    "confidence_weight": 0.37,  # 置信度权重
    "distance_weight": 0.50,  # 距离权重
    "area_weight": 0.13,  # 面积权重
    # Time-domain motion limits.
    # Responsiveness/continuity trade-off: normal trusted measurements are used
    # directly. Prediction only bridges roughly 1-2 inference periods.
    "prediction_enabled": True,  # 是否启用短时预测
    "prediction_window_ms": 70,  # 预测最长时间
    "normal_max_dt_ms": 120,  # 正常时间间隔上限
    "max_speed_mm_s": 7000.0,  # 速度上限
    "max_accel_mm_s2": 40000.0,  # 加速度上限
    # Normal-frame jump rejection remains bounded; reacquisition after loss
    # is intentionally much wider so a fast re-entry can be accepted.
    "max_step_mm": 260.0,  # 正常单帧位移上限
    "reacquire_gate_mm": 1000.0,  # 重捕获位移门限
    "position_correction": 1.0,  # 位置修正系数
    "velocity_correction": 0.75,  # 速度修正系数
    "track_min_margin_mm": 20.0,  # 轨道下边界余量
    "track_max_margin_mm": 20.0,  # 轨道上边界余量
}

# Straight-track calibration. Run calibration.py once on the device to generate it.
CALIBRATION = {
    "path": "/root/steelball_data/calibration.json",  # 标定文件路径
    # Known distances along the pipe, in capture order. Use at least two points;
    # 4+ evenly distributed points better compensate perspective.
    "track_distances_mm": [0.0, 100.0, 200.0, 300.0],  # 标定点距离
    "samples_per_point": 20,  # 每点采样数
    "placement_countdown_seconds": 5,  # 放球倒计时
    "conf_threshold": 0.20,  # 标定检测阈值
    "sample_timeout_seconds": 20,  # 单点超时时间
}

RECORDING = {
    "enabled": True ,  # 是否开启录像支持
    "directory": "/root/recordings",  # 录像保存目录
    "framerate": 30,  # 录像帧率
    "bitrate": 3000000,  # 录像码率
    "segment_seconds": 300,  # 分段时长
}

VIDEO_CAPTURE = {
    "directory": "/root/recordings/steelball_capture",  # 采集目录
    "framerate": 30,  # 采集帧率
    "bitrate": 5000000,  # 采集码率
    "segment_seconds": 300,  # 分段时长
    "width": 640,  # 采集宽度
    "height": 480,  # 采集高度
}

RECORD_CAPTURE = {
    "directory": "/root/recordings/steelball_capture",  # 录像目录
    "framerate": 30,  # 录像帧率
    "bitrate": 5000000,  # 录像码率
    "segment_seconds": 300,  # 分段时长
    "conf_threshold": 0.20,  # 检测阈值
}

SERIAL = {
    # Temporary uncalibrated mode: use image x directly (1 pixel = 1 unit).
    "use_calibration": False,  # 是否使用标定
    "enabled": True,  # 兼容旧开关
    "receive_enabled": True,  # 是否接收串口
    "wait_command": False,  # 开机即自动开始识别与录像 (免指令保底模式)
    "device": "/dev/ttyS4",  # 串口设备
    "baudrate": 115200,  # 波特率
    "start_cmd": "BEGIN",  # 下位机启动命令
    "stop_cmd": "END",    # 下位机停止命令
    "tx_pin": "A21",  # 发送引脚
    "rx_pin": "A22",  # 接收引脚
    "tx_function": "UART4_TX",  # 发送复用功能
    "rx_function": "UART4_RX",  # 接收复用功能
    "print_tx": True,  # 是否打印发送帧
    "output_period_ms": 33,  # 输出周期
    "output_hz": 30,  # 输出频率
    "stale_timeout_ms": 450,  # 数据过期时间
    # In uncalibrated mode this is the image x origin; right is positive.
    "target_center_mm": 320.0,  # 位置零点横坐标
    # EMA for reported velocity: 0.0=very smooth, 1.0=no filtering.
    "velocity_ema_alpha": 0.35,  # 速度EMA系数
    # False preserves the existing $position,speed protocol. True appends status.
    "include_status": False,  # 是否附加状态
}

DEBUG = {
    "display_period_ms": 0,  # 预览推流周期 (66ms ≈ 15 FPS)，设为 0 表示全速推流
    "metrics_interval_ms": 1000,  # 指标打印周期
    "motion_print_enabled": True,  # 是否打印运动数据
    "motion_print_interval_ms": 100,  # 运动数据周期
    "draw_all_candidates": True,  # 是否绘制候选框
    "stats_window_frames": 300,  # 统计窗口帧数
}

PIXEL_DEBUG = {
    # Low diagnostic threshold for lighting-shift tests. Geometry and
    # continuity filtering still reject implausible candidates downstream.
    "conf_threshold": 0.05,  # 调试检测阈值
    "output_hz": 30,  # 调试输出频率
    "stale_timeout_ms": 150,  # 调试数据过期时间
    "max_dt_ms": 250,  # 最大时间间隔
    "max_speed_px_s": 10000.0,  # 像素速度上限
}
