import argparse
from pathlib import Path
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from inspecsafe_auto_label.indexing import load_jsonl, write_json, write_jsonl


def bbox_iou_xyxy(box_a: list[float], box_b: list[float]) -> float:
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b

    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)

    inter_w = max(0.0, inter_x2 - inter_x1)
    inter_h = max(0.0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h
    if inter_area <= 0:
        return 0.0

    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter_area
    return inter_area / union if union > 0 else 0.0


def nms(predictions: list[dict[str, Any]], iou_threshold: float) -> list[dict[str, Any]]:
    kept: list[dict[str, Any]] = []
    for pred in sorted(predictions, key=lambda p: float(p.get("score") or 0.0), reverse=True):
        if all(bbox_iou_xyxy(pred["bbox"], selected["bbox"]) < iou_threshold for selected in kept):
            kept.append(pred)
    return kept


def suppress_cross_label_duplicates(
    predictions: list[dict[str, Any]],
    first_label: str,
    second_label: str,
    iou_threshold: float,
    prefer_label: str,
) -> list[dict[str, Any]]:
    first = [p for p in predictions if p["label"] == first_label]
    second = [p for p in predictions if p["label"] == second_label]
    removed_ids: set[int] = set()

    for a in first:
        for b in second:
            iou = bbox_iou_xyxy(a["bbox"], b["bbox"])
            if iou < iou_threshold:
                continue

            score_a = float(a.get("score") or 0.0)
            score_b = float(b.get("score") or 0.0)

            if prefer_label == first_label:
                drop = b if score_a >= score_b else a
            elif prefer_label == second_label:
                drop = a if score_b >= score_a else b
            else:
                drop = a if score_a < score_b else b
            removed_ids.add(id(drop))

    return [p for p in predictions if id(p) not in removed_ids]


def refine_image_predictions(
    predictions: list[dict[str, Any]],
    default_min_score: float,
    class_min_score: dict[str, float],
    nms_iou: float,
) -> list[dict[str, Any]]:
    by_label: dict[str, list[dict[str, Any]]] = {}
    for pred in predictions:
        by_label.setdefault(pred["label"], []).append(pred)

    refined: list[dict[str, Any]] = []
    for label, items in by_label.items():
        min_score = class_min_score.get(label, default_min_score)
        filtered = [item for item in items if float(item.get("score") or 0.0) >= min_score]
        refined.extend(nms(filtered, iou_threshold=nms_iou))

    refined = suppress_cross_label_duplicates(
        predictions=refined,
        first_label="Pipeline",
        second_label="Direct-Blow Pipe",
        iou_threshold=0.8,
        prefer_label="Pipeline",
    )
    refined = suppress_cross_label_duplicates(
        predictions=refined,
        first_label="Sight Hole Cover",
        second_label="Pressure Gauge",
        iou_threshold=0.8,
        prefer_label="Sight Hole Cover",
    )

    refined.sort(key=lambda p: float(p.get("score") or 0.0), reverse=True)
    return refined


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply moderate refinement v2 to prediction JSONL.")
    parser.add_argument("--input", required=True, help="Input predictions.jsonl path.")
    parser.add_argument("--output", required=True, help="Output refined predictions.jsonl path.")
    parser.add_argument("--summary-output", default=None, help="Optional summary json output path.")
    parser.add_argument("--default-min-score", type=float, default=0.35)
    parser.add_argument("--nms-iou", type=float, default=0.7)
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    class_min_score = {
        "Open Flame": 0.42,
        "Safety Helmet": 0.38,
        "Electronic Control Cabinet": 0.37,
        "Sight Hole Cover": 0.37,
        "Valve": 0.36,
        "Ladder": 0.37,
        "Pressure Gauge": 0.37,
    }

    records = load_jsonl(args.input)
    refined_records: list[dict[str, Any]] = []

    total_before = 0
    total_after = 0

    for record in records:
        before = len(record.get("predictions", []))
        after_predictions = refine_image_predictions(
            predictions=record.get("predictions", []),
            default_min_score=args.default_min_score,
            class_min_score=class_min_score,
            nms_iou=args.nms_iou,
        )
        after = len(after_predictions)

        next_record = dict(record)
        next_record["predictions"] = after_predictions
        refined_records.append(next_record)

        total_before += before
        total_after += after

    output_path = Path(args.output)
    write_jsonl(refined_records, output_path)

    summary_path = Path(args.summary_output) if args.summary_output else output_path.with_name("refine_v2_summary.json")
    summary = {
        "input_path": str(Path(args.input).resolve()),
        "output_path": str(output_path.resolve()),
        "records": len(refined_records),
        "predictions_before": total_before,
        "predictions_after": total_after,
        "removed": total_before - total_after,
        "default_min_score": args.default_min_score,
        "class_min_score": class_min_score,
        "nms_iou": args.nms_iou,
        "cross_label_rules": [
            "Pipeline vs Direct-Blow Pipe: IoU>=0.8 prefer Pipeline",
            "Sight Hole Cover vs Pressure Gauge: IoU>=0.8 prefer Sight Hole Cover",
        ],
    }
    write_json(summary, summary_path)

    print(f"Wrote refined v2 predictions: {output_path}")
    print(f"Wrote refine v2 summary: {summary_path}")


if __name__ == "__main__":
    main()
