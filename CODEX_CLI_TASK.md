# Codex CLI Handoff: Pulsar2 AX620E Conversion for MaixCAM2

Work in this repository on Ubuntu. The goal is to build, verify, and package the NPU and VNPU `.axmodel` files for MaixCAM2 (AX620E) from the newly fine-tuned YOLO11n model.

## ⚠️ 重要格式约定（与最新 converted 分支保持一致）

> **特别强调**：模型转换后的网络结构、输出节点和配置格式必须与最新 `converted` 分支 (`agent/maixcam2-pulsar2-converted`) **完全严格一致**！

1. **输入节点**: `images: 1x3x480x640` (静态 BCHW)
2. **输出节点 (Mode-2 CHW Decoded Output)**:
   - 节点 0: `/model.23/Sigmoid_output_0` (`1x1x6300`, 置信度)
   - 节点 1: `/model.23/dfl/Reshape_1_output_0` (`1x4x6300`, DFL 框预测)
3. **Pulsar2 Config 转换参数**:
   - `dst_perm: [0, 1, 2]`（保持与 `converted` 分支相同，不可修改为 `[0,2,1]`）
4. **Target Output Artifacts**:
   ```text
   out/steelball_yolo11n_640x480.mud
   out/steelball_yolo11n_640x480_npu.axmodel
   out/steelball_yolo11n_640x480_vnpu.axmodel
   ```

---

## Model Information & Fine-Tuning Performance

- **Task**: YOLO11 Detect, 1 class (`steel_ball`).
- **Fine-Tuning Performance (50 Epochs Complete)**:
  - **Dataset**: 572 total verified samples (including AI annotated & audited short missed frames from `steel_ball` and `steelball_1785491594821_part000` + 4x symmetry augmentations).
  - **Precision**: **97.4%** (vs 26.3% on baseline)
  - **Recall**: **92.8%** (vs 64.2% on baseline)
  - **mAP50**: **98.8%** (vs 35.0% on baseline)
  - **mAP50-95**: **72.7%** (vs 17.8% on baseline)

---

## Ubuntu Pulsar2 Workflow

1. Confirm repository is on branch `handoff` and Docker is installed:
   ```bash
   git checkout handoff
   docker images | grep pulsar2
   ```

2. Run prepare script to extract output nodes and simplify ONNX:
   ```bash
   chmod +x scripts/*.sh
   ./scripts/prepare.sh
   ```
   *Verification assertion*: `prepare.sh` must complete cleanly with:
   - `inputs: {'images': [1, 3, 480, 640]}`
   - `outputs: {'/model.23/Sigmoid_output_0': [1, 1, 6300], '/model.23/dfl/Reshape_1_output_0': [1, 4, 6300]}`

3. Run Pulsar2 conversion for both NPU and VNPU targets:
   ```bash
   PULSAR2_IMAGE=<pulsar2-image-tag> ./scripts/convert.sh
   ```

4. Verify Pulsar2 compiler logs:
   - Cosine similarity must be **> 0.99** for both NPU2 and NPU1.
   - Confirm generated `.axmodel` files exist in `out/`.

5. Commit updated models and push to remote `handoff` or `converted` branch.
