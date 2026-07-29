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
- Verified internal outputs:
  - `/model.23/Concat_output_0`
  - `/model.23/Concat_1_output_0`
  - `/model.23/Concat_2_output_0`
- Target hardware: `AX620E` / MaixCAM2.
- Calibration archive: 75 images; conversion config intentionally uses 64.
- PT and full ONNX were already compared on a 900-frame real MaixCAM2 video and produced identical detections.

## Required workflow

1. Read `README.md` and inspect the repository without replacing the verified node names.
2. Confirm Docker works and locate the installed Pulsar2 image with `docker images | grep pulsar2`.
3. If no Pulsar2 image exists, help the user download the current official image and load it with `docker load`. Do not invent an image URL.
4. Run `chmod +x scripts/*.sh` and `./scripts/prepare.sh`.
5. Confirm `export.onnx` has the three outputs above and static input `1x3x480x640`.
6. Run `PULSAR2_IMAGE=<actual-image-tag> ./scripts/convert.sh`.
7. Review both Pulsar2 logs. Require successful compiler checks and cosine similarity at least 0.9.
8. Verify both `.axmodel` files are nonempty and that the `.mud` references their exact basenames.
9. Commit the generated `.axmodel` files to the current branch and push them so the Windows machine can download the completed `out/` directory.

Do not train the model, change input resolution, change label order, or substitute MaixCAM `.cvimodel` conversion.
