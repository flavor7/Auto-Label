import argparse
import json
from pathlib import Path
from typing import Any

from PIL import Image


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}


def polygon_area(points: list[list[float]]) -> float:
    if len(points) < 3:
        return 0.0
    area = 0.0
    for index, point in enumerate(points):
        next_point = points[(index + 1) % len(points)]
        area += point[0] * next_point[1] - next_point[0] * point[1]
    return abs(area) / 2.0


def polygon_to_bbox(points: list[list[float]]) -> list[float]:
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    x_min = min(xs)
    y_min = min(ys)
    x_max = max(xs)
    y_max = max(ys)
    return [x_min, y_min, x_max - x_min, y_max - y_min]


def flatten_polygon(points: list[list[float]]) -> list[float]:
    flat: list[float] = []
    for x_coord, y_coord in points:
        flat.extend([x_coord, y_coord])
    return flat


def convert(dataset_root: Path) -> dict[str, Any]:
    images: list[dict[str, Any]] = []
    annotations: list[dict[str, Any]] = []
    category_ids: dict[str, int] = {}
    image_id = 1
    annotation_id = 1

    for image_path in sorted(path for path in dataset_root.rglob("*") if path.suffix.lower() in IMAGE_SUFFIXES):
        if "Annotations" not in image_path.parts:
            continue

        annotation_path = image_path.with_suffix(".json")
        if not annotation_path.exists():
            continue

        with Image.open(image_path) as image:
            width, height = image.width, image.height

        images.append(
            {
                "id": image_id,
                "file_name": str(image_path.resolve()),
                "width": width,
                "height": height,
            }
        )

        data = json.loads(annotation_path.read_text(encoding="utf-8"))
        for shape in data.get("shapes", []):
            label = shape["label"]
            if label not in category_ids:
                category_ids[label] = len(category_ids) + 1
            points = shape.get("points", [])
            if not points:
                continue

            annotations.append(
                {
                    "id": annotation_id,
                    "image_id": image_id,
                    "category_id": category_ids[label],
                    "bbox": polygon_to_bbox(points),
                    "segmentation": [flatten_polygon(points)],
                    "area": polygon_area(points),
                    "iscrowd": 0,
                }
            )
            annotation_id += 1

        image_id += 1

    categories = [
        {"id": category_id, "name": label}
        for label, category_id in sorted(category_ids.items(), key=lambda item: item[1])
    ]
    return {"images": images, "annotations": annotations, "categories": categories}


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert InspecSafe labelme-style polygons to COCO.")
    parser.add_argument("--dataset-root", required=True, help="Path to InspecSafe DATA_PATH directory.")
    parser.add_argument("--output", required=True, help="Output COCO JSON path.")
    args = parser.parse_args()

    dataset_root = Path(args.dataset_root)
    payload = convert(dataset_root)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Images: {len(payload['images'])}")
    print(f"Annotations: {len(payload['annotations'])}")
    print(f"Categories: {len(payload['categories'])}")
    print(f"Output: {output_path.resolve()}")


if __name__ == "__main__":
    main()
