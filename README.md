# Steel-ball YOLO11 deployment for MaixCAM2

This repository transfers a verified YOLO11n steel-ball detector from Windows to an Ubuntu machine with Docker/Pulsar2. It contains the fixed-size ONNX model, INT8 calibration images, verified conversion configs, MaixPy runtime project, and a Codex CLI handoff.

## Repository contents

```text
model/model.onnx                         fixed 1x3x480x640 ONNX
model/steelball_yolo11n_640x480.pt       original deployment checkpoint
calibration/steelball_calibration_75.zip 75 calibration images
config/                                  NPU2 and NPU1 Pulsar2 configs
scripts/prepare.sh                       crop ONNX and prepare calibration tar
scripts/convert.sh                       build NPU and VNPU AXModel files
out/steelball_yolo11n_640x480.mud         MaixPy model descriptor
maix_project/                            MaixVision project
CODEX_CLI_TASK.md                        task prompt for Codex CLI on Ubuntu
```

## Ubuntu quick start

```bash
git clone <repository-url>
cd maixcam2-steelball-deploy
chmod +x scripts/*.sh
./scripts/prepare.sh
docker images | grep pulsar2
PULSAR2_IMAGE=pulsar2:6.0 ./scripts/convert.sh
```

Use the actual image tag printed by `docker images` if it is not `pulsar2:6.0`. See `CODEX_CLI_TASK.md` for validation and handoff requirements.

## Deploy to MaixCAM2

Upload all three files from `out/` into the same device directory:

```text
/root/models/steelball_yolo11n_640x480/
```

Then open `maix_project/` in MaixVision and run its root `main.py`.

Official conversion reference: https://wiki.sipeed.com/maixpy/doc/zh/ai_model_converter/maixcam2.html
