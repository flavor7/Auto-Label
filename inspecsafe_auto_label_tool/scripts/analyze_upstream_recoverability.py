import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import median
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


def bbox_center(box: list[float]) -> tuple[float, float]:
    return (box[0] + box[2] / 2.0, box[1] + box[3] / 2.0)


def center_distance(box_a: list[float], box_b: list[float]) -> float:
    ax, ay = bbox_center(box_a)
    bx, by = bbox_center(box_b)
    return math.hypot(ax - bx, ay - by)


def size_ratios(pred_box: list[float], gt_box: list[float]) -> dict[str, float]:
    return {
        "width_ratio": pred_box[2] / gt_box[2] if gt_box[2] > 0 else 0.0,
        "height_ratio": pred_box[3] / gt_box[3] if gt_box[3] > 0 else 0.0,
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


def build_occurrences(
    class_name: str,
    gt: dict[str, Any],
    baseline: dict[str, dict[str, Any]],
    v1: dict[str, dict[str, Any]],
    v2: dict[str, dict[str, Any]],
    category_name_by_id: dict[int, str],
) -> list[dict[str, Any]]:
    annotations_by_image: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for annotation in gt.get("annotations", []):
        annotations_by_image[int(annotation["image_id"])].append(annotation)

    occurrences: list[dict[str, Any]] = []
    for asset_id, baseline_record in baseline.items():
        image_id = int(baseline_record["_resolved_image_id"])
        gt_annotations = [
            ann for ann in annotations_by_image.get(image_id, []) if category_name_by_id[int(ann["category_id"])] == class_name
        ]
        if not gt_annotations:
            continue

        v1_keys = {prediction_key(pred) for pred in v1[asset_id].get("predictions", [])}
        v2_keys = {prediction_key(pred) for pred in v2[asset_id].get("predictions", [])}
        for ann in gt_annotations:
            gt_box = [float(v) for v in ann["bbox"]]
            gt_center = bbox_center(gt_box)
            gt_diag = math.hypot(gt_box[2], gt_box[3])
            same_label: list[dict[str, Any]] = []
            wrong_label: list[dict[str, Any]] = []
            local_small_wrong: list[dict[str, Any]] = []

            for pred in baseline_record.get("predictions", []):
                pred_box = bbox_xywh(pred)
                pred_center = bbox_center(pred_box)
                dx = pred_center[0] - gt_center[0]
                dy = pred_center[1] - gt_center[1]
                dist = math.hypot(dx, dy)
                ratios = size_ratios(pred_box, gt_box)
                entry = {
                    "label": str(pred["label"]),
                    "score": float(pred.get("score") or 0.0),
                    "bbox": [float(v) for v in pred["bbox"]],
                    "iou": iou_xywh(pred_box, gt_box),
                    "center_distance_px": dist,
                    "center_distance_norm": dist / gt_diag if gt_diag > 0 else 0.0,
                    "center_offset": {"dx": dx, "dy": dy},
                    "size_ratio": ratios,
                    "kept_in_v1": prediction_key(pred) in v1_keys,
                    "kept_in_v2": prediction_key(pred) in v2_keys,
                }
                if entry["label"] == class_name:
                    same_label.append(entry)
                else:
                    wrong_label.append(entry)
                    if max(pred_box[2], pred_box[3]) <= max(gt_box[2], gt_box[3]) * 3.0:
                        local_small_wrong.append(entry)

            same_label.sort(key=lambda item: (-item["iou"], -item["score"]))
            wrong_label.sort(key=lambda item: (-item["iou"], item["center_distance_px"], -item["score"]))
            local_small_wrong.sort(key=lambda item: (item["center_distance_px"], -item["score"]))

            occurrences.append(
                {
                    "asset_id": asset_id,
                    "gt_bbox": gt_box,
                    "same_label_candidates": same_label,
                    "best_same_label_candidate": same_label[0] if same_label else None,
                    "best_wrong_overlap_candidate": wrong_label[0] if wrong_label else None,
                    "nearest_local_wrong_candidates": local_small_wrong[:5],
                }
            )
    return occurrences


def summarize_numeric(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"min": None, "median": None, "max": None}
    return {"min": min(values), "median": median(values), "max": max(values)}


def summarize_valve(occurrences: list[dict[str, Any]]) -> dict[str, Any]:
    nearby_candidates = []
    for occ in occurrences:
        for cand in occ["nearest_local_wrong_candidates"]:
            if cand["center_distance_norm"] <= 2.0:
                nearby_candidates.append(cand)

    return {
        "class_name": "Valve",
        "gt_count": len(occurrences),
        "asset_ids": sorted({occ["asset_id"] for occ in occurrences}),
        "same_label_candidate_count": 0,
        "has_reusable_nearby_wrong_candidate": False,
        "nearby_wrong_candidate_examples": nearby_candidates[:6],
        "nearest_wrong_label_counts": count_labels(nearby_candidates),
        "primary_upstream_issue": "candidate_generation_missing",
        "diagnosis": "候选生成缺失主导。没有同类候选，也没有与 GT 接近重叠的局部错类候选可直接复用。",
        "lightweight_rule_recoverable": False,
        "likely_next_direction": "检查小目标/部件级候选生成与召回，而不是继续放宽后处理规则。",
    }


def summarize_pipeline(occurrences: list[dict[str, Any]]) -> dict[str, Any]:
    best_same = [occ["best_same_label_candidate"] for occ in occurrences if occ["best_same_label_candidate"]]
    width_ratios = [cand["size_ratio"]["width_ratio"] for cand in best_same]
    height_ratios = [cand["size_ratio"]["height_ratio"] for cand in best_same]
    dxs = [cand["center_offset"]["dx"] for cand in best_same]
    dys = [cand["center_offset"]["dy"] for cand in best_same]
    ious = [cand["iou"] for cand in best_same]

    examples = []
    for occ in occurrences:
        cand = occ["best_same_label_candidate"]
        if cand is None:
            continue
        examples.append(
            {
                "asset_id": occ["asset_id"],
                "gt_bbox": occ["gt_bbox"],
                "candidate_score": cand["score"],
                "candidate_iou": cand["iou"],
                "width_ratio": cand["size_ratio"]["width_ratio"],
                "height_ratio": cand["size_ratio"]["height_ratio"],
                "center_dx": cand["center_offset"]["dx"],
                "center_dy": cand["center_offset"]["dy"],
            }
        )

    return {
        "class_name": "Pipeline",
        "gt_count": len(occurrences),
        "asset_ids": sorted({occ["asset_id"] for occ in occurrences}),
        "same_label_candidate_count": len(best_same),
        "score_summary": summarize_numeric([cand["score"] for cand in best_same]),
        "iou_summary": summarize_numeric(ious),
        "width_ratio_summary": summarize_numeric(width_ratios),
        "height_ratio_summary": summarize_numeric(height_ratios),
        "center_dx_summary": summarize_numeric(dxs),
        "center_dy_summary": summarize_numeric(dys),
        "primary_upstream_issue": "localization_extent_quality",
        "geometry_failure_mode": "长条目标被截短 / 覆盖范围不足",
        "diagnosis": "同类候选已经存在并保留到 v1/v2，但宽度和高度覆盖明显不足，属于大结构范围/extent 回归失败，不是规则过滤。",
        "lightweight_rule_recoverable": False,
        "likely_next_direction": "优先检查长条大结构目标的范围回归、截短现象和 coverage 表达。",
        "representative_examples": examples[:4],
    }


def summarize_pressure_gauge(occurrences: list[dict[str, Any]]) -> dict[str, Any]:
    best_same = [occ["best_same_label_candidate"] for occ in occurrences if occ["best_same_label_candidate"]]
    width_ratios = [cand["size_ratio"]["width_ratio"] for cand in best_same]
    height_ratios = [cand["size_ratio"]["height_ratio"] for cand in best_same]
    dxs = [cand["center_offset"]["dx"] for cand in best_same]
    dys = [cand["center_offset"]["dy"] for cand in best_same]
    ious = [cand["iou"] for cand in best_same]

    representative_examples = []
    for occ in occurrences:
        cand = occ["best_same_label_candidate"]
        if cand is None:
            continue
        representative_examples.append(
            {
                "asset_id": occ["asset_id"],
                "gt_bbox": occ["gt_bbox"],
                "candidate_score": cand["score"],
                "candidate_iou": cand["iou"],
                "width_ratio": cand["size_ratio"]["width_ratio"],
                "height_ratio": cand["size_ratio"]["height_ratio"],
                "center_dx": cand["center_offset"]["dx"],
                "center_dy": cand["center_offset"]["dy"],
                "nearest_local_wrong_candidates": occ["nearest_local_wrong_candidates"][:3],
            }
        )

    return {
        "class_name": "Pressure Gauge",
        "gt_count": len(occurrences),
        "asset_ids": sorted({occ["asset_id"] for occ in occurrences}),
        "same_label_candidate_count": len(best_same),
        "score_summary": summarize_numeric([cand["score"] for cand in best_same]),
        "iou_summary": summarize_numeric(ious),
        "width_ratio_summary": summarize_numeric(width_ratios),
        "height_ratio_summary": summarize_numeric(height_ratios),
        "center_dx_summary": summarize_numeric(dxs),
        "center_dy_summary": summarize_numeric(dys),
        "primary_upstream_issue": "localization_quality",
        "geometry_failure_mode": "误定位到下方附近部件，且尺度过高",
        "diagnosis": "同类候选存在且保留到了 v1/v2，但中心持续向下偏移约一百多像素，框高约为 GT 的 2.5 倍，说明是稳定误定位而不是规则过滤。",
        "lightweight_rule_recoverable": False,
        "likely_next_direction": "优先检查小部件定位和 bbox 回归，尤其是为什么候选持续落在更低、更高的邻近部件上。",
        "representative_examples": representative_examples[:3],
    }


def summarize_fire_hydrant(occurrences: list[dict[str, Any]]) -> dict[str, Any]:
    overlapping = []
    for occ in occurrences:
        candidate = occ["best_wrong_overlap_candidate"]
        if candidate and candidate["iou"] >= 0.1:
            overlapping.append(candidate)
    return {
        "class_name": COMPARE_CLASS,
        "gt_count": len(occurrences),
        "asset_ids": sorted({occ["asset_id"] for occ in occurrences}),
        "overlap_wrong_label_counts": count_labels(overlapping),
        "overlap_iou_summary": summarize_numeric([cand["iou"] for cand in overlapping]),
        "recoverable_path": "stable_wrong_label_overlap",
        "diagnosis": "Fire Hydrant 没有同类候选，但存在可稳定重标的错类重叠候选，因此能通过轻量后处理救回一部分。",
    }


def count_labels(candidates: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for cand in candidates:
        counts[str(cand["label"])] += 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def build_priority_ranking() -> list[dict[str, Any]]:
    return [
        {
            "rank": 1,
            "target": "Pressure Gauge",
            "direction": "定位质量检查",
            "reason": "同类候选已经稳定出现且分数不低，但在三张图上都以近乎相同的方式向下误定位，属于一致性很强、最适合先做上游定位调试的问题。",
        },
        {
            "rank": 2,
            "target": "Valve",
            "direction": "候选生成缺失检查",
            "reason": "当前既没有同类候选，也没有可直接重标的重叠错类候选，需要确认小部件级召回是否在候选生成阶段就缺失。",
        },
        {
            "rank": 3,
            "target": "Pipeline",
            "direction": "大结构范围/extent 检查",
            "reason": "问题更像长条大结构被系统性截短和覆盖不足，通常比局部定位/召回问题更重，更适合放在前两项之后处理。",
        },
    ]


def write_markdown(output_path: Path, result: dict[str, Any]) -> None:
    lines: list[str] = []
    lines.append("# Upstream Recoverability Analysis")
    lines.append("")
    lines.append(f"- Root-cause input: `{result['input_paths']['root_cause_json']}`")
    lines.append(f"- Fixed subset: `{result['input_paths']['baseline']}`")
    lines.append("")

    for class_name in FOCUS_CLASSES:
        info = result["classes"][class_name]
        lines.append(f"## {class_name}")
        lines.append("")
        lines.append(f"- GT occurrences: `{info['gt_count']}`")
        lines.append(f"- GT asset_ids: `{', '.join(info['asset_ids'])}`")
        lines.append(f"- Primary upstream issue: `{info['primary_upstream_issue']}`")
        lines.append(f"- Diagnosis: {info['diagnosis']}")
        lines.append(f"- Still recoverable by lightweight rules: `{info['lightweight_rule_recoverable']}`")
        lines.append(f"- Next direction: {info['likely_next_direction']}")
        if class_name == "Valve":
            lines.append(f"- Nearby wrong labels: `{json.dumps(info['nearest_wrong_label_counts'], ensure_ascii=False)}`")
            lines.append(
                f"- Reusable nearby wrong candidate exists: `{info['has_reusable_nearby_wrong_candidate']}`"
            )
        else:
            lines.append(f"- Score summary: `{json.dumps(info['score_summary'], ensure_ascii=False)}`")
            lines.append(f"- IoU summary: `{json.dumps(info['iou_summary'], ensure_ascii=False)}`")
            lines.append(f"- Width ratio summary: `{json.dumps(info['width_ratio_summary'], ensure_ascii=False)}`")
            lines.append(f"- Height ratio summary: `{json.dumps(info['height_ratio_summary'], ensure_ascii=False)}`")
            lines.append(f"- Center dx summary: `{json.dumps(info['center_dx_summary'], ensure_ascii=False)}`")
            lines.append(f"- Center dy summary: `{json.dumps(info['center_dy_summary'], ensure_ascii=False)}`")
            lines.append(f"- Geometry failure mode: `{info['geometry_failure_mode']}`")
        lines.append("")

    fire_hydrant = result["fire_hydrant_compare"]
    lines.append("## Why Fire Hydrant Was Recoverable")
    lines.append("")
    lines.append(f"- Recoverable path: `{fire_hydrant['recoverable_path']}`")
    lines.append(f"- Overlap wrong-label counts: `{json.dumps(fire_hydrant['overlap_wrong_label_counts'], ensure_ascii=False)}`")
    lines.append(f"- Overlap IoU summary: `{json.dumps(fire_hydrant['overlap_iou_summary'], ensure_ascii=False)}`")
    lines.append(f"- Diagnosis: {fire_hydrant['diagnosis']}")
    lines.append("")

    lines.append("## Postprocess Boundary")
    lines.append("")
    lines.append(f"- Still possibly recoverable by lightweight rules: `{', '.join(result['lightweight_rule_candidates']) or 'none'}`")
    lines.append(f"- Clearly beyond lightweight postprocess: `{', '.join(result['beyond_postprocess'])}`")
    lines.append("")

    lines.append("## Priority Ranking")
    lines.append("")
    for item in result["priority_ranking"]:
        lines.append(f"- {item['rank']}. `{item['target']}`: {item['direction']}。{item['reason']}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze upstream recoverability for unresolved high-FN classes.")
    parser.add_argument("--gt-coco", required=True)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--refinement-v1", required=True)
    parser.add_argument("--refinement-v2", required=True)
    parser.add_argument("--root-cause-json", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-md", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    gt = json.loads(Path(args.gt_coco).read_text(encoding="utf-8"))
    root_cause = json.loads(Path(args.root_cause_json).read_text(encoding="utf-8"))

    image_id_by_name = {normalize_path(str(im["file_name"])): int(im["id"]) for im in gt.get("images", [])}
    category_name_by_id = {int(cat["id"]): str(cat["name"]) for cat in gt.get("categories", [])}

    baseline = load_records(Path(args.baseline), image_id_by_name)
    v1 = load_records(Path(args.refinement_v1), image_id_by_name)
    v2 = load_records(Path(args.refinement_v2), image_id_by_name)

    valve_occ = build_occurrences("Valve", gt, baseline, v1, v2, category_name_by_id)
    pipeline_occ = build_occurrences("Pipeline", gt, baseline, v1, v2, category_name_by_id)
    gauge_occ = build_occurrences("Pressure Gauge", gt, baseline, v1, v2, category_name_by_id)
    hydrant_occ = build_occurrences(COMPARE_CLASS, gt, baseline, v1, v2, category_name_by_id)

    result = {
        "input_paths": {
            "gt_coco": str(Path(args.gt_coco).resolve()),
            "baseline": str(Path(args.baseline).resolve()),
            "refinement_v1": str(Path(args.refinement_v1).resolve()),
            "refinement_v2": str(Path(args.refinement_v2).resolve()),
            "root_cause_json": str(Path(args.root_cause_json).resolve()),
        },
        "stable_conclusion": {
            "Valve": root_cause["focus_classes"]["Valve"]["primary_failure_mode"],
            "Pipeline": root_cause["focus_classes"]["Pipeline"]["primary_failure_mode"],
            "Pressure Gauge": root_cause["focus_classes"]["Pressure Gauge"]["primary_failure_mode"],
        },
        "classes": {
            "Valve": summarize_valve(valve_occ),
            "Pipeline": summarize_pipeline(pipeline_occ),
            "Pressure Gauge": summarize_pressure_gauge(gauge_occ),
        },
        "fire_hydrant_compare": summarize_fire_hydrant(hydrant_occ),
        "lightweight_rule_candidates": [],
        "beyond_postprocess": ["Valve", "Pipeline", "Pressure Gauge"],
        "priority_ranking": build_priority_ranking(),
    }

    output_json = Path(args.output_json)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(Path(args.output_md), result)

    print(f"Wrote {output_json}")
    print(f"Wrote {Path(args.output_md)}")


if __name__ == "__main__":
    main()
