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
        "/model.23/Sigmoid_output_0",
        "/model.23/dfl/Reshape_1_output_0",
    ],
)'
onnxsim tmp_extract.onnx export.onnx
tar -cf datasets/train.tar -C datasets/train_images .

python - <<'PY'
import onnx

model = onnx.shape_inference.infer_shapes(onnx.load("export.onnx"))
onnx.checker.check_model(model)

def shape(value):
    return [dim.dim_value for dim in value.type.tensor_type.shape.dim]

inputs = {value.name: shape(value) for value in model.graph.input}
outputs = {value.name: shape(value) for value in model.graph.output}
expected_inputs = {"images": [1, 3, 480, 640]}
expected_outputs = {
    "/model.23/Sigmoid_output_0": [1, 1, 6300],
    "/model.23/dfl/Reshape_1_output_0": [1, 4, 6300],
}

print("inputs:", inputs)
print("outputs:", outputs)
if inputs != expected_inputs:
    raise SystemExit(f"unexpected inputs: {inputs}")
if outputs != expected_outputs:
    raise SystemExit(f"unexpected outputs: {outputs}")
PY
echo "Prepared export.onnx and datasets/train.tar"
