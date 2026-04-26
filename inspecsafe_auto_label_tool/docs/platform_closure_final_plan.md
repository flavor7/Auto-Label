# Platform Closure Final Plan

This document records the remote acceptance path for the human review loop.
The current priority is proving the platform loop works end to end on the
remote host, not improving model quality.

## Verified Remote Services

- Label Studio:
  - Remote bind: `127.0.0.1:6006`
  - Demo project id: `1`
  - Demo data dir: `artifacts/platform_closure_demo_20260426/label_studio_data`
  - Demo log: `artifacts/platform_closure_demo_20260426/logs/label_studio.log`
- Static image service:
  - Remote bind: `127.0.0.1:6008`
  - Document root: `/root/autodl-tmp/datasets/InspecSafe-V1/DATA_PATH`
  - Demo log: `artifacts/platform_closure_demo_20260426/logs/static_server.log`
- Required runtime notes:
  - Use conda env `inspecsafe-gpu`.
  - Set `DEBUG=false`; the host-level value `DEBUG=release` is not accepted by Label Studio.
  - Use `LABEL_STUDIO_LOCAL_FILES_SERVING_ENABLED=true`.
  - Use `LABEL_STUDIO_LOCAL_FILES_DOCUMENT_ROOT=/root/autodl-tmp`.

## Demo Batch

- Demo directory:
  - `artifacts/platform_closure_demo_20260426/`
- Demo size:
  - `3` tasks
- Demo assets:
  - `test:cigarette_frame_000009`
  - `test:cigarette_frame_000010`
  - `test:cigarette_frame_000011`
- Selection principle:
  - Use existing fixed 12-image subset material.
  - Keep the demo small enough for live acceptance.
  - Use assets with existing images and baseline predictions.

## Verified Loop

- Static image loading:
  - Verified with HTTP `200` on a demo image URL.
- Task import:
  - Source: `artifacts/platform_closure_demo_20260426/demo_tasks.json`
  - Imported task count: `3`
  - Note: task data must include `meta` because `configs/label_studio_config.xml` references `$meta`.
- Preannotation import:
  - Source: `artifacts/platform_closure_demo_20260426/demo_predictions_label_studio.json`
  - Imported prediction count: `3`
- Human annotation export:
  - Export: `artifacts/platform_closure_demo_20260426/label_studio_export.json`
  - Export contains `3` tasks, `3` annotations, and `3` predictions.
- Review conversion:
  - Script: `scripts/convert_label_studio_export_to_reviewed_annotations.py`
  - Output: `artifacts/platform_closure_demo_20260426/reviewed_annotations.jsonl`
  - Output contains `3` reviewed records and `9` polygon annotations.
- Review batch registration:
  - Script: `scripts/register_review_batch.py`
  - Manifest: `artifacts/index/review_manifest.jsonl`
  - Batch id: `review_platform_closure_demo_20260426`

## Conversion Contract

The current converter is intentionally minimal and acceptance-focused.

- Input:
  - Label Studio JSON export list.
  - Canonical `asset_manifest.jsonl`.
- Alignment key:
  - `data.asset_id`.
- Supported Label Studio result types:
  - `polygonlabels`
  - `rectanglelabels`
- Output:
  - JSONL, one reviewed record per Label Studio task.
  - Each record keeps asset metadata, Label Studio task / annotation ids,
    reviewed timestamp, converted annotations, pixel-space polygon, `bbox`
    as `[x1, y1, x2, y2]`, and `bbox_xywh`.

## Recommended Formal Demo Access

Use SSH tunnels instead of public port exposure:

```bash
ssh -L 6006:127.0.0.1:6006 -L 6008:127.0.0.1:6008 <remote>
```

Reasons:

- Keeps Label Studio credentials and API tokens off public network surfaces.
- Lets the browser load Label Studio and image URLs through the same verified
  local ports.
- Avoids copying large image files back to the local machine.

## Formal Demo Steps

1. Start or verify the remote static image service on `127.0.0.1:6008`.
2. Start or verify Label Studio on `127.0.0.1:6006`.
3. Create or reuse a Label Studio project with `configs/label_studio_config.xml`.
4. Import task JSON with `asset_id`, `image`, and `meta` fields.
5. Import model preannotations.
6. Review or modify annotations in Label Studio.
7. Export Label Studio JSON.
8. Convert export:

```bash
python scripts/convert_label_studio_export_to_reviewed_annotations.py \
  --input artifacts/platform_closure_demo_20260426/label_studio_export.json \
  --asset-manifest artifacts/index/asset_manifest.jsonl \
  --output artifacts/platform_closure_demo_20260426/reviewed_annotations.jsonl
```

9. Register review batch:

```bash
python scripts/register_review_batch.py \
  --review-batch-id review_platform_closure_demo_20260426 \
  --review-export-path artifacts/platform_closure_demo_20260426/reviewed_annotations.jsonl \
  --asset-manifest-path artifacts/index/asset_manifest.jsonl \
  --platform label_studio \
  --based-on-prediction-run-id baseline_demo_20260426 \
  --output artifacts/index/review_manifest.jsonl
```

## Current Closure Status

The remote platform loop is accepted for the demo scope:

- service startup: passed
- task import: passed
- preannotation import: passed
- annotation export: passed
- conversion to `reviewed_annotations.jsonl`: passed
- review batch registration: passed
