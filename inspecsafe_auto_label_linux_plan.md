# InspecSafe Linux GPU 路线计划

日期：2026-04-09

本文件仅覆盖 Linux GPU 部署路线，不覆盖 Colab 路线，也不替代 `inspecsafe_auto_label_colab_plan.md`。

## 一、当前状态

- 当前 Linux 工作区：`D:\HuaweiMoveData\Users\matebook14s\Desktop\program_linux`
- 当前 Linux 开发分支：`codex/linux-gpu-isolation`
- `main` / `origin/main` 已冻结为 Colab 基线：
  - commit：`0a3987f`
  - tag：`colab-baseline-20260409`
- Linux 部署入口已收敛到：
  - `inspecsafe_auto_label_tool/deploy/linux/README.md`
  - `inspecsafe_auto_label_tool/deploy/linux/setup_env.sh`
  - `inspecsafe_auto_label_tool/deploy/linux/start_stack.sh`
- 共享核心逻辑继续保留在：
  - `inspecsafe_auto_label_tool/src/`
  - `inspecsafe_auto_label_tool/configs/`
  - `inspecsafe_auto_label_tool/scripts/`
- 共享静态文件服务脚本继续使用：
  - `inspecsafe_auto_label_tool/scripts/run_static_server_with_cors.py`
- AutoDL 远端运行副本已重新按 Linux 独立工作区同步，且已确认存在 `deploy/linux/` 下三个入口文件
- AutoDL 远端已完成 shell 脚本换行修复：
  - `sed -i 's/\r$//' deploy/linux/setup_env.sh deploy/linux/start_stack.sh`
- 上一个待确认结果的远端命令为：

```bash
cd /root/autodl-tmp/inspecsafe/program/inspecsafe_auto_label_tool && export PYTHON_VERSION=3.10 && bash deploy/linux/setup_env.sh
```

## 二、当前问题

- Linux 路线此前曾与 Colab 路线共用工作区，导致远端副本混入两条线内容，虽然已经清理并重同步，但后续必须继续严格隔离
- Linux 专项计划文件此前缺失，导致当前分支目标、约束与验收口径没有独立文档承接
- AutoDL 环境安装流程虽然已有脚本，但还没有确认完整安装结果与第一轮 smoke test 结果
- 当前暂不传数据集，因此环境安装完成后只能先做依赖、GPU、服务脚本级别验证，完整业务闭环需要留到后续阶段
- 当前仓库中的部分说明仍带有 Colab / notebook 主入口痕迹，需要继续收敛到 Linux 脚本化主线
- Linux 侧尚未形成独立的脚本化推理入口与默认推理配置，当前闭环还停留在部署与导出骨架阶段
- 旧 Linux 入口仍然存在于仓库中，后续沟通与操作时需要避免重新回到旧路径：
  - `inspecsafe_auto_label_tool/docs/autodl_deploy.md`
  - `inspecsafe_auto_label_tool/scripts/setup_autodl_env.sh`
  - `inspecsafe_auto_label_tool/scripts/start_linux_stack.sh`

## 三、下一阶段目标

本阶段只推进 Linux GPU 路线，不改 Colab 主线。

目标按优先级排序如下：

1. 固化 Linux 与 Colab 的目录、分支和职责边界
2. 补齐 Linux 路线独立计划文件，明确当前状态与后续步骤
3. 在 AutoDL 上跑通 `deploy/linux/setup_env.sh`，确认 conda、PyTorch、CUDA 相关依赖可用
4. 将 Linux 主线进一步收敛为脚本化、参数化、可重复执行的运行方式，不再以 notebook 为中心
5. 复核 `deploy/linux/start_stack.sh` 的启动前提，确保后续拿到数据集后可直接启动 `Label Studio` 与静态文件服务
6. 在不引入 Colab 实验逻辑的前提下，形成 Linux 最小可运行闭环的执行清单

## 四、实施步骤

### 1. 固化工作区与分支边界

- Linux 线路后续所有代码修改只落在 `D:\HuaweiMoveData\Users\matebook14s\Desktop\program_linux`
- Linux 线路只在 `codex/linux-gpu-isolation` 上继续开发
- 不在 Linux 线程中操作 `D:\HuaweiMoveData\Users\matebook14s\Desktop\program`
- 不在 Linux 线路中改动 Colab 计划文件 `inspecsafe_auto_label_colab_plan.md`

### 2. 以 `deploy/linux/` 作为唯一主入口

- 文档入口固定为 `inspecsafe_auto_label_tool/deploy/linux/README.md`
- 环境安装入口固定为 `inspecsafe_auto_label_tool/deploy/linux/setup_env.sh`
- 服务启动入口固定为 `inspecsafe_auto_label_tool/deploy/linux/start_stack.sh`
- 后续若需要补充 Linux 文档或脚本，优先放在 `inspecsafe_auto_label_tool/deploy/linux/` 目录下，而不是继续扩散到旧脚本路径

### 3. 完成 AutoDL 环境安装

- 在 AutoDL 远端进入：

