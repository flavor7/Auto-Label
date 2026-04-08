# Label Studio 本地接入说明

当前推荐使用：

- `Label Studio` 做人工交互
- `asset_manifest.jsonl` 做任务事实源
- `HTTP 静态服务` 提供图像

不再把 `Label Studio` 任务 JSON 当作主索引。

## 1. 启动服务

推荐直接使用一键脚本：

```cmd
cd D:\HuaweiMoveData\Users\matebook14s\Desktop\program\inspecsafe_auto_label_tool
scripts\start_local_stack.cmd
```

它会启动：

- `Label Studio`：`http://127.0.0.1:8080`
- 静态图像服务：`http://127.0.0.1:9000`

停止：

```cmd
scripts\stop_local_stack.cmd
```

## 2. 构建主索引

```powershell
python scripts/build_asset_manifest.py `
  --dataset-root ..\datasets\InspecSafe-V1\DATA_PATH `
  --output .\artifacts\index\asset_manifest.jsonl `
  --summary-output .\artifacts\reports\index_summary.json
```

## 3. 创建项目

在 Label Studio 新建项目时，使用：

- `configs/label_studio_config.xml`

## 4. 导出任务

从主索引直接导出任务，不再从 `image_index.jsonl` 导出：

```powershell
python scripts/export_label_studio_tasks.py `
  --input .\artifacts\index\asset_manifest.jsonl `
  --output .\artifacts\exports\label_studio_tasks_test_http.json `
  --document-root D:\HuaweiMoveData\Users\matebook14s\Desktop\program\datasets\InspecSafe-V1\DATA_PATH `
  --url-prefix http://127.0.0.1:9000 `
  --split test `
  --limit 50
```

当前只允许这些筛选条件：

- `split`
- `subset`
- `task_group_id`
- `asset_id`
- `limit`

这样可以避免任务导出脚本重新发明第二套索引逻辑。

## 5. 任务字段

导入到 Label Studio 的每条任务固定带：

- `asset_id`
- `image`
- `split`
- `subset`
- `sample_id`
- `task_group_id`

后续人工回流必须靠 `asset_id` 对齐，不依赖 Label Studio 自己生成的任务 ID。

## 6. 预标注导入

如果已有模型预测结果：

```powershell
python scripts/export_predictions.py `
  --input .\artifacts\predictions.jsonl `
  --format label_studio `
  --asset-manifest .\artifacts\index\asset_manifest.jsonl `
  --document-root D:\HuaweiMoveData\Users\matebook14s\Desktop\program\datasets\InspecSafe-V1\DATA_PATH `
  --url-prefix http://127.0.0.1:9000 `
  --output .\artifacts\exports\predictions_label_studio.json
```

## 7. 批次登记

完成一次任务导出后，建议立刻登记批次：

```powershell
python scripts/register_task_batch.py `
  --task-batch-id task_20260408_001 `
  --task-file-path .\artifacts\exports\label_studio_tasks_test_http.json `
  --asset-manifest-path .\artifacts\index\asset_manifest.jsonl `
  --item-count 50 `
  --image-url-mode http `
  --split test
```

这样后续可以追踪：

- 哪批资产被导进过平台
- 对应哪个任务文件
- 是哪次人工修订的输入
