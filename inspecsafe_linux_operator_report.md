# InspecSafe Linux 主线数据集算子报告

日期：2026-04-10

本文档用于说明当前项目在 Linux GPU 服务器主线下，如何理解“数据集算子”、为什么需要将其作为正式主路径推进，以及后续实现应遵守的输入输出协议与设计边界。

本文档面向两个用途：

- 供项目负责人快速阅读当前 Linux 主线的总体设计；
- 供 Linux 侧主会话或后续实现者参考具体的数据集算子规范。

## 一、当前项目状态与路线结论

本项目的核心目标，是围绕 `InspecSafe-V1` 数据集建立一套“模型初标 -> 人工交互 -> 结果回流”的智能标注闭环，而不是单独验证某个模型是否能跑通。

当前本地项目已经完成的基础工作包括：

- 已构建 canonical `asset_manifest.jsonl`；
- 已完成主索引校验，当前本地 `4957` 条资产记录无校验问题；
- 已实现从主索引导出 `Label Studio` 任务；
- 已实现预测结果导出为 `Label Studio` 预标注；
- 已实现 prediction/task/review 三类批次日志登记；
- 已完成 Colab 最小流程验证；
- 已补齐 Linux 主线计划、AutoDL 使用规范与默认推理配置骨架；
- 项目重心已转向 Linux GPU 服务器主线。

当前更合理的路线结论是：

- `asset_manifest` 继续作为全项目唯一资产事实源；
- `Label Studio` 继续作为人工交互平台；
- `GroundingDINO + SAM` 的正式自动预标注主线应转移到 Linux GPU 服务器；
- Colab 保留为历史验证与兼容路径，不再作为主开发和主演示路线。

## 二、为什么 Linux 成为主线

项目初期同时探索了 Colab 与 Linux 两条模型推理路线。Colab 的主要价值在于：

- 快速验证 `GroundingDINO + SAM` 组合是否可行；
- 低门槛完成最小样本跑通；
- 提供早期输出格式参考。

但从当前项目目标出发，Colab 不再适合作为正式主路径，主要原因包括：

- 会话和环境不稳定，通常需要反复执行 notebook；
- 往往依赖云盘挂载、外部网络和在线资源；
- 输出协议仍带有较强 notebook/实验性质；
- 对答辩实时演示和稳定运行服务不够友好。

相比之下，Linux 主线更适合作为正式推理后端，因为它更容易：

- 固化模型环境、权重和数据路径；
- 形成稳定的批量推理入口；
- 直接对接本地主索引和 `Label Studio` 流程；
- 满足答辩现场“可运行、可复现、可演示”的要求。

因此，Linux 主线的定位应明确为：

- 正式自动预标注执行后端；
- canonical prediction schema 的主要生产者；
- 智能标注闭环中的“模型推理算子集合”承载环境。

## 三、什么是 Linux 主线中的“数据集算子”

在 Linux 主线语境下，“数据集算子”不是若干零散脚本的统称，而是围绕同一批数据资产组织的一组标准化数据变换节点。

它们共同服务于如下闭环：

- 原始数据集；
- canonical 资产登记；
- 自动预标注推理；
- 预标注导入 `Label Studio`；
- 人工修订；
- 修订结果回流；
- 训练/评估导出。

因此，数据集算子的本质可以概括为：

- 以 `asset_id` 为稳定身份；
- 以 `asset_manifest` 为唯一事实源；
- 以 canonical schema 为协议中心；
- 以批次日志为治理和追踪手段；
- 将数据从一种“状态”推进到下一种“状态”。

换言之，本项目中的数据集算子，不是“模型代码本身”，而是让数据资产在闭环中稳定流动的标准处理单元。

## 四、Linux 主线的数据集算子分层

从总体设计上，Linux 主线的数据集算子建议分为三层。

### 1. 底座数据算子

职责：

- 数据资产化；
- 主索引校验；
- 任务切片；
- 批次组织。

特点：

- 平台无关；
- 不依赖具体模型；
- 决定整个系统的数据入口是否稳定。

### 2. 智能预标注算子

职责：

- `GroundingDINO` 开放词汇检测；
- `SAM` 分割或 polygon 生成；
- 标签映射；
- 标准预测结果生成。

特点：

- 是 Linux 主线的核心；
- 负责把资产数据转换成可交给人工审核的初始标注；
- 不应再输出实验性 raw 协议作为主路径结果。

### 3. 闭环治理算子

职责：

- 预测批次登记；
- 任务导出与任务批次登记；
- 人工回流批次登记；
- 训练导出与误差分析。

特点：

- 保证系统具有可追踪性和可复现性；
- 使项目从“模型跑通”升级为“数据生产闭环”。

## 五、Linux 主线必须遵守的协议原则

### 1. 身份协议

所有中间结果都必须围绕 `asset_id` 组织，不能依赖平台内部任务 ID。

每个资产的稳定身份字段至少包括：

