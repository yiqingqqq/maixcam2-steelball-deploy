#!/usr/bin/env python3
"""Merge manual annotations from dataset/raw_robot_to_annotate, augment, and trigger fine-tuning."""

import cv2, os, glob, pathlib, shutil, json
from ultralytics import YOLO

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "dataset" / "raw_robot_to_annotate"
RAW_IMG_DIR = RAW_DIR / "images"
RAW_LBL_DIR = RAW_DIR / "labels"

IMG_ALL_DIR = ROOT / "dataset" / "images" / "all"
LBL_ALL_DIR = ROOT / "dataset" / "labels" / "all"

TRAIN_TXT = ROOT / "dataset" / "train.txt"
VAL_TXT = ROOT / "dataset" / "val.txt"

def main():
    raw_images = sorted(RAW_IMG_DIR.glob("*.jpg"))
    if not raw_images:
        print("No images found in dataset/raw_robot_to_annotate/images")
        return

    added_train = []
    added_val = []

    for idx, img_p in enumerate(raw_images, start=1):
        lbl_p = RAW_LBL_DIR / f"{img_p.stem}.txt"
        if not lbl_p.exists():
            print(f"Warning: Label {lbl_p.name} not found, treating as empty/background.")
            label_content = ""
        else:
            label_content = lbl_p.read_text(encoding="utf-8").strip()

        img = cv2.imread(str(img_p))
        base_name = f"manual_robot_{idx:02d}"

        # 1. Base image
        dst_img = IMG_ALL_DIR / f"{base_name}_orig.jpg"
        dst_lbl = LBL_ALL_DIR / f"{base_name}_orig.txt"
        cv2.imwrite(str(dst_img), img)
        dst_lbl.write_text(label_content + "\n" if label_content else "", encoding="utf-8")

        if idx % 3 == 0:
            added_val.append(str(dst_img))
        else:
            added_train.append(str(dst_img))

        # 2. Augmentation - Flip H
        img_fh = cv2.flip(img, 1)
        dst_fh_img = IMG_ALL_DIR / f"{base_name}_flip_h.jpg"
        dst_fh_lbl = LBL_ALL_DIR / f"{base_name}_flip_h.txt"
        cv2.imwrite(str(dst_fh_img), img_fh)
        
        # Parse & flip H boxes
        fh_lines = []
        if label_content:
            for line in label_content.splitlines():
                parts = line.strip().split()
                if len(parts) == 5:
                    cls_id, x, y, w, h = parts
                    x_flipped = 1.0 - float(x)
                    fh_lines.append(f"{cls_id} {x_flipped:.6f} {y} {w} {h}")
        dst_fh_lbl.write_text("\n".join(fh_lines) + "\n" if fh_lines else "", encoding="utf-8")
        added_train.append(str(dst_fh_img))

        # 3. Augmentation - Brightness
        img_b = cv2.convertScaleAbs(img, alpha=1.15, beta=15)
        dst_b_img = IMG_ALL_DIR / f"{base_name}_bright.jpg"
        dst_b_lbl = LBL_ALL_DIR / f"{base_name}_bright.txt"
        cv2.imwrite(str(dst_b_img), img_b)
        dst_b_lbl.write_text(label_content + "\n" if label_content else "", encoding="utf-8")
        added_train.append(str(dst_b_img))

    # Update train.txt and val.txt
    with open(TRAIN_TXT) as f:
        train_lines = [l.strip() for l in f if l.strip() and "manual_robot_" not in l]
    with open(VAL_TXT) as f:
        val_lines = [l.strip() for l in f if l.strip() and "manual_robot_" not in l]

    train_lines.extend(added_train)
    val_lines.extend(added_val)

    with open(TRAIN_TXT, "w") as f:
        f.write("\n".join(train_lines) + "\n")
    with open(VAL_TXT, "w") as f:
        f.write("\n".join(val_lines) + "\n")

    # Clean cache
    for cache_f in (ROOT / "dataset").rglob("*.cache"):
        cache_f.unlink(missing_ok=True)

    print(f"Successfully merged {len(raw_images)} manual images into dataset.")
    print(f"Train samples: {len(train_lines)}, Val samples: {len(val_lines)}")

if __name__ == "__main__":
    main()
