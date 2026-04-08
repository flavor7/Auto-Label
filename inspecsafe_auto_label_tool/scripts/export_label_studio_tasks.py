import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from inspecsafe_auto_label.exporters import asset_records_to_label_studio_tasks, load_jsonl, write_json


def main() -> None:
    parser = argparse.ArgumentParser(description="Export canonical asset manifest JSONL to Label Studio task JSON.")
    parser.add_argument("--input", required=True, help="Image index JSONL path.")
    parser.add_argument("--output", required=True, help="Output Label Studio tasks JSON path.")
    parser.add_argument(
        "--document-root",
        required=True,
        help="Root directory allowed by LABEL_STUDIO_LOCAL_FILES_DOCUMENT_ROOT.",
    )
    parser.add_argument(
        "--url-prefix",
        default=None,
        help="Optional URL prefix for HTTP mode, for example http://127.0.0.1:9000 .",
    )
    parser.add_argument(
        "--url-root",
        default=None,
        help="Optional filesystem root for HTTP mode. Defaults to --document-root.",
    )
    parser.add_argument("--split", default=None, help="Optional split filter, for example test or train.")
    parser.add_argument("--subset", default=None, help="Optional subset filter, for example Normal_data.")
    parser.add_argument("--task-group-id", default=None, help="Optional task_group_id filter.")
    parser.add_argument("--asset-id", default=None, help="Optional asset_id filter.")
    parser.add_argument("--limit", type=int, default=None, help="Optional max task count.")
    args = parser.parse_args()

    records = []
    for record in load_jsonl(args.input):
        if args.split and record.get("split") != args.split:
            continue
        if args.subset and record.get("subset") != args.subset:
            continue
        if args.task_group_id and record.get("task_group_id") != args.task_group_id:
            continue
        if args.asset_id and record.get("asset_id") != args.asset_id:
            continue
        records.append(record)

        if args.limit is not None and len(records) >= args.limit:
            break

    tasks = asset_records_to_label_studio_tasks(
        records,
        document_root=args.document_root,
        url_prefix=args.url_prefix,
        url_root=args.url_root,
    )
    write_json(tasks, args.output)
    print(f"Exported {len(tasks)} tasks to {Path(args.output).resolve()}")


if __name__ == "__main__":
    main()
