#!/usr/bin/env python3
"""Convert LabelMe JSON annotations in dataset/raw_robot_to_annotate/images to YOLO txt format."""

import json, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "dataset" / "raw_robot_to_annotate"
RAW_IMG_DIR = RAW_DIR / "images"
RAW_LBL_DIR = RAW_DIR / "labels"

RAW_LBL_DIR.mkdir(parents=True, exist_ok=True)

def convert():
    json_files = sorted(RAW_IMG_DIR.glob("*.json"))
    if not json_files:
        print("No LabelMe JSON files found in dataset/raw_robot_to_annotate/images")
        return

    converted_count = 0
    for json_p in json_files:
        with open(json_p, encoding="utf-8") as f:
            data = json.load(f)

        img_w = data.get("imageWidth")
        img_h = data.get("imageHeight")
        
        txt_lines = []
        for shape in data.get("shapes", []):
            label = shape.get("label", "steel_ball")
            points = shape.get("points", [])
            if len(points) >= 2:
                xs = [p[0] for p in points]
                ys = [p[1] for p in points]
                x1, x2 = min(xs), max(xs)
                y1, y2 = min(ys), max(ys)
                
                xc = ((x1 + x2) / 2.0) / img_w
                yc = ((y1 + y2) / 2.0) / img_h
                bw = (x2 - x1) / img_w
                bh = (y2 - y1) / img_h
                
                txt_lines.append(f"0 {xc:.6f} {yc:.6f} {bw:.6f} {bh:.6f}")

        txt_p = RAW_LBL_DIR / f"{json_p.stem}.txt"
        txt_p.write_text("\n".join(txt_lines) + "\n" if txt_lines else "", encoding="utf-8")
        converted_count += 1
        print(f"Converted {json_p.name} -> {txt_p.name} ({len(txt_lines)} boxes)")

    print(f"Done! Converted {converted_count} LabelMe JSON files.")

if __name__ == "__main__":
    convert()
