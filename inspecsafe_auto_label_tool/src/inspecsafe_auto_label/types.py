from dataclasses import dataclass, field
from typing import Any, List, Optional


Point = List[float]
Polygon = List[Point]


@dataclass
class ImageRecord:
    image_path: str
    split: str
    subset: str
    sample_dir: str
    sample_id: str
    annotation_path: Optional[str] = None
    text_path: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None


@dataclass
class AssetRecord:
    asset_id: str
    image_rel_path: str
    image_abs_path: str
    split: str
    subset: str
    sample_dir: str
    sample_id: str
    task_group_id: str
    width: int
    height: int
    annotation_abs_path: str
    text_abs_path: str
    file_size: int
    mtime: float
    sha1: str
    source_type: str = "dataset_gt"


@dataclass
class InstancePrediction:
    label: str
    score: Optional[float]
    bbox: List[float]
    polygon: Polygon = field(default_factory=list)


@dataclass
class ImagePrediction:
    image_path: str
    width: int
    height: int
    predictions: List[InstancePrediction] = field(default_factory=list)
    asset_id: Optional[str] = None
    image_rel_path: Optional[str] = None


@dataclass
class PredictionBatchRecord:
    prediction_run_id: str
    prediction_path: str
    asset_manifest_path: str
    item_count: int
    model_name: str
    model_version: str
    prompt_version: str
    threshold_profile: str
    created_at: str
    notes: str = ""


@dataclass
class TaskBatchRecord:
    task_batch_id: str
    platform: str
    task_file_path: str
    asset_manifest_path: str
    item_count: int
    created_at: str
    image_url_mode: str
    split: str = ""
    subset: str = ""
    task_group_id: str = ""
    asset_id: str = ""
    notes: str = ""


@dataclass
class ReviewBatchRecord:
    review_batch_id: str
    platform: str
    review_export_path: str
    asset_manifest_path: str
    item_count: int
    updated_at: str
    based_on_prediction_run_id: str = ""
    notes: str = ""


ManifestRecord = AssetRecord | PredictionBatchRecord | TaskBatchRecord | ReviewBatchRecord
JsonDict = dict[str, Any]
