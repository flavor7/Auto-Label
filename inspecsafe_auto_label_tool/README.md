# InspecSafe Auto Label Tool

本工具目前采用“无外部数据库”的索引管理方案：

- `asset_manifest.jsonl` 作为唯一事实源
- `prediction_manifest.jsonl` / `task_manifest.jsonl` / `review_manifest.jsonl` 作为批次日志
- `Label Studio`、预测预标注、训练导出都从主索引派生

当前已基于本地数据验证：

- 总图像数：`4957`
- `train=3763`
- `test=1194`
- 全量 `.jpg/.json/.txt` 三元组完整
- `asset_id={split}:{sample_id}` 全局唯一

## 目录结构

```text
inspecsafe_auto_label_tool/
  artifacts/
    index/
    exports/
    reports/
  configs/
  docs/
  notebooks/
  scripts/
  src/
```

## 核心文件

- `artifacts/index/asset_manifest.jsonl`
- `artifacts/index/prediction_manifest.jsonl`
- `artifacts/index/task_manifest.jsonl`
- `artifacts/index/review_manifest.jsonl`

## 常用命令

### 1. 构建主索引

```powershell
python scripts/build_asset_manifest.py `
  --dataset-root ..\datasets\InspecSafe-V1\DATA_PATH `
  --output .\artifacts\index\asset_manifest.jsonl `
  --summary-output .\artifacts\reports\index_summary.json
```

### 2. 校验主索引

```powershell
python scripts/validate_asset_manifest.py `
  --input .\artifacts\index\asset_manifest.jsonl `
  --dataset-root ..\datasets\InspecSafe-V1\DATA_PATH `
  --report-output .\artifacts\reports\asset_manifest_validation.json
```

### 3. 兼容导出旧版 image index

```powershell
python scripts/build_index.py `
  --dataset-root ..\datasets\InspecSafe-V1\DATA_PATH `
  --output .\artifacts\image_index.jsonl `
  --summary-output .\artifacts\image_index_summary.json
```

### 4. 从主索引导出 Label Studio 任务

HTTP 静态服务模式：

```powershell
python scripts/export_label_studio_tasks.py `
  --input .\artifacts\index\asset_manifest.jsonl `
  --output .\artifacts\exports\label_studio_tasks_test_http.json `
  --document-root D:\HuaweiMoveData\Users\matebook14s\Desktop\program\datasets\InspecSafe-V1\DATA_PATH `
  --url-prefix http://127.0.0.1:9000 `
  --split test `
  --limit 50
```

导出的任务 `data` 固定携带：

- `asset_id`
- `image`
- `split`
- `subset`
- `sample_id`
- `task_group_id`

### 5. 导出模型预测为 Label Studio 预标注

```powershell
python scripts/export_predictions.py `
  --input .\artifacts\predictions.jsonl `
  --format label_studio `
  --asset-manifest .\artifacts\index\asset_manifest.jsonl `
  --document-root D:\HuaweiMoveData\Users\matebook14s\Desktop\program\datasets\InspecSafe-V1\DATA_PATH `
  --url-prefix http://127.0.0.1:9000 `
  --output .\artifacts\exports\predictions_label_studio.json
```

### 6. 登记批次日志

登记模型预测批次：

```powershell
python scripts/register_prediction_batch.py `
  --prediction-run-id pred_20260408_001 `
  --prediction-path .\artifacts\predictions.jsonl `
  --asset-manifest-path .\artifacts\index\asset_manifest.jsonl `
  --model-name groundingdino+sam
```

登记 Label Studio 任务导出批次：

```powershell
python scripts/register_task_batch.py `
  --task-batch-id task_20260408_001 `
  --task-file-path .\artifacts\exports\label_studio_tasks_test_http.json `
  --asset-manifest-path .\artifacts\index\asset_manifest.jsonl `
  --item-count 50 `
  --image-url-mode http `
  --split test
```

登记人工回流批次：

```powershell
python scripts/register_review_batch.py `
  --review-batch-id review_20260408_001 `
  --review-export-path .\artifacts\reviewed_annotations.jsonl `
  --asset-manifest-path .\artifacts\index\asset_manifest.jsonl `
  --platform label_studio
```

## 设计原则

- 主索引全量重建，不做在线随机写
- 批次日志追加写入，不覆盖旧记录
- 派生导出不反向作为事实源
- 所有平台交互靠 `asset_id` 对齐，不依赖平台内部任务 ID
