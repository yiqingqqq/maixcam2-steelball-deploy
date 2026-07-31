# Codex CLI Handoff: Pulsar2 AX620E Conversion for MaixCAM2

Work in this repository on Ubuntu. The goal is to build, verify, and package the NPU and VNPU `.axmodel` files for MaixCAM2 (AX620E) from the newly fine-tuned YOLO11n model.

## Target Output Artifacts

```text
out/steelball_yolo11n_640x480.mud
out/steelball_yolo11n_640x480_npu.axmodel
out/steelball_yolo11n_640x480_vnpu.axmodel
```

## Model Information & Fine-Tuning Status

- **Task**: YOLO11 Detect, 1 class (`steel_ball`).
- **Fine-Tuning Update**: Model fine-tuned on MacBook with **50 updated real-world robot chassis images & offline augmentations** (flips H/V, brightness variations).
  - Validation Recall: **100% (1.0000)** vs 90.9% on baseline.
  - Validation mAP50: **0.9950** vs 0.9210 on baseline.
- **Static Input**: `images`, shape `1x3x480x640` (height x width).
- **MaixPy `nn.YOLO11` Mode-2 Output Nodes (CHW)**:
  - `/model.23/Sigmoid_output_0` (`1x1x6300`, class confidence)
  - `/model.23/dfl/Reshape_1_output_0` (`1x4x6300`, DFL distances before anchor/stride decoding)
- **Target Hardware**: AX620E / MaixCAM2.

## Forbidden Outputs & Graph Contract

- **DO NOT** use `/model.23/Mul_2_output_0`. Matching shape `1x4x6300` is insufficient because its coordinate values are pre-multiplied by stride, causing MaixPy mode 2 to double-decode boxes into a persistent full-frame green box `(320,240,640,480)`.
- **DO NOT** restore three `/model.23/Concat*_output_0` rank-3 output nodes.
- **DO NOT** alter the input resolution (`1x3x480x640`) or output node names.

## Ubuntu Pulsar2 Workflow & Assertions

1. Inspect repository and confirm Docker is installed:
   ```bash
   docker images | grep pulsar2
   ```
2. Prepare calibration archive and verify extracted ONNX shape assertions:
   ```bash
   chmod +x scripts/*.sh
   ./scripts/prepare.sh
   ```
   *Requirement*: `prepare.sh` must succeed with input `images: 1x3x480x640`, output 0 `Sigmoid: 1x1x6300`, output 1 `dfl/Reshape_1: 1x4x6300`.

3. Run Pulsar2 conversion for both NPU and VNPU targets:
   ```bash
   PULSAR2_IMAGE=<pulsar2-image-tag> ./scripts/convert.sh
   ```
4. Verify Pulsar2 compiler logs:
   - Cosine similarity must be **> 0.99** for both NPU2 and NPU1.
   - Confirm no output node substitution occurred.
5. Record output `.axmodel` file sizes, output node shapes, and SHA-256 hashes in your response.
6. Verify `out/steelball_yolo11n_640x480.mud` points to the exact generated `.axmodel` basenames.
7. Device / MaixVision On-Device Acceptance Criteria (`maix_project/main.py`):
   - `nn.YOLO11` initializes cleanly without `output node shape error`.
   - With steel ball in view: green box tightly surrounds the ball (`w < 640`, `h < 480`), center point lies on the ball.
   - Tracking follows the ball when moved.
   - When ball is removed for > 10s: no persistent full-frame detection (`target=NONE`).
8. Commit updated `.axmodel` and `.mud` files and push to remote `handoff` branch.
