import argparse
from datetime import datetime
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from inspecsafe_auto_label.indexing import append_jsonl, load_jsonl
from inspecsafe_auto_label.types import PredictionBatchRecord


def main() -> None:
    parser = argparse.ArgumentParser(description="Register one prediction batch in prediction_manifest.jsonl.")
    parser.add_argument("--prediction-run-id", required=True, help="Batch id, for example pred_20260408_001.")
    parser.add_argument("--prediction-path", required=True, help="Prediction JSONL path produced by model inference.")
    parser.add_argument("--asset-manifest-path", required=True, help="Canonical asset manifest JSONL path.")
    parser.add_argument("--model-name", required=True, help="Model name, for example groundingdino+sam.")
    parser.add_argument("--model-version", default="unknown", help="Model version or checkpoint tag.")
    parser.add_argument("--prompt-version", default="unknown", help="Prompt configuration version.")
    parser.add_argument("--threshold-profile", default="default", help="Threshold profile name.")
    parser.add_argument(
        "--output",
        default="artifacts/index/prediction_manifest.jsonl",
        help="Prediction manifest JSONL path.",
    )
    parser.add_argument("--notes", default="", help="Optional free-form notes.")
    args = parser.parse_args()

    item_count = len(load_jsonl(args.prediction_path))
    record = PredictionBatchRecord(
        prediction_run_id=args.prediction_run_id,
        prediction_path=str(Path(args.prediction_path).resolve()),
        asset_manifest_path=str(Path(args.asset_manifest_path).resolve()),
        item_count=item_count,
        model_name=args.model_name,
        model_version=args.model_version,
        prompt_version=args.prompt_version,
        threshold_profile=args.threshold_profile,
        created_at=datetime.now().isoformat(timespec="seconds"),
        notes=args.notes,
    )
    append_jsonl([record], args.output)
    print(f"Registered prediction batch: {args.prediction_run_id}")
    print(f"Items: {item_count}")
    print(f"Manifest: {Path(args.output).resolve()}")


if __name__ == "__main__":
    main()
