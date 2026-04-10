# AutoDL Usage Guide

日期：2026-04-10

本文档用于记录当前 InspecSafe Linux GPU 路线在 AutoDL 上的使用规范，适合后续会话直接查阅。

## 1. 使用定位

- AutoDL 仅作为 Linux GPU 运行副本，不作为正式 git 主仓
- 本地仓库是唯一真相源，Linux 线路固定使用：
  - `D:\HuaweiMoveData\Users\matebook14s\Desktop\program_linux`
- Linux 线路当前只在分支 `codex/linux-gpu-isolation` 上继续推进
- Colab 线路当前降级为历史验证参考，近期不作为主实现模板

## 2. 每日使用场景

当前默认工作方式：

- 工作时间开机 AutoDL 实例
- 下班后关机以节省成本
- 后续可能因为实例释放而更换实例

因此需要按以下原则使用：

- 接受“换实例后 SSH 连接信息可能变化”
- 接受“新实例可能需要重新核对环境或重新装环境”
- 不把重要结果只放在实例本地盘
- 一旦流程跑通，应尽快保存镜像或做等价备份

## 3. 目录规范

远端统一使用以下目录布局：

```text
/root/autodl-tmp/inspecsafe/
  program/
  datasets/
  outputs/
```

目录职责：

- `/root/autodl-tmp/inspecsafe/program`
  - 代码运行副本
- `/root/autodl-tmp/inspecsafe/datasets`
  - 数据集目录
- `/root/autodl-tmp/inspecsafe/outputs`
  - 推理输出、导出结果、日志汇总

如需额外持久化，优先考虑：

```text
/root/autodl-fs/inspecsafe/
```

## 4. 代码与分支规范

- Linux 线路只操作本地工作区 `program_linux`
- Linux 线程不要再操作 `D:\HuaweiMoveData\Users\matebook14s\Desktop\program`
- Linux 线路不在 `main` 上直接开发
- `main` 视为冻结基线
- AutoDL 上的改动不替代本地正式代码管理

## 5. Linux 主入口

远端操作统一以以下文件为主入口：

- `inspecsafe_auto_label_tool/deploy/linux/README.md`
- `inspecsafe_auto_label_tool/deploy/linux/setup_env.sh`
- `inspecsafe_auto_label_tool/deploy/linux/start_stack.sh`

不要再把以下旧路径作为主入口：

- `inspecsafe_auto_label_tool/docs/autodl_deploy.md`
- `inspecsafe_auto_label_tool/scripts/setup_autodl_env.sh`
- `inspecsafe_auto_label_tool/scripts/start_linux_stack.sh`

## 6. 每天开机后的标准检查

登录 AutoDL 后，按顺序检查：

```bash
hostname
```

```bash
nvidia-smi
```

```bash
python --version
```

```bash
conda env list
```

然后检查项目目录：

```bash
ls /root/autodl-tmp/inspecsafe
```

进入项目目录：

```bash
cd /root/autodl-tmp/inspecsafe/program/inspecsafe_auto_label_tool
```

## 7. 原实例与新实例的处理区别

### 7.1 如果还是原实例

- 一般环境和文件仍在
- 先激活环境并做最小验证：

```bash
conda activate inspecsafe-gpu
```

```bash
python -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```

通过后即可继续当天工作。

### 7.2 如果是新实例或环境丢失

按以下顺序处理：

1. 重新准备代码副本
2. 修复 shell 脚本换行
3. 重建或重装环境
4. 做核心依赖验证

推荐命令顺序：

```bash
cd /root/autodl-tmp/inspecsafe/program/inspecsafe_auto_label_tool
```

```bash
sed -i 's/\r$//' deploy/linux/setup_env.sh deploy/linux/start_stack.sh
```

```bash
export PYTHON_VERSION=3.10
```

```bash
bash deploy/linux/setup_env.sh
```

安装完成后执行：

```bash
conda activate inspecsafe-gpu
```

```bash
python -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```

```bash
python -c "from groundingdino.util.inference import Model; print('GroundingDINO OK')"
```

```bash
python -c "from segment_anything import sam_model_registry; print('SAM OK')"
```

## 8. 数据规范

- 当前阶段优先跑通环境与流程验证，不急于一次性同步完整数据集
- 后续如需同步数据集，默认目录为：
  - `/root/autodl-tmp/inspecsafe/datasets/InspecSafe-V1/DATA_PATH`
- 数据不要只保存在实例本地盘
- 重要数据应至少满足以下之一：
  - 本地有备份
  - 远端持久化目录有备份
  - 可从稳定来源重新获取

## 9. 输出与备份规范

以下结果不应只保留一份：

- 推理输出
- 批次登记结果
- Label Studio 导出结果
- 关键日志
- 修改过的配置文件

建议策略：

- 运行输出先写到 `/root/autodl-tmp/inspecsafe/outputs`
- 阶段性结果复制到 `/root/autodl-fs/inspecsafe`
- 关键结果再拉回本地保留

## 10. SSH 使用规范

- 使用统一 SSH 别名，例如：`autodl-inspecsafe`
- 一旦更换实例，优先更新本机 SSH 配置
- 后续命令尽量通过别名连接，避免混用旧地址

## 11. 服务启动规范

在未同步数据集前，不强行启动完整服务。

原因：

- `deploy/linux/start_stack.sh` 会检查 `DATA_ROOT` 是否存在
- 若数据目录不存在，脚本会直接失败

数据到位后，再按以下参数启动：

```bash
export ENV_NAME=inspecsafe-gpu
```

```bash
export DOCUMENT_ROOT=/root/autodl-tmp/inspecsafe/program
```

```bash
export DATA_ROOT=/root/autodl-tmp/inspecsafe/datasets/InspecSafe-V1/DATA_PATH
```

```bash
export LABEL_STUDIO_PORT=6006
```

```bash
export STATIC_PORT=6008
```

```bash
bash deploy/linux/start_stack.sh
```

## 12. 镜像与成本策略

当前阶段建议：

1. 先用临时实例完成 Linux 流程验证
2. 一旦环境安装和最小验证通过，尽快保存镜像
3. 再决定是否包周或包月

适用原因：

- 当前仍在验证阶段，先确认链路稳定性比提前锁长期机器更重要
- 如果镜像可复用，后续即使更换实例也能显著减少重复配置成本

## 13. 当前优先级

近期 Linux 线路优先级固定为：

1. Linux 与 Colab 继续隔离
2. Linux 主线以脚本化、参数化、可重复执行为准
3. AutoDL 上跑通 Linux 环境安装
4. 完成最小 smoke test
5. 之后再同步数据并推进闭环验证

## 14. 超短操作卡片

如只看最短版，请记住：

- 只认本地 `program_linux`
- Linux 只在 `codex/linux-gpu-isolation` 上改
- 远端固定目录：`program / datasets / outputs`
- 每天开机先查：`hostname`、`nvidia-smi`、`python --version`、`conda env list`
- 新实例先修换行，再跑 `deploy/linux/setup_env.sh`
- 装完先验：CUDA、GroundingDINO、SAM
- 重要输出别只放实例本地盘
- 跑通后尽快保存镜像
