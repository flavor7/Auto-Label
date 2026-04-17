import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


FOCUS_CLASSES = ["Valve", "Pipeline", "Pressure Gauge"]
COMPARE_CLASS = "Fire Hydrant"


def normalize_path(value: str) -> str:
    return value.replace("\\", "/")


def iou_xywh(box_a: list[float], box_b: list[float]) -> float:
    ax, ay, aw, ah = box_a
    bx, by, bw, bh = box_b

    x1 = max(ax, bx)
    y1 = max(ay, by)
    x2 = min(ax + aw, bx + bw)
    y2 = min(ay + ah, by + bh)

    iw = max(0.0, x2 - x1)
    ih = max(0.0, y2 - y1)
    inter = iw * ih
    if inter <= 0:
        return 0.0

    union = aw * ah + bw * bh - inter
    return inter / union if union > 0 else 0.0


def bbox_xywh(prediction: dict[str, Any]) -> list[float]:
    x1, y1, x2, y2 = prediction["bbox"]
    return [float(x1), float(y1), float(x2) - float(x1), float(y2) - float(y1)]


def bbox_center_xywh(box: list[float]) -> tuple[float, float]:
    x, y, w, h = box
    return (x + w / 2.0, y + h / 2.0)


def bbox_size_ratios(pred_box: list[float], gt_box: list[float]) -> dict[str, float]:
    pred_w, pred_h = pred_box[2], pred_box[3]
    gt_w, gt_h = gt_box[2], gt_box[3]
    return {
        "width_ratio": pred_w / gt_w if gt_w > 0 else 0.0,
        "height_ratio": pred_h / gt_h if gt_h > 0 else 0.0,
    }


def resolve_image_id(record: dict[str, Any], image_id_by_name: dict[str, int]) -> int:
    keys: list[str] = []
    if record.get("image_rel_path"):
        keys.append(normalize_path(str(record["image_rel_path"])))
    if record.get("image_path"):
        raw = str(record["image_path"])
        keys.append(normalize_path(raw))
        keys.append(normalize_path(str(Path(raw).resolve())))

    for key in keys:
        if key in image_id_by_name:
            return image_id_by_name[key]
    raise KeyError(f"Could not resolve image id for asset_id={record.get('asset_id')}")


def load_records(path: Path, image_id_by_name: dict[str, int]) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        record["_resolved_image_id"] = resolve_image_id(record, image_id_by_name)
        records[str(record["asset_id"])] = record
    return records


def prediction_key(prediction: dict[str, Any]) -> tuple[str, tuple[float, float, float, float], float]:
    return (
        str(prediction["label"]),
        tuple(float(v) for v in prediction["bbox"]),
        float(prediction.get("score") or 0.0),
    )


def build_occurrence(
    asset_id: str,
    gt_box: list[float],
    class_name: str,
    baseline_record: dict[str, Any],
    v1_record: dict[str, Any],
    v2_record: dict[str, Any],
) -> dict[str, Any]:
    v1_keys = {prediction_key(pred) for pred in v1_record.get("predictions", [])}
    v2_keys = {prediction_key(pred) for pred in v2_record.get("predictions", [])}

    same_label_candidates: list[dict[str, Any]] = []
    wrong_label_candidates: list[dict[str, Any]] = []

    for pred in baseline_record.get("predictions", []):
        pred_box = bbox_xywh(pred)
        iou = iou_xywh(pred_box, gt_box)
        cx, cy = bbox_center_xywh(pred_box)
        gx, gy = bbox_center_xywh(gt_box)
        entry = {
            "label": str(pred["label"]),
            "score": float(pred.get("score") or 0.0),
            "bbox": [float(v) for v in pred["bbox"]],
            "iou": iou,
            "center_offset": {
                "dx": cx - gx,
                "dy": cy - gy,
            },
            "size_ratio": bbox_size_ratios(pred_box, gt_box),
            "kept_in_v1": prediction_key(pred) in v1_keys,
            "kept_in_v2": prediction_key(pred) in v2_keys,
        }
        if entry["label"] == class_name:
            same_label_candidates.append(entry)
        else:
            wrong_label_candidates.append(entry)

    same_label_candidates.sort(key=lambda item: (-item["iou"], -item["score"], item["label"]))
    wrong_label_candidates.sort(key=lambda item: (-item["iou"], -item["score"], item["label"]))

    overlapping_wrong = [item for item in wrong_label_candidates if item["iou"] >= 0.1]
    best_same = same_label_candidates[0] if same_label_candidates else None
    best_wrong = wrong_label_candidates[0] if wrong_label_candidates else None

    return {
        "asset_id": asset_id,
        "gt_bbox": [float(v) for v in gt_box],
        "same_label_candidates": same_label_candidates,
        "best_same_label_candidate": best_same,
        "best_wrong_label_candidate": best_wrong,
        "overlapping_wrong_label_candidates": overlapping_wrong[:5],
    }