```bash
cd /root/autodl-tmp/inspecsafe/program/inspecsafe_auto_label_tool
```

- 显式指定 Python 版本并执行安装脚本：

```bash
export PYTHON_VERSION=3.10
bash deploy/linux/setup_env.sh
```

- 如安装成功，继续执行以下基础验证：

```bash
conda activate inspecsafe-gpu
python -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0))"
python -c "from groundingdino.util.inference import Model; print('GroundingDINO OK')"
python -c "from segment_anything import sam_model_registry; print('SAM OK')"
```

### 4. 为后续服务启动准备固定约定

- `DOCUMENT_ROOT` 默认使用 `/root/autodl-tmp/inspecsafe/program`
- `DATA_ROOT` 默认指向 `/root/autodl-tmp/inspecsafe/datasets/InspecSafe-V1/DATA_PATH`
- `LABEL_STUDIO_PORT` 默认使用 `6006`
- `STATIC_PORT` 默认使用 `6008`
- 启动入口统一通过 `deploy/linux/start_stack.sh`
- 在当前“先不传数据集”的阶段，不强行启动完整服务，只先保留启动参数与检查命令

### 5. 环境跑通后的最小闭环准备

- 待数据集同步后，再执行 `start_stack.sh`
- 先验证 `Label Studio`、静态文件服务、日志输出和本地文件映射是否正常
- 再补 Linux 独立推理入口与默认推理配置，目标是直接产出 canonical `predictions.jsonl`
- 推理链路应优先直接兼容 `scripts/register_prediction_batch.py` 与 `scripts/export_predictions.py`
- `scripts/normalize_colab_predictions.py` 仅保留为历史兼容脚本，不作为 Linux 主线路径依赖
- 再进入数据导入、预测导出、人工回流等业务链路验证
- 如后续需要远端持久化，优先规划 `/root/autodl-fs/inspecsafe`，避免重要输出只留在临时盘

## 五、验收标准

完成本阶段后，应满足以下条件：

- 当前 Linux 路线文档明确声明仅适用于 `codex/linux-gpu-isolation`
- Linux 线程后续不再使用旧 Linux 入口脚本作为主路径
- `deploy/linux/README.md`、`deploy/linux/setup_env.sh`、`deploy/linux/start_stack.sh` 三个入口文件可作为统一操作入口
- AutoDL 上 `inspecsafe-gpu` conda 环境创建成功
- AutoDL 上 `torch.cuda.is_available()` 返回 `True`
- AutoDL 上 `GroundingDINO` 与 `segment-anything` import 检查通过
- 在尚未同步数据集时，已明确后续启动命令、端口、目录与日志位置

## 六、默认决策与约束

- `program` 只服务 Colab 路线，`program_linux` 只服务 Linux GPU 路线
- 本地仓库是唯一真相源，AutoDL 服务器只是运行副本，不作为正式 git 主仓
- Linux 路线不在 `main` 上直接开发
- Linux 路线不把试验性 Colab notebook 改造混入主线部署目标
- `inspecsafe_auto_label_tool/notebooks/inspecsafe_colab_browser.ipynb` 视为实验性 notebook，默认不纳入 Linux 主线
- Linux 主线优先采用脚本化、配置驱动、可批次登记的运行方式
- `scripts/run_static_server_with_cors.py` 属于共享层，不迁入 Linux 私有目录
- 需要用户执行命令时，统一提供“可直接复制、一次一条”的命令
- 当前阶段先不传数据集，优先完成环境安装与部署骨架确认

## 七、相关文件

- Linux 计划文件：`D:\HuaweiMoveData\Users\matebook14s\Desktop\program_linux\inspecsafe_auto_label_linux_plan.md`
- 总计划文件：`D:\HuaweiMoveData\Users\matebook14s\Desktop\program_linux\inspecsafe_auto_label_plan.md`
- Colab 计划文件：`D:\HuaweiMoveData\Users\matebook14s\Desktop\program_linux\inspecsafe_auto_label_colab_plan.md`
- Linux 算子报告：`D:\HuaweiMoveData\Users\matebook14s\Desktop\program_linux\inspecsafe_linux_operator_report.md`
- AutoDL 使用规范：`D:\HuaweiMoveData\Users\matebook14s\Desktop\program_linux\inspecsafe_auto_label_tool\deploy\linux\AUTODL_USAGE.md`
- Linux 推理默认配置：`D:\HuaweiMoveData\Users\matebook14s\Desktop\program_linux\inspecsafe_auto_label_tool\configs\linux_inference.default.json`
- Linux 文档入口：`D:\HuaweiMoveData\Users\matebook14s\Desktop\program_linux\inspecsafe_auto_label_tool\deploy\linux\README.md`
- Linux 环境脚本：`D:\HuaweiMoveData\Users\matebook14s\Desktop\program_linux\inspecsafe_auto_label_tool\deploy\linux\setup_env.sh`
- Linux 启动脚本：`D:\HuaweiMoveData\Users\matebook14s\Desktop\program_linux\inspecsafe_auto_label_tool\deploy\linux\start_stack.sh`
