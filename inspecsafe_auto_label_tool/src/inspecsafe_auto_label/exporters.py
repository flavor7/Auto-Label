from pathlib import Path
from typing import Any, Iterable, Sequence
from urllib.parse import quote

from .indexing import load_jsonl, write_json


def _polygon_area(points: list[list[float]]) -> float:
    if len(points) < 3:
        return 0.0
    area = 0.0
    for index, point in enumerate(points):
        next_point = points[(index + 1) % len(points)]
        area += point[0] * next_point[1] - next_point[0] * point[1]
    return abs(area) / 2.0


def _polygon_to_bbox(points: list[list[float]]) -> list[float]:
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    x_min = min(xs)
    y_min = min(ys)
    x_max = max(xs)
    y_max = max(ys)
    return [x_min, y_min, x_max - x_min, y_max - y_min]


def _flatten_polygon(points: list[list[float]]) -> list[float]:
    flat: list[float] = []
    for x_coord, y_coord in points:
        flat.extend([x_coord, y_coord])
    return flat


def build_asset_lookups(asset_records: Sequence[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    by_asset_id: dict[str, dict[str, Any]] = {}
    by_image_path: dict[str, dict[str, Any]] = {}
    for record in asset_records:
        by_asset_id[record["asset_id"]] = record
        by_image_path[str(Path(record["image_abs_path"]).resolve())] = record
    return by_asset_id, by_image_path


def predictions_to_coco(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    records = list(records)
    categories: dict[str, int] = {}
    images: list[dict[str, Any]] = []
    annotations: list[dict[str, Any]] = []
    annotation_id = 1

    for image_id, record in enumerate(records, start=1):
        file_name = record.get("image_rel_path") or record.get("image_path")
        images.append(
            {
                "id": image_id,
                "file_name": file_name,
                "width": record["width"],
                "height": record["height"],
                "asset_id": record.get("asset_id"),
            }
        )

        for prediction in record.get("predictions", []):
            label = prediction["label"]
            if label not in categories:
                categories[label] = len(categories) + 1

            polygon = prediction.get("polygon") or []
            if polygon:
                bbox = _polygon_to_bbox(polygon)
                segmentation = [_flatten_polygon(polygon)]
                area = _polygon_area(polygon)
            else:
                x1, y1, x2, y2 = prediction["bbox"]
                bbox = [x1, y1, x2 - x1, y2 - y1]
                segmentation = []
                area = bbox[2] * bbox[3]

            annotations.append(
                {
                    "id": annotation_id,
                    "image_id": image_id,
                    "category_id": categories[label],
                    "bbox": bbox,
                    "segmentation": segmentation,
                    "area": area,
                    "iscrowd": 0,
                    "score": prediction.get("score"),
                }
            )
            annotation_id += 1

    coco_categories = [
        {"id": category_id, "name": label}
        for label, category_id in sorted(categories.items(), key=lambda item: item[1])
    ]
    return {"images": images, "annotations": annotations, "categories": coco_categories}


def to_local_files_url(path: str, document_root: str | Path | None = None) -> str:
    if document_root is None:
        return path
    file_path = Path(path).resolve()
    root = Path(document_root).resolve()
    relative_path = file_path.relative_to(root)
    return "/data/local-files/?d=" + quote(relative_path.as_posix(), safe="/")


def to_http_url(path: str, url_root: str | Path, url_prefix: str) -> str:
    file_path = Path(path).resolve()
    root = Path(url_root).resolve()
    relative_path = file_path.relative_to(root)
    return url_prefix.rstrip("/") + "/" + quote(relative_path.as_posix(), safe="/")


def asset_records_to_label_studio_tasks(
    asset_records: Sequence[dict[str, Any]],
    document_root: str | Path | None = None,
    url_prefix: str | None = None,
    url_root: str | Path | None = None,
) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    resolved_url_root = url_root if url_root is not None else document_root

    for index, record in enumerate(asset_records, start=1):
        image_url = (
            to_http_url(record["image_abs_path"], resolved_url_root, url_prefix)
            if url_prefix
            else to_local_files_url(record["image_abs_path"], document_root)
        )
        tasks.append(
            {
                "id": index,
                "data": {
                    "asset_id": record["asset_id"],
                    "image": image_url,
                    "split": record["split"],
                    "subset": record["subset"],
                    "sample_id": record["sample_id"],
                    "task_group_id": record["task_group_id"],
                },
            }
        )
    return tasks


def predictions_to_label_studio(
    records: Iterable[dict[str, Any]],
    asset_records: Sequence[dict[str, Any]] | None = None,
    document_root: str | Path | None = None,
    url_prefix: str | None = None,
    url_root: str | Path | None = None,
) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    asset_by_id: dict[str, dict[str, Any]] = {}
    asset_by_image_path: dict[str, dict[str, Any]] = {}
    if asset_records:
        asset_by_id, asset_by_image_path = build_asset_lookups(asset_records)

    resolved_url_root = url_root if url_root is not None else document_root

    for task_id, record in enumerate(records, start=1):
        width = record["width"]
        height = record["height"]
        results: list[dict[str, Any]] = []

        asset = None
        if record.get("asset_id"):
            asset = asset_by_id.get(record["asset_id"])
        if asset is None and record.get("image_path"):
            asset = asset_by_image_path.get(str(Path(record["image_path"]).resolve()))

        for prediction_id, prediction in enumerate(record.get("predictions", []), start=1):
            polygon = prediction.get("polygon") or []
            if not polygon:
                x1, y1, x2, y2 = prediction["bbox"]
                polygon = [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]

            results.append(
                {
                    "id": f"{task_id}-{prediction_id}",
                    "type": "polygonlabels",
                    "from_name": "label",
                    "to_name": "image",
                    "original_width": width,
                    "original_height": height,
                    "image_rotation": 0,
                    "value": {
                        "points": [
                            [round(point[0] / width * 100, 4), round(point[1] / height * 100, 4)]
                            for point in polygon
                        ],
                        "polygonlabels": [prediction["label"]],
                    },
                    "score": prediction.get("score"),
                }
            )

        image_path = asset["image_abs_path"] if asset else record.get("image_path", "")
        image_url = (
            to_http_url(image_path, resolved_url_root, url_prefix)
            if url_prefix and image_path
            else to_local_files_url(image_path, document_root)
        )
        data = {
            "asset_id": asset["asset_id"] if asset else record.get("asset_id", ""),
            "image": image_url,
            "split": asset["split"] if asset else "",
            "subset": asset["subset"] if asset else "",
            "sample_id": asset["sample_id"] if asset else "",
            "task_group_id": asset["task_group_id"] if asset else "",
        }

        tasks.append(
            {
                "id": task_id,
                "data": data,
                "predictions": [{"model_version": "bootstrap-v1", "result": results}],
            }
        )

    return tasks


__all__ = [
    "asset_records_to_label_studio_tasks",
    "build_asset_lookups",
    "load_jsonl",
    "predictions_to_coco",
    "predictions_to_label_studio",
    "to_http_url",
    "to_local_files_url",
    "write_json",
]