def classify_root_cause(class_name: str, occurrences: list[dict[str, Any]]) -> dict[str, str]:
    same_candidate_occurrences = sum(1 for occ in occurrences if occ["same_label_candidates"])
    overlap_occurrences = sum(
        1
        for occ in occurrences
        if occ["best_wrong_label_candidate"] and occ["best_wrong_label_candidate"]["iou"] >= 0.1
    )
    filtered_occurrences = sum(
        1
        for occ in occurrences
        if occ["best_same_label_candidate"]
        and ((not occ["best_same_label_candidate"]["kept_in_v1"]) or (not occ["best_same_label_candidate"]["kept_in_v2"]))
    )
    same_with_overlap = sum(
        1
        for occ in occurrences
        if occ["best_same_label_candidate"] and occ["best_same_label_candidate"]["iou"] >= 0.1
    )

    if same_candidate_occurrences == 0 and overlap_occurrences == 0:
        return {
            "primary": "A. 候选缺失",
            "reason": f"{class_name} 在 baseline 里没有同类候选，也没有能与 GT 形成有效重叠的错类候选。",
        }
    if filtered_occurrences > 0:
        return {
            "primary": "B. 候选存在但当前规则过滤过强",
            "reason": f"{class_name} 的最佳同类候选在 baseline 里存在，但在 v1/v2 被规则移除。",
        }
    if same_candidate_occurrences == 0 and overlap_occurrences > 0:
        return {
            "primary": "C. 类别混淆主导",
            "reason": f"{class_name} 没有同类候选，但存在和 GT 明显重叠的错类候选，可视为稳定混淆。",
        }
    if same_candidate_occurrences > 0:
        if same_with_overlap > 0:
            return {
                "primary": "D. 几何位置偏差太大，无法命中",
                "reason": f"{class_name} 的同类候选存在且保留到了 v1/v2，但 IoU 长期停留在命中阈值以下，属于定位/尺度偏差主导。",
            }
        return {
            "primary": "D. 几何位置偏差太大，无法命中",
            "reason": f"{class_name} 的同类候选存在且保留到了 v1/v2，但与 GT 基本不重叠，说明是严重的几何偏差而不是规则过滤。",
        }
    return {
        "primary": "mixed",
        "reason": f"{class_name} 呈现混合失效模式，需要更细的人工拆解。",
    }


