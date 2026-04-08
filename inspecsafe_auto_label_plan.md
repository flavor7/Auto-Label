# InspecSafe 自动标注工具技术框架与实施计划

日期：2026-04-08

本文档基于当前工作区中的实际数据状态更新，目标是在 `InspecSafe-V1` 上建立一套“模型初标 -> 人工交互 -> 结果回流”的自动标注闭环。  
当前优先级仍然是先跑通 RGB 图像流程，但索引管理已升级为**无外部数据库的文件化主索引方案**。

## 一、当前数据状态

基于本地已解压数据的实测结果：

- RGB 图像总数：`4957`
- `train=3763`
- `test=1194`
- `train/Normal_data=3014`
- `train/Anomaly_data=749`
- `test/Normal_data=943`
- `test/Anomaly_data=251`
- 全量 `.jpg/.json/.txt` 三元组完整
- `sample_id` 在当前全量数据中全局唯一
- 共 `3187` 个 `task_group_id`
- 单个分组最多 `4` 帧

结论：

- 当前目录结构已经满足自动标注闭环的基础要求
- 现有 `image_index.jsonl` 只适合作为轻量导入清单
- 闭环管理必须以 `asset_manifest.jsonl` 作为事实源

## 二、项目目标

- 基于 `InspecSafe-V1` 构建一套可运行的自动标注流程
- 使用开源预训练模型自动生成目标标签与分割掩码
- 将模型初标导入 `Label Studio` 做人工审核与修订
- 将人工修订结果稳定回流，并用于训练导出与后续模型优化
- 全流程不依赖外部数据库，以文件化索引和批次日志管理

## 三、阶段性原则

- 第一阶段只覆盖 RGB 图像
- 第一阶段优先使用开源预训练模型，不做复杂微调
- 模型推理优先在 `Google Colab + GPU` 运行
- 本地重点负责主索引、平台导入、任务管理和回流整理
- 所有平台交互都依赖 `asset_id`，不依赖平台内部任务 ID

## 四、总体技术框架

### 1. 数据接入层

职责：

- 扫描 `DATA_PATH/train` 和 `DATA_PATH/test`
- 解析 `Annotations/Normal_data` 与 `Annotations/Anomaly_data`
- 为每张图建立稳定资产记录

输出：

- `asset_manifest.jsonl`
- `index_summary.json`
- 兼容旧流程的 `image_index.jsonl`

### 2. 文件化主索引层

采用“无外部数据库”的索引架构：

- `artifacts/index/asset_manifest.jsonl`
  唯一事实源，描述每张图像资产
- `artifacts/index/prediction_manifest.jsonl`
  记录每次模型初标批次
- `artifacts/index/task_manifest.jsonl`
  记录导入标注平台的任务批次
- `artifacts/index/review_manifest.jsonl`
  记录人工回流批次

说明：

- `asset_manifest.jsonl` 每次全量重建
- 其余三个 manifest 采用追加写入
- 派生导出文件不反向作为事实源

### 3. 主索引字段设计

每条 `asset_manifest` 记录固定包含：

- `asset_id`
  默认规则：`{split}:{sample_id}`
- `image_rel_path`
- `image_abs_path`
- `split`
- `subset`
- `sample_dir`
- `sample_id`
- `task_group_id`
  默认取 `sample_dir`
- `width`
- `height`
- `annotation_abs_path`
- `text_abs_path`
- `file_size`
- `mtime`
- `sha1`
- `source_type`
  当前默认：`dataset_gt`

### 4. 自动检测模块

职责：

- 使用 `GroundingDINO` 执行开放词汇目标检测
- 为每张图生成候选目标框、类别与置信度

建议：

- 使用类别提示词配置文件统一管理 prompt
- 对高风险类和小目标类单独维护阈值配置

### 5. 自动分割模块

职责：

- 使用 `SAM` 根据目标框生成实例分割掩码
- 输出 polygon 或 mask

建议：

- 保留 polygon 结果用于平台交互
- 低质量结果进入人工审核

### 6. 平台交互层

当前人工交互平台采用 `Label Studio`。

任务导出策略：

- 只从 `asset_manifest.jsonl` 派生任务
- 任务 `data` 固定携带：
  - `asset_id`
  - `image`
  - `split`
  - `subset`
  - `sample_id`
  - `task_group_id`

