import argparse
import json
from pathlib import Path
from typing import Any


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for line in handle:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def write_jsonl(records: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def bbox_from_polygon(points: list[list[float]]) -> list[float]:
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return [min(xs), min(ys), max(xs), max(ys)]


def polygon_area(points: list[list[float]]) -> float:
    if len(points) < 3:
        return 0.0
    area = 0.0
    for index, point in enumerate(points):
        next_point = points[(index + 1) % len(points)]
        area += point[0] * next_point[1] - next_point[0] * point[1]
    return abs(area) / 2.0


def scale_points(points: list[list[float]], width: float, height: float) -> list[list[float]]:
    return [[round(float(x) / 100.0 * width, 4), round(float(y) / 100.0 * height, 4)] for x, y in points]


def labels_from_value(value: dict[str, Any]) -> list[str]:
    for key in ("polygonlabels", "rectanglelabels", "labels"):
        labels = value.get(key)
        if isinstance(labels, list):
            return [str(label) for label in labels]
    return []


def convert_polygon_result(result: dict[str, Any]) -> dict[str, Any] | None:
    value = result.get("value") or {}
    raw_points = value.get("points") or []
    if not raw_points:
        return None

    width = float(result.get("original_width") or 0)
    height = float(result.get("original_height") or 0)
    if width <= 0 or height <= 0:
        return None

    polygon = scale_points(raw_points, width, height)
    bbox = bbox_from_polygon(polygon)
    labels = labels_from_value(value)

    return {
        "label": labels[0] if labels else "",
        "labels": labels,
        "type": "polygon",
        "bbox": bbox,
        "bbox_xywh": [bbox[0], bbox[1], round(bbox[2] - bbox[0], 4), round(bbox[3] - bbox[1], 4)],
        "polygon": polygon,
        "area": round(polygon_area(polygon), 4),
        "source_result_id": result.get("id", ""),
        "score": result.get("score"),
    }


def convert_rectangle_result(result: dict[str, Any]) -> dict[str, Any] | None:
    value = result.get("value") or {}
    required = ("x", "y", "width", "height")
    if any(key not in value for key in required):
        return None

    image_width = float(result.get("original_width") or 0)
    image_height = float(result.get("original_height") or 0)
    if image_width <= 0 or image_height <= 0:
        return None

    x1 = round(float(value["x"]) / 100.0 * image_width, 4)
    y1 = round(float(value["y"]) / 100.0 * image_height, 4)
    rect_width = round(float(value["width"]) / 100.0 * image_width, 4)
    rect_height = round(float(value["height"]) / 100.0 * image_height, 4)
    x2 = round(x1 + rect_width, 4)
    y2 = round(y1 + rect_height, 4)
    polygon = [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]
    labels = labels_from_value(value)

    return {
        "label": labels[0] if labels else "",
        "labels": labels,
        "type": "rectangle",
        "bbox": [x1, y1, x2, y2],
        "bbox_xywh": [x1, y1, rect_width, rect_height],
        "polygon": polygon,
        "area": round(rect_width * rect_height, 4),
        "source_result_id": result.get("id", ""),
        "score": result.get("score"),
    }


def convert_result(result: dict[str, Any]) -> dict[str, Any] | None:
    result_type = str(result.get("type") or "")
    if result_type == "polygonlabels":
        return convert_polygon_result(result)
    if result_type == "rectanglelabels":
        return convert_rectangle_result(result)
    return None


def select_annotation(task: dict[str, Any]) -> dict[str, Any] | None:
    annotations = [ann for ann in task.get("annotations", []) if not ann.get("was_cancelled")]
    if not annotations:
        return None
    return sorted(
        annotations,
        key=lambda ann: (str(ann.get("updated_at") or ann.get("created_at") or ""), int(ann.get("id") or 0)),
    )[-1]


def convert_task(task: dict[str, Any], asset_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    data = task.get("data") or {}
    asset_id = str(data.get("asset_id") or "")
    if not asset_id:
        raise ValueError(f"Task {task.get('id')} has no data.asset_id")

    asset = asset_by_id.get(asset_id)
    if asset is None:
        raise KeyError(f"asset_id not found in asset manifest: {asset_id}")

    annotation = select_annotation(task)
    converted: list[dict[str, Any]] = []
    unsupported_types: dict[str, int] = {}

    if annotation:
        for result in annotation.get("result", []):
            converted_result = convert_result(result)
            if converted_result is None:
                result_type = str(result.get("type") or "unknown")
                unsupported_types[result_type] = unsupported_types.get(result_type, 0) + 1
                continue
            converted.append(converted_result)

    return {
        "asset_id": asset_id,
        "image_path": asset.get("image_abs_path", ""),
        "image_rel_path": asset.get("image_rel_path", ""),
        "width": int(asset.get("width") or 0),
        "height": int(asset.get("height") or 0),
        "split": asset.get("split", data.get("split", "")),
        "subset": asset.get("subset", data.get("subset", "")),
        "sample_id": asset.get("sample_id", data.get("sample_id", "")),
        "task_group_id": asset.get("task_group_id", data.get("task_group_id", "")),
        "review_source": "label_studio",
        "label_studio_task_id": task.get("id"),
        "label_studio_project_id": task.get("project"),
        "label_studio_annotation_id": annotation.get("id") if annotation else None,
        "reviewed_at": annotation.get("updated_at") if annotation else None,
        "was_cancelled": bool(annotation.get("was_cancelled")) if annotation else False,
        "annotations": converted,
        "annotation_count": len(converted),
        "unsupported_result_types": unsupported_types,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert Label Studio JSON export to reviewed_annotations.jsonl.")
    parser.add_argument("--input", required=True, help="Label Studio JSON export path.")
    parser.add_argument("--asset-manifest", required=True, help="Canonical asset_manifest.jsonl path.")
    parser.add_argument("--output", required=True, help="Output reviewed_annotations.jsonl path.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    asset_manifest_path = Path(args.asset_manifest)
    output_path = Path(args.output)

    export_payload = json.loads(input_path.read_text(encoding="utf-8-sig"))
    if not isinstance(export_payload, list):
        raise TypeError("Label Studio export must be a JSON list of tasks.")

    asset_records = load_jsonl(asset_manifest_path)
    asset_by_id = {str(record["asset_id"]): record for record in asset_records}
    reviewed_records = [convert_task(task, asset_by_id) for task in export_payload]
    write_jsonl(reviewed_records, output_path)

    result_type_counts: dict[str, int] = {}
    annotation_count = 0
    for record in reviewed_records:
        annotation_count += int(record["annotation_count"])
        for annotation in record["annotations"]:
            result_type = str(annotation["type"])
            result_type_counts[result_type] = result_type_counts.get(result_type, 0) + 1

    print(f"Converted tasks: {len(reviewed_records)}")
    print(f"Converted annotations: {annotation_count}")
    print(f"Supported annotation types: {', '.join(sorted(result_type_counts)) or 'none'}")
    print(f"Output: {output_path.resolve()}")


if __name__ == "__main__":
    main()