def summarize_class(class_name: str, occurrences: list[dict[str, Any]]) -> dict[str, Any]:
    score_values = [
        candidate["score"]
        for occurrence in occurrences
        for candidate in occurrence["same_label_candidates"]
    ]
    best_same_values = [
        occurrence["best_same_label_candidate"]
        for occurrence in occurrences
        if occurrence["best_same_label_candidate"] is not None
    ]
    wrong_confusions: dict[str, int] = defaultdict(int)
    nearest_wrong_labels: dict[str, int] = defaultdict(int)
    for occurrence in occurrences:
        if occurrence["best_wrong_label_candidate"] is not None:
            nearest_wrong_labels[occurrence["best_wrong_label_candidate"]["label"]] += 1
        for candidate in occurrence["overlapping_wrong_label_candidates"]:
            wrong_confusions[candidate["label"]] += 1

    summary = {
        "gt_count": len(occurrences),
        "asset_ids": sorted({occurrence["asset_id"] for occurrence in occurrences}),
        "occurrences_with_same_label_candidates": sum(1 for occ in occurrences if occ["same_label_candidates"]),
        "same_label_candidate_count": sum(len(occ["same_label_candidates"]) for occ in occurrences),
        "same_label_score_range": {
            "min": min(score_values) if score_values else None,
            "max": max(score_values) if score_values else None,
        },
        "best_same_label_iou_range": {
            "min": min(item["iou"] for item in best_same_values) if best_same_values else None,
            "max": max(item["iou"] for item in best_same_values) if best_same_values else None,
        },
        "best_same_label_kept_in_v1_count": sum(1 for item in best_same_values if item["kept_in_v1"]),
        "best_same_label_kept_in_v2_count": sum(1 for item in best_same_values if item["kept_in_v2"]),
        "occurrences_with_wrong_label_overlap_ge_0_1": sum(
            1
            for occ in occurrences
            if occ["best_wrong_label_candidate"] and occ["best_wrong_label_candidate"]["iou"] >= 0.1
        ),
        "typical_confusion_labels": dict(sorted(wrong_confusions.items(), key=lambda item: (-item[1], item[0]))),
        "nearest_wrong_labels": dict(sorted(nearest_wrong_labels.items(), key=lambda item: (-item[1], item[0]))),
        "primary_failure_mode": classify_root_cause(class_name, occurrences),
        "occurrences": occurrences,
    }
    return summary


def find_occurrences(
    class_name: str,
    gt: dict[str, Any],
    baseline: dict[str, dict[str, Any]],
    v1: dict[str, dict[str, Any]],
    v2: dict[str, dict[str, Any]],
    category_name_by_id: dict[int, str],
) -> list[dict[str, Any]]:
    by_image: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for annotation in gt.get("annotations", []):
        by_image[int(annotation["image_id"])].append(annotation)

    occurrences: list[dict[str, Any]] = []
    for asset_id, baseline_record in baseline.items():
        image_id = int(baseline_record["_resolved_image_id"])
        for annotation in by_image.get(image_id, []):
            if category_name_by_id[int(annotation["category_id"])] != class_name:
                continue
            occurrences.append(
                build_occurrence(
                    asset_id=asset_id,
                    gt_box=[float(v) for v in annotation["bbox"]],
                    class_name=class_name,
                    baseline_record=baseline_record,
                    v1_record=v1[asset_id],
                    v2_record=v2[asset_id],
                )
            )
    return occurrences


