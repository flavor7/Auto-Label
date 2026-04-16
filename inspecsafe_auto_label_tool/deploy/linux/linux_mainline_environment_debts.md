# Linux Mainline Environment Debts

日期：2026-04-15

本文档用于沉淀当前 InspecSafe Linux 主线已经验证可运行、但仍带有历史遗留依赖和特殊路径约束的环境事实。它不是业务逻辑设计文档，也不代表这些问题已经彻底收口；它只记录当前远端的可运行事实、已知环境债务，以及后续建议修复方向。

文档关系说明：本文件是“环境债务台账”，不替代 `../inspecsafe_auto_label_linux_plan.md` 的总计划职责，也不替代 `README.md` 的运行入口职责。

## 1. 当前远端双区结构

当前远端运行采用双区结构，而不是单一整洁工作区：

- Git 工作副本：`/root/autodl-tmp/inspecsafe/program_git`
- 旧资源区：`/root/autodl-tmp/inspecsafe/program/inspecsafe_auto_label_tool`

其中：

- `program_git` 是当前 Linux 主线继续推进的代码工作区
- 旧资源区不是当前长期开发目录，但仍承载若干已经验证可用的资源和编译产物

## 2. 当前 Linux 主线仍复用旧资源区的内容

当前 Linux baseline 已经验证可运行，但仍依赖旧资源区复用以下内容：

- GroundingDINO config
- GroundingDINO checkpoint
- SAM checkpoint
- 本地 `bert-base-uncased`
- GroundingDINO `_C` 扩展产物

当前已验证的旧资源区路径包括：

- GroundingDINO config：`/root/autodl-tmp/inspecsafe/program/inspecsafe_auto_label_tool/third_party/GroundingDINO/groundingdino/config/GroundingDINO_SwinT_OGC.py`
- GroundingDINO checkpoint：`/root/autodl-tmp/inspecsafe/program/inspecsafe_auto_label_tool/models/groundingdino_swint_ogc.pth`
- SAM checkpoint：`/root/autodl-tmp/inspecsafe/program/inspecsafe_auto_label_tool/models/sam_vit_b_01ec64.pth`
- 本地 BERT 目录：`/root/autodl-tmp/inspecsafe/program/inspecsafe_auto_label_tool/bert-base-uncased`
- GroundingDINO `_C` 扩展：`/root/autodl-tmp/inspecsafe/program/inspecsafe_auto_label_tool/third_party/GroundingDINO/groundingdino/_C.cpython-312-x86_64-linux-gnu.so`

## 3. 当前首个环境阻塞点：BERT 本地命中依赖实际工作目录

这轮 Linux 主线验证暴露出的首个阻塞点不是 `_C`，而是 `bert-base-uncased` 的离线命中条件。

已验证事实：

- 仅在 `program_git` 根下放同名路径并不足以稳定命中本地 BERT 目录
- 当前运行工作目录实际是：`/root/autodl-tmp/inspecsafe/program_git/inspecsafe_auto_label_tool`
- `deploy/linux/run_baseline.sh` 当前不会再显式切换到其他工作目录；它会在当前 shell 上下文中计算 `PROJECT_ROOT` / `CODE_ROOT`，然后直接执行 baseline Python 入口
- 因此，`AutoTokenizer.from_pretrained("bert-base-uncased")` 是否命中本地目录，实际会受到当前工作目录中是否存在同名路径影响

当前已验证可用的本地命中位置是：

- `/root/autodl-tmp/inspecsafe/program_git/inspecsafe_auto_label_tool/bert-base-uncased`

该路径当前应为同名软链接，指向：

- `/root/autodl-tmp/inspecsafe/program/inspecsafe_auto_label_tool/bert-base-uncased`

如果没有这个位置的同名映射，运行可能退回到把 `bert-base-uncased` 视为 Hugging Face 远端仓库名，并尝试访问：

- `https://huggingface.co/bert-base-uncased/...`

在 AutoDL 当前无外网或外网不可达时，这会直接成为 Linux baseline 的首个可见阻塞点。

## 4. `_C` 扩展的定位

GroundingDINO `_C` 扩展仍然是第二层环境前提，但在本轮验证中它不是首个阻塞点。

本轮已验证事实：

- `_C.cpython-312-x86_64-linux-gnu.so` 文件存在于旧资源区
- 在正确的 Python / torch 环境下，`import torch` 后再 `import groundingdino._C` 可以成功

因此，当前 `_C` 更适合作为启动前置自检项，而不是这轮 train smoke test 的首个根因。

## 5. 对 AutoDL 外网能力的口径

AutoDL 的 `network_turbo` 或其他临时网络能力可以作为 Hugging Face / GitHub 访问兜底，但它不应被视为 Linux baseline 主路径依赖。

当前主线路径应坚持：

- 模型和 tokenizer 优先命中本地已准备资源
- 不把“运行时临时联网下载”当成默认前提
- 避免把网络状态波动变成 baseline 成败条件

## 6. 当前已验证的最小运行事实

在当前双区结构和本地命中条件满足时，以下链路已经验证通过：

- `split=test limit=1`
- `split=test limit=3`
- `split=train limit=1`

其中 `split=train limit=1` 跑通前提之一，就是当前工作目录下存在可命中的 `bert-base-uncased` 同名路径：

- `/root/autodl-tmp/inspecsafe/program_git/inspecsafe_auto_label_tool/bert-base-uncased`

## 7. 后续建议修复方向

这些问题当前只做事实记录，不建议在未充分验证前直接做大迁移。后续建议按下面顺序逐步收口：

1. 启动脚本显式准备 BERT 本地命中
   - 当前 `run_baseline.sh` 已会准备 `program_git` 根级别的同名映射
   - 后续应把“实际运行工作目录的同名命中”显式化，而不是依赖隐式相对路径命中

2. 旧资源区依赖显式化 / 自检化
   - 在启动前统一检查 GroundingDINO config、checkpoint、SAM checkpoint、本地 BERT、`_C` 扩展是否齐全
   - 让缺失信息在启动前报清楚，而不是拖到模型初始化阶段

3. 保留当前双区结构，后续再做目录收口
   - 当前目标是保持 Linux 主线可重复执行
   - 不建议在这一阶段直接迁移旧资源区内容或重组目录
   - 后续如要收口，应先把依赖列表和自检逻辑固化，再计划单区迁移

## 8. 当前使用口径

后续会话如果继续 Linux 主线，应默认接受以下事实：

- Linux 正式主线继续在 `program_git` 推进
- baseline 当前可运行，但不是“零环境债务”状态
- 旧资源区仍是事实上的模型 / tokenizer / 自定义扩展复用来源
- BERT 本地命中问题已经验证可通过“实际工作目录同名软链接”绕开
- 这个绕开方案是当前可运行事实，不等同于最终结构性修复