- `asset_id`
- `image_rel_path`
- `split`
- `subset`
- `sample_id`
- `task_group_id`

其中建议继续沿用当前本地主索引规则：

- `asset_id = {split}:{sample_id}`
- `sample_id = image_path.stem`
- `task_group_id = sample_dir`
- `subset` 取 `Normal_data` 或 `Anomaly_data`

### 2. 事实源协议

`asset_manifest.jsonl` 是唯一资产事实源。

这意味着：

- 任务文件只是派生产物；
- 预测文件只是派生产物；
- `Label Studio` 导出文件只是派生产物；
- 任何派生文件都不能反向替代 `asset_manifest`。

### 3. 路径协议

Linux 主线不能把 Windows 绝对路径当作正式输入协议。

当前 `asset_manifest` 中虽然保留了 `image_abs_path` 等字段，但这些字段具有运行环境依赖性。对 Linux 主线而言，真正跨平台稳定的定位字段是：

- `image_rel_path`

因此 Linux 侧必须遵守：

- 优先使用 `dataset_root + image_rel_path` 解析图像；
- 不直接依赖 Windows 生成的 `image_abs_path`；
- 如需在 Linux 重新生成本地绝对路径，必须保证 `asset_id` 与 `image_rel_path` 保持不变。

### 4. 标签协议

Linux 主线的主输出必须直接对齐 canonical label，而不是 prompt label。

可以保留 raw prompt label 作为调试信息，但正式 `predictions.jsonl` 中的 `label` 必须与现有 schema 和 `Label Studio` 配置一致。

### 5. 几何协议

每条实例级预测至少应包含：

- `label`
- `score`
- `bbox`
- `polygon`

推荐约定如下：

- `bbox` 使用 `[x1, y1, x2, y2]`
- `polygon` 使用 `[[x, y], ...]`
- 若 `SAM` 成功输出 polygon，则优先保留 polygon；
- 若只有检测框，也允许保留 bbox，但后续导出时需可退化为矩形 polygon。

## 六、Linux 主线推荐算子清单

以下算子建议作为 Linux 主线路径的正式组成部分。

### 算子 1：资产清单构建算子

作用：

- 扫描数据集目录，构建 canonical `asset_manifest.jsonl`

输入：

- `dataset_root`

输出：

- `asset_manifest.jsonl`
- `index_summary.json`

要求：

- 只纳入 `.jpg/.json/.txt` 三元组完整样本；
- 固化 `asset_id`、`image_rel_path`、尺寸、校验信息等字段。

### 算子 2：资产校验算子

作用：

- 校验主索引的完整性、一致性与可用性

输入：

- `asset_manifest.jsonl`
- 可选 `dataset_root`

输出：

- `asset_manifest_validation.json`

要求：

- 校验字段完整性、路径存在性、唯一性、相对路径重建和可选哈希一致性。

### 算子 3：推理批次切片算子

作用：

- 从全量资产中切出一批送 Linux GPU 推理的资产子集

输入：

- `asset_manifest.jsonl`
- 过滤条件：`split`、`subset`、`task_group_id`、`asset_id`、`limit`

输出：

- `inference_manifest.jsonl` 或等价记录列表

要求：

- 不发明第二套索引逻辑；
- 切片结果仍保留主索引关键字段。

### 算子 4：GroundingDINO 检测算子

作用：

- 基于 prompt 生成候选目标框与分数

输入：

- 推理批次清单
- prompt 配置
- 检测阈值配置

输出：

- 原始检测结果

要求：

- 必须携带 `asset_id`；
- raw label 仅供中间调试使用。

### 算子 5：SAM 分割算子

作用：

- 基于候选框生成实例 polygon 或 mask

输入：

- 检测框
- 图像数据

输出：

- 带 polygon 的实例结果

要求：

- 结果仍保持与 `asset_id` 绑定；
- polygon 为主输出优先。

### 算子 6：预测规范化算子

作用：

- 将模型原始结果规范化为主链路可直接消费的 canonical prediction schema

输入：

- raw detection/segmentation records
- label schema
- `asset_manifest` 或推理切片清单

输出：

- `predictions.jsonl`

主输出记录至少包含：

- `asset_id`
- `image_path`
- `image_rel_path`
- `width`
- `height`
- `predictions`

要求：

- Linux 主线必须直接输出 canonical prediction schema；
- 不应继续依赖 Colab 兼容适配脚本作为主路径。

### 算子 7：预测结果校验算子

作用：

- 校验 `predictions.jsonl` 是否符合主链路协议

建议校验内容：

- `asset_id` 是否可回查到 manifest；
- label 是否属于 canonical schema；
- bbox/polygon 是否在图像尺寸范围内；
- 图像尺寸是否与资产记录一致。

说明：

- 当前代码库尚未显式实现，但非常适合作为 Linux 主线的新增治理算子。

### 算子 8：预测批次登记算子

作用：

- 将一次正式推理结果登记到 `prediction_manifest.jsonl`

输入：

