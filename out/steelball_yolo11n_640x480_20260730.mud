[basic]
type = axmodel
model_npu = steelball_yolo11n_640x480_20260730_npu.axmodel
model_vnpu = steelball_yolo11n_640x480_20260730_vnpu.axmodel

[extra]
model_type = yolo11
type = detector
input_type = rgb
labels = steel_ball

input_cache = true
output_cache = true
input_cache_flush = false
output_cache_inval = true

mean = 0,0,0
scale = 0.00392156862745098,0.00392156862745098,0.00392156862745098
