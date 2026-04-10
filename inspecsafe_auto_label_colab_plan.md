# InspecSafe Colab 路线计划

日期：2026-04-09

本文件仅覆盖 Colab 线路，不覆盖 Linux GPU 部署路线。

## 一、当前状态

- 当前 Colab 开发分支：`codex/colab-next`
- 当前 Colab 基线标签：`colab-baseline-20260409`
- 已验证基线笔记本：`inspecsafe_auto_label_tool/notebooks/inspecsafe_colab_bootstrap.ipynb`
- 已验证本地对接脚本：`inspecsafe_auto_label_tool/scripts/normalize_colab_predictions.py`
- Colab 侧已经验证通过的最小流程：
  - `GroundingDINO + SAM` 在 Google Colab GPU 环境可运行
  - 以 `test/Annotations` 为输入，5 张样本图推理成功
  - 导出成功：`predictions.jsonl`、`predictions_coco.json`、`failures.json`、`run_summary.json`
  - 已确认 `success_count=5`、`failure_count=0`、`prediction_count=36`

## 二、当前问题

当前 Colab 路线已经达到“能跑通”的阶段，但尚未完全接入本地主链路。

主要问题如下：

- Colab 导出的 `predictions.jsonl` 仍以 notebook 内部原始结构为主
- 导出记录主要依赖 `image_path`，不能直接稳定映射到本地主索引字段
- 导出标签仍然是 prompt 形式的小写标签，如 `person`、`open flame`
- 本地主链路和 Label Studio 配置使用的是 canonical label，如 `Person`、`Open Flame`
- 因此当前 Colab 输出仍需要本地执行 `normalize_colab_predictions.py`，才能完全进入 `export_predictions.py` 和批次登记流程

## 三、下一阶段目标

将 `inspecsafe_colab_bootstrap.ipynb` 从“能跑通”推进到“直接输出 canonical schema 并接本地主链路”。

具体目标：

- notebook 直接输出 `asset_id`
- notebook 直接输出 `image_rel_path`
- notebook 直接输出 canonical label，而不是原始 prompt label
- notebook 同时保留 raw 与 canonical 两套导出，兼顾调试与主链路接入
- 本地可直接消费 Colab 导出的 canonical `predictions.jsonl`，不再把 normalize 作为主路径必需步骤

## 四、实施步骤

### 1. 元数据生成

在收集图片阶段，不再只返回图片路径列表，而是为每张图生成完整 metadata：

- `asset_id`
- `image_path`
- `image_rel_path`
- `split`
- `subset`
- `sample_id`
- `task_group_id`
- `width`
- `height`

字段规则与本地主索引保持一致：

- `asset_id = {split}:{sample_id}`
- `sample_id = image_path.stem`
- `task_group_id = image_path.parent.name`
- `subset = image_path.parent.parent.name`
- `image_rel_path = image_path.relative_to(DATASET_ROOT).as_posix()`

### 2. 内置标签映射

在 notebook 中直接维护一份自包含的 label mapping，不依赖外部仓库配置文件。

本阶段只保留当前已经验证的 10 个类别，并将 prompt 映射到 canonical label：

- `person -> Person`
- `open flame -> Open Flame`
- `fire hydrant -> Fire Hydrant`
- `fire extinguisher -> Fire Extinguisher`
- `safety helmet -> Safety Helmet`
- `electrical box -> Electrical Box`
- `electronic control cabinet -> Electronic Control Cabinet`
- `pipeline -> Pipeline`
- `valve -> Valve`
- `pressure gauge -> Pressure Gauge`

推理时继续使用 prompt 列表，导出时统一写 canonical label。

### 3. 双轨输出

推理结果拆成两套记录：

- `raw_records`
  - 保留原始 prompt label，用于排错和回溯
- `records`
  - 使用 canonical label，并带完整 metadata，用于主链路对接

canonical 记录结构与本地 `normalize_colab_predictions.py` 输出对齐：

- `asset_id`
- `image_path`
- `image_rel_path`
- `width`
- `height`
- `predictions`

其中 `predictions` 中每条结果至少包含：

- `label`
- `score`
- `bbox`
- `polygon`

### 4. 导出调整

导出单元固定产出以下文件：

- `predictions_raw.jsonl`
- `predictions.jsonl`
- `predictions_coco.json`
- `failures.json`
- `run_summary.json`

约束如下：

- `predictions_raw.jsonl` 用于调试，保留 raw label
- `predictions.jsonl` 作为标准主输出，供本地 pipeline 直接消费
- `predictions_coco.json` 基于 canonical `records` 生成
- `run_summary.json` 需要明确记录当前输出模式为 `raw+canonical`

### 5. Notebook 结构整理

将以下配置集中到 notebook 配置单元中统一维护：

- `SPLIT`
- `MAX_IMAGES`
- `BOX_THRESHOLD`
- `TEXT_THRESHOLD`
- label mapping 配置
- Drive 输入输出路径

本阶段不处理：

- 扩展到 schema 全量 15 类
- 改造 `inspecsafe_colab_browser.ipynb`
- Linux GPU 服务器相关逻辑

## 五、验收标准

完成后需要满足以下标准：

- Colab 仍以 `MAX_IMAGES=5` 跑通最小回归
- 导出文件中同时存在 `predictions_raw.jsonl` 和 `predictions.jsonl`
- canonical `predictions.jsonl` 中包含：
  - `asset_id`
  - `image_rel_path`
  - canonical label
- 本地可以直接运行以下脚本消费 Colab 导出结果：
  - `python scripts/export_predictions.py --input <canonical_predictions.jsonl> --format label_studio ...`
  - `python scripts/register_prediction_batch.py --prediction-path <canonical_predictions.jsonl> ...`
- 在主路径验证中，不再需要先执行 `normalize_colab_predictions.py`

## 六、当前默认决策

- Colab 后续开发只在 `codex/colab-next` 上进行
- `main` 保持为冻结的 Colab 基线，不直接继续开发
- notebook 保持自包含，不依赖外部配置文件
- 先解决输出协议收敛，不优先扩大样本量
- raw 输出继续保留，canonical 输出作为主交付物
