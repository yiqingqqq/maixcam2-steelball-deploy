#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE="${PULSAR2_IMAGE:-pulsar2:6.0}"
cd "$ROOT"

test -f export.onnx
test -f datasets/train.tar
docker image inspect "$IMAGE" >/dev/null

# Pulsar2 writes its build directories as root inside the container. Clean them
# in the same environment so this script remains repeatable for an unprivileged
# host user.
docker run --rm -v "$ROOT:/data" -w /data "$IMAGE" \
  -c 'rm -rf ./tmp_npu ./tmp_vnpu'
mkdir -p out

docker run --rm --net host -v "$ROOT:/data" -w /data "$IMAGE" \
  pulsar2 build --target_hardware AX620E --input ./export.onnx \
  --output_dir ./tmp_npu --config ./config/yolo11n.npu.json
cp tmp_npu/compiled.axmodel out/steelball_yolo11n_640x480_npu.axmodel

docker run --rm --net host -v "$ROOT:/data" -w /data "$IMAGE" \
  pulsar2 build --target_hardware AX620E --input ./export.onnx \
  --output_dir ./tmp_vnpu --config ./config/yolo11n.vnpu.json
cp tmp_vnpu/compiled.axmodel out/steelball_yolo11n_640x480_vnpu.axmodel

ls -lh out
echo "Conversion finished. Keep all three files in out/ together."