用途：

- 确保模型预测、人工修订、训练导出都能通过 `asset_id` 无歧义对齐

### 7. 回流层

人工修订后，不直接依赖平台内部任务 ID 做匹配。

回流策略：

- 以 `asset_id` 为唯一关联键
- 用 `review_manifest.jsonl` 登记每次人工回流批次
- 后续训练导出只读取：
  - `asset_manifest`
  - 已接受的人工作业回流
  - 指定版本的标签映射

## 五、推荐技术选型

### 核心模型

- 检测：`GroundingDINO`
- 分割：`Segment Anything Model (SAM)`
- 可选文本增强：`BLIP-2` 或 `Tag2Text`

### 支撑工具

- 索引与文件处理：`Python + JSONL`
- 图像处理：`OpenCV`
- 标注与可视化：`Label Studio`
- 评估与分析：`pycocotools`、`FiftyOne`

## 六、实施路径

### 第 1 步：构建 canonical asset manifest

目标：

- 从全量 `train + test` 建立主索引
- 固化 `asset_id`、`task_group_id` 和路径字段

当前状态：

- 已实现并完成本地验证

### 第 2 步：校验主索引

目标：

- 校验唯一性、路径存在性、字段完整性、哈希一致性

当前状态：

- 已实现并完成本地验证
- 当前 `4957` 条资产记录无校验问题

### 第 3 步：从主索引导出平台任务

目标：

- 由 `asset_manifest` 派生出 `Label Studio` 任务文件
- 不再依赖轻量 `image_index` 作为事实源

当前状态：

- 已实现

### 第 4 步：Colab 自动初标

目标：

- 使用 `GroundingDINO + SAM` 在 Colab 跑通自动初标
- 输出预测 JSONL

要求：

- 预测记录后续要能映射回 `asset_id`

### 第 5 步：登记模型初标批次

目标：

- 为每次预测运行生成 `prediction_run_id`
- 将预测文件登记到 `prediction_manifest.jsonl`

当前状态：

- 已实现批次登记脚本

### 第 6 步：导入平台并做人机交互

目标：

- 将任务文件导入 `Label Studio`
- 将预测结果导入为预标注
- 人工修订关键目标与低质量结果

### 第 7 步：登记人工回流批次

目标：

- 记录人工回流导出文件
- 维护 `review_manifest.jsonl`

当前状态：

- 已实现批次登记脚本

### 第 8 步：训练导出与后续优化

目标：

- 从主索引 + 回流结果生成训练用导出
- 为阈值调优、提示词优化和后续微调提供基础

## 七、输出物

- `asset_manifest.jsonl`
- `prediction_manifest.jsonl`
- `task_manifest.jsonl`
- `review_manifest.jsonl`
- `index_summary.json`
- `asset_manifest_validation.json`
- `Label Studio` 任务导出文件
- 预测预标注导出文件
- 后续训练导出文件

## 八、验收标准

- `asset_id` 在全量 `4957` 张图上全局唯一
- 全量 `.jpg/.json/.txt` 配对完整
- `image_rel_path` 可稳定重建平台导入 URL
- `task_group_id` 可稳定聚合同点位连续帧
- 可从主索引直接导出平台任务
- 可将模型预测导入为预标注
- 可将人工修订结果稳定回流
- 最终训练导出不依赖平台内部任务 ID

## 九、风险与应对

### 1. 继续依赖轻量索引导致闭环不稳

应对：

- 轻量索引只保留为兼容导出
- 所有正式流程统一切换到 `asset_manifest`

### 2. 平台任务与模型预测错位

应对：

- 所有中间文件都携带 `asset_id`
- 不再依赖平台内部任务 ID

### 3. 文件移动或重命名后路径漂移

应对：

- 保留 `image_rel_path` 和 `sha1`
- 通过校验脚本做漂移检测

### 4. 后续需要更复杂查询

应对：

- 仍保留 JSONL 为事实源
- 仅在需要时增加本地只读缓存层，如 SQLite 或 Parquet

## 十、后续扩展方向

- 将红外、多模态数据纳入主索引扩展字段
- 为预测结果增加更细粒度的评估与误差分析
- 从人工回流中自动筛选高价值样本用于微调
- 建立适用于具身智能工厂巡检的数据生产闭环