- `prediction_run_id`
- `predictions.jsonl`
- `asset_manifest.jsonl`
- 模型与阈值版本信息

输出：

- 追加后的 `prediction_manifest.jsonl`

要求：

- 正式推理完成后应立刻登记，保证后续可追踪。

### 算子 9：预标注导出算子

作用：

- 将 canonical `predictions.jsonl` 转为 `Label Studio` 可导入的预标注格式

输入：

- `predictions.jsonl`
- `asset_manifest.jsonl`
- `document_root`
- `url_prefix`

输出：

- `predictions_label_studio.json`

说明：

- 该算子是模型输出与人机交互平台之间的转换层。

### 算子 10：任务与回流治理算子

作用：

- 从主索引导出平台任务；
- 登记任务批次；
- 登记人工回流批次；
- 为训练导出提供稳定输入。

说明：

- 这些算子可以继续在本地控制端执行；
- Linux 主线需要保证输出能够无缝接入这些既有治理流程。

## 七、当前代码库中的实现映射

为方便 Linux 主会话后续直接实现，当前代码库中已具备和待补齐的能力可以先映射如下。

### 1. 已具备的底座与治理算子

- 资产清单构建：
  - `inspecsafe_auto_label_tool/scripts/build_asset_manifest.py`
- 主索引校验：
  - `inspecsafe_auto_label_tool/scripts/validate_asset_manifest.py`
- 任务导出：
  - `inspecsafe_auto_label_tool/scripts/export_label_studio_tasks.py`
- 预测导出：
  - `inspecsafe_auto_label_tool/scripts/export_predictions.py`
- prediction 批次登记：
  - `inspecsafe_auto_label_tool/scripts/register_prediction_batch.py`
- task 批次登记：
  - `inspecsafe_auto_label_tool/scripts/register_task_batch.py`
- review 批次登记：
  - `inspecsafe_auto_label_tool/scripts/register_review_batch.py`

这些能力已经足够支撑 Linux 主线后续接入主索引、批次治理和 `Label Studio` 闭环。

### 2. 已具备的配置基础

- 标签 schema：
  - `inspecsafe_auto_label_tool/configs/label_schema.json`
- `Label Studio` 配置：
  - `inspecsafe_auto_label_tool/configs/label_studio_config.xml`
- Linux 默认推理配置骨架：
  - `inspecsafe_auto_label_tool/configs/linux_inference.default.json`

这意味着 Linux 主线后续应优先沿用现有配置体系，而不是把 prompt、标签映射和阈值继续散落在 notebook 或临时脚本中。

### 3. 当前仍缺失的关键算子

从 Linux 主线落地角度，当前最关键但尚未成形的部分主要有：

- 脚本化推理主入口
  - 例如 `run_linux_inference.py` 或等价脚本
- 推理批次切片算子
  - 显式按 `split / subset / task_group_id / asset_id / limit` 组织推理输入
- 预测结果校验算子
  - 在结果进入批次登记或平台导出前做协议检查

### 4. 历史兼容脚本的定位

- `inspecsafe_auto_label_tool/scripts/normalize_colab_predictions.py`

该脚本应明确视为 Colab 历史输出兼容工具，而不是 Linux 主线路径依赖。Linux 正式推理入口应直接生成 canonical `predictions.jsonl`。

## 八、Linux 主线与 Colab 路线的职责边界

为避免主链再次分叉，建议明确以下职责边界：

- Colab 只保留历史验证、原型实验和兼容调试价值；
- Linux 负责正式批量推理与 canonical prediction 输出；
- 主链路中的预测结果不再依赖 `normalize_colab_predictions.py` 进行补协议；
- 所有正式流程统一围绕 `asset_manifest` 和批次日志组织。

## 九、当前实施建议

从实现优先级看，Linux 主线建议按以下顺序推进：

1. 先统一 Linux 输入协议，明确以 `image_rel_path + dataset_root` 定位样本；
2. 让 Linux 推理端直接输出 canonical `predictions.jsonl`；
3. 增加预测结果校验算子，防止坏结果进入平台；
4. 再考虑是否封装成长驻服务或更复杂的在线推理模式；
5. 最后再扩展训练导出、多模态接入和误差分析能力。

## 十、相关文档

- Linux 路线计划：
  - `inspecsafe_auto_label_linux_plan.md`
- Linux 部署入口：
  - `inspecsafe_auto_label_tool/deploy/linux/README.md`
- AutoDL 使用规范：
  - `inspecsafe_auto_label_tool/deploy/linux/AUTODL_USAGE.md`
- Linux 默认推理配置：
  - `inspecsafe_auto_label_tool/configs/linux_inference.default.json`

## 十一、一句话总结

Linux 版本的数据集算子，不是将 Colab notebook 原样迁移到服务器，而是围绕 `asset_manifest` 这一唯一事实源，在 Linux 上建立一条能够直接输出 canonical predictions、并无缝接入 `Label Studio` 与回流治理体系的正式智能预标注主链。
