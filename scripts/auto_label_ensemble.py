#!/usr/bin/env python3
"""Generate reviewable YOLO labels by averaging agreeing model detections."""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path, help="Directory containing JPG images")
    parser.add_argument("models", nargs="+", type=Path, help="Two or more YOLO models")
    parser.add_argument("--imgsz", type=int, default=1920)
    parser.add_argument("--conf", type=float, default=0.1)
    parser.add_argument("--min-iou", type=float, default=0.7)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def box_iou(a: np.ndarray, b: np.ndarray) -> float:
    ix1, iy1 = max(a[0], b[0]), max(a[1], b[1])
    ix2, iy2 = min(a[2], b[2]), min(a[3], b[3])
    intersection = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    area_a = max(0.0, a[2] - a[0]) * max(0.0, a[3] - a[1])
    area_b = max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])
    return intersection / max(area_a + area_b - intersection, 1e-9)


def make_contact_sheet(preview_paths: list[Path], destination: Path) -> None:
    cols = 3
    cell_w, cell_h = 640, 520
    rows = (len(preview_paths) + cols - 1) // cols
    sheet = np.full((rows * cell_h, cols * cell_w, 3), 28, dtype=np.uint8)

    for index, path in enumerate(preview_paths):
        image = cv2.imread(str(path))
        height, width = image.shape[:2]
        scale = min((cell_w - 20) / width, (cell_h - 55) / height)
        resized = cv2.resize(
            image,
            (max(1, int(width * scale)), max(1, int(height * scale))),
        )
        resized_h, resized_w = resized.shape[:2]
        x0 = (index % cols) * cell_w + (cell_w - resized_w) // 2
        y0 = (index // cols) * cell_h + 10
        sheet[y0 : y0 + resized_h, x0 : x0 + resized_w] = resized
        cv2.putText(
            sheet,
            path.name,
            (
                (index % cols) * cell_w + 10,
                (index // cols) * cell_h + cell_h - 18,
            ),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.48,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )

    if not cv2.imwrite(str(destination), sheet):
        raise RuntimeError(f"Failed to write {destination}")


def main() -> None:
    args = parse_args()
    source = args.source.resolve()
    image_paths = sorted(source.glob("*.jpg"))
    if not image_paths:
        raise SystemExit(f"No JPG images found in {source}")
    if len(args.models) < 2:
        raise SystemExit("At least two models are required")

    labels_dir = source / "labels"
    # Keep previews outside the source tree because LabelImg scans image
    # directories recursively and would otherwise treat previews as inputs.
    preview_dir = source.parent / f"{source.name}_ai_preview"
    existing_labels = list(labels_dir.glob("*.txt")) if labels_dir.exists() else []
    if existing_labels and not args.overwrite:
        raise SystemExit("Existing labels found; pass --overwrite to replace them")
    labels_dir.mkdir(exist_ok=True)
    preview_dir.mkdir(exist_ok=True)

    model_results = []
    for model_path in args.models:
        model = YOLO(str(model_path.resolve()))
        results = model.predict(
            source=[str(path) for path in image_paths],
            imgsz=args.imgsz,
            conf=args.conf,
            iou=0.5,
            device="cpu",
            verbose=False,
        )
        model_results.append((model_path.stem, results))

    preview_paths = []
    summaries = []
    for index, image_path in enumerate(image_paths):
        selected = []
        for model_name, results in model_results:
            boxes = results[index].boxes
            if boxes is None or len(boxes) == 0:
                raise SystemExit(f"{model_name}: no detection for {image_path.name}")
            selected.append(
                (
                    model_name,
                    boxes.xyxy[0].cpu().numpy().astype(float),
                    float(boxes.conf[0].cpu()),
                )
            )

        reference = selected[0][1]
        pair_ious = [box_iou(reference, item[1]) for item in selected[1:]]
        minimum_iou = min(pair_ious)
        if minimum_iou < args.min_iou:
            raise SystemExit(
                f"Model disagreement for {image_path.name}: IoU={minimum_iou:.3f}"
            )

        box = np.mean([item[1] for item in selected], axis=0)
        image = cv2.imread(str(image_path))
        if image is None:
            raise SystemExit(f"Cannot read {image_path}")
        height, width = image.shape[:2]

        x1, y1, x2, y2 = box
        x1, x2 = np.clip([x1, x2], 0, width)
        y1, y2 = np.clip([y1, y2], 0, height)
        x_center = ((x1 + x2) / 2.0) / width
        y_center = ((y1 + y2) / 2.0) / height
        box_width = (x2 - x1) / width
        box_height = (y2 - y1) / height

        label_path = labels_dir / f"{image_path.stem}.txt"
        label_path.write_text(
            f"0 {x_center:.6f} {y_center:.6f} "
            f"{box_width:.6f} {box_height:.6f}\n",
            encoding="utf-8",
        )

        cv2.rectangle(
            image,
            (int(round(x1)), int(round(y1))),
            (int(round(x2)), int(round(y2))),
            (0, 255, 0),
            5,
        )
        confidence_text = "  ".join(
            f"m{model_index + 1}={item[2]:.2f}"
            for model_index, item in enumerate(selected)
        )
        caption = f"steel_ball  {confidence_text}  IoU={minimum_iou:.2f}"
        text_position = (max(5, int(round(x1))), max(35, int(round(y1)) - 12))
        cv2.putText(
            image,
            caption,
            text_position,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 0, 0),
            5,
            cv2.LINE_AA,
        )
        cv2.putText(
            image,
            caption,
            text_position,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2,
            cv2.LINE_AA,
        )
        preview_path = preview_dir / image_path.name
        if not cv2.imwrite(str(preview_path), image):
            raise RuntimeError(f"Failed to write {preview_path}")
        preview_paths.append(preview_path)
        summaries.append(
            (image_path.name, [item[2] for item in selected], minimum_iou)
        )

    contact_path = preview_dir / "contact.jpg"
    make_contact_sheet(preview_paths, contact_path)

    print(f"images={len(image_paths)} labels={len(list(labels_dir.glob('*.txt')))}")
    print(f"preview={contact_path}")
    for name, confidences, minimum_iou in summaries:
        confidence_text = " ".join(f"{value:.3f}" for value in confidences)
        print(f"{name} conf={confidence_text} iou={minimum_iou:.3f}")


if __name__ == "__main__":
    main()
