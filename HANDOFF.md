# YOLO11 模型微调与 Pulsar2 转换 Handoff 文档

## 1. 任务完成情况

已完成对 MaixCAM2 小球识别模型 YOLO11n 的微调与评估：
- **微调数据集**：结合最近新增抽取且经人工审核的漏检帧 (`steel_ball`, `steelball_1785491594821_part000`) 以及 4x 对称增强，扩充至 **572 张全量验证样本**。
- **微调轮次**：完成 50 Epochs 训练（基于 Apple M5 MPS GPU）。
- **实测性能**：
  - **Precision (精准率)**：**97.4%** (Baseline 26.3%)
  - **Recall (召回率)**：**92.8%** (Baseline 64.2%)
  - **mAP50**：**98.8%** (Baseline 35.0%)
  - **mAP50-95**：**72.7%** (Baseline 17.8%)

---

## 2. 转换格式约定（⚠️ 与最新 `converted` 分支严格一致）

在 Ubuntu 端使用 Pulsar2 编译时，**模型的导出了与描述文件必须与 `agent/maixcam2-pulsar2-converted` 分支完全一致**：

1. **输入 Shape**: `images: [1, 3, 480, 640]`
2. **输出节点 (Mode-2 CHW)**:
   - `/model.23/Sigmoid_output_0` `[1, 1, 6300]` (Class Conf)
   - `/model.23/dfl/Reshape_1_output_0` `[1, 4, 6300]` (DFL Coordinates)
3. **Pulsar2 Config**:
   - `dst_perm: [0, 1, 2]`
4. **输出产物目标文件**:
   - `out/steelball_yolo11n_640x480.mud`
   - `out/steelball_yolo11n_640x480_npu.axmodel`
   - `out/steelball_yolo11n_640x480_vnpu.axmodel`

---

## 3. Ubuntu 端转换操作指南

在 Ubuntu 环境中拉取分支并执行模型转换：

```bash
# 1. 切换到 handoff 分支并拉取最新更改
git checkout handoff
git pull origin handoff

# 2. 检查 Docker 及 Pulsar2 镜像
docker images | grep pulsar2

# 3. 运行 ONNX 裁剪与节点校验脚本
chmod +x scripts/*.sh
./scripts/prepare.sh

# 4. 执行 Pulsar2 NPU/VNPU axmodel 模型转换
PULSAR2_IMAGE=pulsar2:6.0 ./scripts/convert.sh

# 5. 校验转换产物
ls -lh out/
```
