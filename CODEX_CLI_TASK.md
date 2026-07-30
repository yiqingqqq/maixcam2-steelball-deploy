# Codex CLI handoff: convert YOLO11 for MaixCAM2

Work in this repository on Ubuntu. The goal is to produce and verify these files:

```text
out/steelball_yolo11n_640x480.mud
out/steelball_yolo11n_640x480_npu.axmodel
out/steelball_yolo11n_640x480_vnpu.axmodel
```

## Known model facts

- Task: YOLO11 Detect, one class: `steel_ball`.
- Static input: `images`, shape `1x3x480x640` (height x width).
- MaixPy `nn.YOLO11` mode-2 outputs (CHW):
  - `/model.23/Sigmoid_output_0` (`1x1x6300`, class confidence)
  - `/model.23/dfl/Reshape_1_output_0` (`1x4x6300`, DFL left/top/right/bottom distances before anchor/stride decoding)
- Target hardware: `AX620E` / MaixCAM2.
- Calibration archive: 75 images; conversion config intentionally uses 64.
- PT and full ONNX were already compared on a 900-frame real MaixCAM2 video and produced identical detections.

## Root cause and forbidden outputs

The previous AXModels loaded successfully but produced a full-frame green box centered near `(320,240)`. The second output was `/model.23/Mul_2_output_0`, which already contains decoded boxes multiplied by stride. MaixPy mode 2 interpreted those values as DFL distances and decoded them a second time.

- Do not use `/model.23/Mul_2_output_0`; matching shape `1x4x6300` is not sufficient because its coordinate semantics are wrong.
- Do not restore the three `/model.23/Concat*_output_0` nodes; those produce three rank-3 outputs and fail `nn.YOLO11` loading with `output node shape error`.
- Do not change the two verified output node names above unless MaixPy runtime source and an on-device test prove a different contract.

## Required workflow

1. Read `README.md` and inspect the repository without replacing the verified node names.
2. Confirm Docker works and locate the installed Pulsar2 image with `docker images | grep pulsar2`.
3. If no Pulsar2 image exists, help the user download the current official image and load it with `docker load`. Do not invent an image URL.
4. Run `chmod +x scripts/*.sh` and `./scripts/prepare.sh`.
5. Require `prepare.sh` to finish its assertions: the input must be exactly `images: 1x3x480x640`, and the only outputs must be exactly `Sigmoid: 1x1x6300` and `dfl/Reshape_1: 1x4x6300` in CHW layout.
6. Run `PULSAR2_IMAGE=<actual-image-tag> ./scripts/convert.sh`.
7. Review both Pulsar2 logs. Require successful compiler checks, no output-node substitution, and cosine similarity at least 0.9 for NPU2 and NPU1.
8. Inspect both generated AXModels. Each must expose exactly two outputs with shapes `[1,1,6300]` and `[1,4,6300]`; record the output names, shapes, file sizes, and SHA-256 hashes in the handoff response.
9. Verify the `.mud` references the exact basenames of both generated AXModels.
10. Test on a real MaixCAM2 with the repository's `maix_project/main.py`. Merely loading the model is not acceptance. Require all of the following:
    - `nn.YOLO11` initializes and prints `model ready` without `output node shape error`.
    - With a steel ball visible, the green box tightly surrounds the ball instead of covering the full `640x480` frame; the red center point lies on or near the ball.
    - Terminal metrics report a plausible localized box (`w < 640` and `h < 480`), not `640x480` or a frame-clipped equivalent.
    - Moving the ball makes the box and center follow it.
    - With the ball removed for at least 10 seconds, there is no persistent full-frame detection and the program reports `target=NONE` after the configured lost-frame tolerance.
    - Capture the terminal output and one device/MaixVision screenshot showing the localized box as acceptance evidence.
11. Commit the regenerated `.axmodel` files together with any required script/config corrections and push them to the current branch. Report the exact branch name and commit hash.

Do not train the model, change input resolution, change label order, or substitute MaixCAM `.cvimodel` conversion.
