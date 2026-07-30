"""Export YOLO11n .pt to static ONNX (640x480)."""
import os
import shutil
from ultralytics import YOLO

os.chdir('/home/yiqing/Workspace/Computer-Vision/YOLO/Diansai/maixcam2-steelball-deploy')

model = YOLO('model/steelball_yolo11n_640x480.pt')
model.export(format='onnx', imgsz=[480, 640], batch=1, device='cpu',
             simplify=False, opset=12)

# The export writes to the same directory as the .pt with auto-generated name
exported = 'model/steelball_yolo11n_640x480.onnx'
if os.path.exists(exported):
    shutil.move(exported, 'model/steelball_yolo11n_export.onnx')
    print("Exported to model/steelball_yolo11n_export.onnx")
else:
    # Check for other possible names
    for f in os.listdir('model'):
        if f.endswith('.onnx') and f != 'model.onnx':
            print(f"Found: model/{f}")
