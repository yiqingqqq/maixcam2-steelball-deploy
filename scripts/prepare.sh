#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install onnx onnxsim

rm -rf datasets tmp_extract.onnx export.onnx
mkdir -p datasets/train_images
unzip -q calibration/steelball_calibration_75.zip -d datasets/train_images

python -c 'import onnx; onnx.utils.extract_model(
    "model/model.onnx",
    "tmp_extract.onnx",
    ["images"],
    [
        "/model.23/Concat_output_0",
        "/model.23/Concat_1_output_0",
        "/model.23/Concat_2_output_0",
    ],
)'
onnxsim tmp_extract.onnx export.onnx
tar -cf datasets/train.tar -C datasets/train_images .

python -c 'import onnx; m=onnx.load("export.onnx"); onnx.checker.check_model(m); print("input:", [(x.name, [d.dim_value for d in x.type.tensor_type.shape.dim]) for x in m.graph.input]); print("outputs:", [x.name for x in m.graph.output])'
echo "Prepared export.onnx and datasets/train.tar"