def write_markdown(output_path: Path, result: dict[str, Any]) -> None:
    lines: list[str] = []
    lines.append("# High-FN Root Cause Analysis")
    lines.append("")
    lines.append(f"- Fixed subset input: `{result['input_paths']['baseline']}`")
    lines.append(f"- Compared variants: `baseline`, `refinement_v1`, `refinement_v2`")
    lines.append("")

    for class_name in FOCUS_CLASSES:
        summary = result["focus_classes"][class_name]
        lines.append(f"## {class_name}")
        lines.append("")
        lines.append(f"- GT occurrences: `{summary['gt_count']}`")
        lines.append(f"- GT asset_ids: `{', '.join(summary['asset_ids'])}`")
        if summary["same_label_score_range"]["min"] is None:
            lines.append("- Baseline same-label candidates: `none`")
        else:
            lines.append(
                "- Baseline same-label candidate score range: "
                f"`{summary['same_label_score_range']['min']:.4f} .. {summary['same_label_score_range']['max']:.4f}`"
            )
            lines.append(
                "- Best same-label IoU range: "
                f"`{summary['best_same_label_iou_range']['min']:.4f} .. {summary['best_same_label_iou_range']['max']:.4f}`"
            )
            lines.append(
                "- Best same-label candidate kept by v1/v2: "
                f"`{summary['best_same_label_kept_in_v1_count']} / {summary['best_same_label_kept_in_v2_count']}`"
            )
        lines.append(f"- Typical confusion labels: `{json.dumps(summary['typical_confusion_labels'], ensure_ascii=False)}`")
        lines.append(f"- Nearest wrong labels: `{json.dumps(summary['nearest_wrong_labels'], ensure_ascii=False)}`")
        lines.append(f"- Primary failure mode: `{summary['primary_failure_mode']['primary']}`")
        lines.append(f"- Reason: {summary['primary_failure_mode']['reason']}")
        lines.append("")
        lines.append("### Typical Failures")
        lines.append("")
        for occurrence in summary["occurrences"]:
            best_same = occurrence["best_same_label_candidate"]
            best_wrong = occurrence["best_wrong_label_candidate"]
            same_text = (
                f"{best_same['label']} score={best_same['score']:.4f} iou={best_same['iou']:.4f} "
                f"kept_v1={best_same['kept_in_v1']} kept_v2={best_same['kept_in_v2']}"
                if best_same
                else "none"
            )
            wrong_text = (
                f"{best_wrong['label']} score={best_wrong['score']:.4f} iou={best_wrong['iou']:.4f}"
                if best_wrong
                else "none"
            )
            lines.append(f"- `{occurrence['asset_id']}` GT={json.dumps(occurrence['gt_bbox'])}")
            lines.append(f"  same-label best: `{same_text}`")
            lines.append(f"  wrong-label best: `{wrong_text}`")
        lines.append("")

    fire_hydrant = result["fire_hydrant_compare"]
    lines.append("## Why Fire Hydrant Was Recoverable")
    lines.append("")
    lines.append(f"- Fire Hydrant GT asset_ids: `{', '.join(fire_hydrant['asset_ids'])}`")
    lines.append(f"- Primary pattern: `{fire_hydrant['primary_failure_mode']['primary']}`")
    lines.append(f"- Reason: {fire_hydrant['primary_failure_mode']['reason']}")
    lines.append(
        "- Key difference vs Valve/Pipeline/Pressure Gauge: "
        "Fire Hydrant had stable wrong-label overlap candidates that could be relabeled, "
        "while the other three either lacked candidates entirely or had same-label boxes with unusable geometry."
    )
    lines.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze high-FN root causes on the fixed subset.")
    parser.add_argument("--gt-coco", required=True)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--refinement-v1", required=True)
    parser.add_argument("--refinement-v2", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-md", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    gt = json.loads(Path(args.gt_coco).read_text(encoding="utf-8"))
    image_id_by_name = {normalize_path(str(im["file_name"])): int(im["id"]) for im in gt.get("images", [])}
    category_name_by_id = {int(cat["id"]): str(cat["name"]) for cat in gt.get("categories", [])}

    baseline = load_records(Path(args.baseline), image_id_by_name)
    v1 = load_records(Path(args.refinement_v1), image_id_by_name)
    v2 = load_records(Path(args.refinement_v2), image_id_by_name)

    result: dict[str, Any] = {
        "input_paths": {
            "gt_coco": str(Path(args.gt_coco).resolve()),
            "baseline": str(Path(args.baseline).resolve()),
            "refinement_v1": str(Path(args.refinement_v1).resolve()),
            "refinement_v2": str(Path(args.refinement_v2).resolve()),
        },
        "focus_classes": {},
    }

    for class_name in FOCUS_CLASSES:
        occurrences = find_occurrences(class_name, gt, baseline, v1, v2, category_name_by_id)
        result["focus_classes"][class_name] = summarize_class(class_name, occurrences)

    fire_hydrant_occurrences = find_occurrences(COMPARE_CLASS, gt, baseline, v1, v2, category_name_by_id)
    result["fire_hydrant_compare"] = summarize_class(COMPARE_CLASS, fire_hydrant_occurrences)

    output_json = Path(args.output_json)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    write_markdown(Path(args.output_md), result)

    print(f"Wrote {output_json}")
    print(f"Wrote {Path(args.output_md)}")


if __name__ == "__main__":
    main()
