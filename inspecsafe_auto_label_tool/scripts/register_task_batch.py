import argparse
from datetime import datetime
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from inspecsafe_auto_label.indexing import append_jsonl, write_json
from inspecsafe_auto_label.types import TaskBatchRecord


def main() -> None:
    parser = argparse.ArgumentParser(description="Register one Label Studio task export batch.")
    parser.add_argument("--task-batch-id", required=True, help="Batch id, for example task_20260408_001.")
    parser.add_argument("--task-file-path", required=True, help="Exported task JSON file path.")
    parser.add_argument("--asset-manifest-path", required=True, help="Canonical asset manifest JSONL path.")
    parser.add_argument("--item-count", required=True, type=int, help="Number of tasks exported in this batch.")
    parser.add_argument("--platform", default="label_studio", help="Target annotation platform.")
    parser.add_argument("--image-url-mode", default="http", choices=("http", "local_files"))
    parser.add_argument("--split", default="", help="Optional split filter used for the export.")
    parser.add_argument("--subset", default="", help="Optional subset filter used for the export.")
    parser.add_argument("--task-group-id", default="", help="Optional task_group_id filter used for the export.")
    parser.add_argument("--asset-id", default="", help="Optional asset_id filter used for the export.")
    parser.add_argument(
        "--output",
        default="artifacts/index/task_manifest.jsonl",
        help="Task manifest JSONL path.",
    )
    parser.add_argument("--notes", default="", help="Optional notes.")
    args = parser.parse_args()

    record = TaskBatchRecord(
        task_batch_id=args.task_batch_id,
        platform=args.platform,
        task_file_path=str(Path(args.task_file_path).resolve()),
        asset_manifest_path=str(Path(args.asset_manifest_path).resolve()),
        item_count=args.item_count,
        created_at=datetime.now().isoformat(timespec="seconds"),
        image_url_mode=args.image_url_mode,
        split=args.split,
        subset=args.subset,
        task_group_id=args.task_group_id,
        asset_id=args.asset_id,
        notes=args.notes,
    )
    append_jsonl([record], args.output)
    print(f"Registered task batch: {args.task_batch_id}")
    print(f"Items: {args.item_count}")
    print(f"Manifest: {Path(args.output).resolve()}")


if __name__ == "__main__":
    main()
