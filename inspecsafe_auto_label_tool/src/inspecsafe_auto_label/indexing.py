import hashlib
import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Iterable, List, Sequence

from PIL import Image

from .types import AssetRecord, ImageRecord, JsonDict


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}


def _read_image_size(image_path: Path) -> tuple[int, int]:
    with Image.open(image_path) as image:
        return image.width, image.height


def _iter_annotation_images(split_root: Path) -> Iterable[Path]:
    annotations_dir = split_root / "Annotations"
    if not annotations_dir.exists():
        return []

    return (
        path
        for path in annotations_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    )


def _compute_sha1(file_path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha1()
    with file_path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _normalize_rel_path(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _build_asset_id(split: str, sample_id: str) -> str:
    return f"{split}:{sample_id}"


def build_asset_manifest(dataset_root: str | Path, splits: Sequence[str] = ("train", "test")) -> List[AssetRecord]:
    dataset_root = Path(dataset_root)
    records: List[AssetRecord] = []

    for split in splits:
        split_root = dataset_root / split
        for image_path in _iter_annotation_images(split_root):
            annotation_path = image_path.with_suffix(".json")
            text_path = image_path.with_suffix(".txt")

            if not annotation_path.exists() or not text_path.exists():
                continue

            width, height = _read_image_size(image_path)
            stat = image_path.stat()
            sample_dir = image_path.parent.name
            subset = image_path.parent.parent.name if image_path.parent.parent else "unknown"
            sample_id = image_path.stem

            records.append(
                AssetRecord(
                    asset_id=_build_asset_id(split, sample_id),
                    image_rel_path=_normalize_rel_path(image_path, dataset_root),
                    image_abs_path=str(image_path.resolve()),
                    split=split,
                    subset=subset,
                    sample_dir=sample_dir,
                    sample_id=sample_id,
                    task_group_id=sample_dir,
                    width=width,
                    height=height,
                    annotation_abs_path=str(annotation_path.resolve()),
                    text_abs_path=str(text_path.resolve()),
                    file_size=stat.st_size,
                    mtime=stat.st_mtime,
                    sha1=_compute_sha1(image_path),
                )
            )

    records.sort(key=lambda item: (item.split, item.subset, item.task_group_id, item.sample_id))
    return records


def derive_legacy_image_index(records: Sequence[AssetRecord]) -> List[ImageRecord]:
    return [
        ImageRecord(
            image_path=record.image_abs_path,
            split=record.split,
            subset=record.subset,
            sample_dir=record.sample_dir,
            sample_id=record.sample_id,
            annotation_path=record.annotation_abs_path,
            text_path=record.text_abs_path,
            width=record.width,
            height=record.height,
        )
        for record in records
    ]


def _to_json_ready(item: Any) -> JsonDict:
    if is_dataclass(item):
        return asdict(item)
    if isinstance(item, dict):
        return item
    raise TypeError(f"Unsupported record type: {type(item)!r}")


def write_jsonl(records: Iterable[Any], output_path: str | Path) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(_to_json_ready(record), ensure_ascii=False) + "\n")


def append_jsonl(records: Iterable[Any], output_path: str | Path) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("a", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(_to_json_ready(record), ensure_ascii=False) + "\n")


def load_jsonl(path: str | Path) -> List[JsonDict]:
    records: List[JsonDict] = []
    with Path(path).open("r", encoding="utf-8-sig") as handle:
        for line in handle:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def write_json(payload: Any, output_path: str | Path) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)


def summarize_asset_manifest(records: Sequence[AssetRecord]) -> JsonDict:
    by_split: dict[str, int] = {}
    by_subset: dict[str, int] = {}
    task_group_sizes: dict[str, int] = {}

    for record in records:
        by_split[record.split] = by_split.get(record.split, 0) + 1
        subset_key = f"{record.split}/{record.subset}"
        by_subset[subset_key] = by_subset.get(subset_key, 0) + 1
        task_group_key = f"{record.split}/{record.subset}/{record.task_group_id}"
        task_group_sizes[task_group_key] = task_group_sizes.get(task_group_key, 0) + 1

    group_size_distribution: dict[str, int] = {}
    for group_size in task_group_sizes.values():
        group_size_distribution[str(group_size)] = group_size_distribution.get(str(group_size), 0) + 1

    return {
        "total_assets": len(records),
        "by_split": by_split,
        "by_subset": by_subset,
        "task_groups": {
            "total_groups": len(task_group_sizes),
            "max_group_size": max(task_group_sizes.values()) if task_group_sizes else 0,
            "group_size_distribution": group_size_distribution,
        },
    }


def validate_asset_manifest_records(
    records: Sequence[JsonDict],
    dataset_root: str | Path | None = None,
    verify_sha1: bool = False,
) -> JsonDict:
    required_fields = {
        "asset_id",
        "image_rel_path",
        "image_abs_path",
        "split",
        "subset",
        "sample_dir",
        "sample_id",
        "task_group_id",
        "width",
        "height",
        "annotation_abs_path",
        "text_abs_path",
        "file_size",
        "mtime",
        "sha1",
        "source_type",
    }

    dataset_root_path = Path(dataset_root).resolve() if dataset_root else None
    issues: list[JsonDict] = []
    asset_ids: set[str] = set()

    for record in records:
        missing_fields = sorted(required_fields - set(record.keys()))
        if missing_fields:
            issues.append(
                {
                    "asset_id": record.get("asset_id", ""),
                    "issue": "missing_fields",
                    "details": missing_fields,
                }
            )
            continue

        asset_id = record["asset_id"]
        if asset_id in asset_ids:
            issues.append({"asset_id": asset_id, "issue": "duplicate_asset_id", "details": ""})
        asset_ids.add(asset_id)

        image_path = Path(record["image_abs_path"])
        annotation_path = Path(record["annotation_abs_path"])
        text_path = Path(record["text_abs_path"])

        for field_name, field_path in (
            ("image_abs_path", image_path),
            ("annotation_abs_path", annotation_path),
            ("text_abs_path", text_path),
        ):
            if not field_path.exists():
                issues.append({"asset_id": asset_id, "issue": "missing_path", "details": field_name})

        if dataset_root_path is not None and image_path.exists():
            expected_rel_path = _normalize_rel_path(image_path, dataset_root_path)
            if record["image_rel_path"] != expected_rel_path:
                issues.append(
                    {
                        "asset_id": asset_id,
                        "issue": "image_rel_path_mismatch",
                        "details": expected_rel_path,
                    }
                )

        if image_path.exists():
            stat = image_path.stat()
            if int(record["file_size"]) != int(stat.st_size):
                issues.append({"asset_id": asset_id, "issue": "file_size_mismatch", "details": stat.st_size})
            if verify_sha1:
                actual_sha1 = _compute_sha1(image_path)
                if record["sha1"] != actual_sha1:
                    issues.append({"asset_id": asset_id, "issue": "sha1_mismatch", "details": actual_sha1})

    return {
        "total_records": len(records),
        "unique_asset_ids": len(asset_ids),
        "issue_count": len(issues),
        "issues": issues,
    }
