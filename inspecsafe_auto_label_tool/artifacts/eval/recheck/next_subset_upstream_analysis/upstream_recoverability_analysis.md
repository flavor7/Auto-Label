# Upstream Recoverability Analysis

- Root-cause input: `/root/autodl-tmp/inspecsafe/program_git/inspecsafe_auto_label_tool/artifacts/eval/recheck/next_subset_error_analysis/high_fn_root_cause_analysis.json`
- Fixed subset: `/root/autodl-tmp/inspecsafe/program_git/inspecsafe_auto_label_tool/artifacts/eval/recheck/next_subset_baseline/baseline_subset_predictions.jsonl`

## Valve

- GT occurrences: `6`
- GT asset_ids: `test:phone_frame_000013, test:phone_frame_000014, test:phone_frame_000015`
- Primary upstream issue: `candidate_generation_missing`
- Diagnosis: 候选生成缺失主导。没有同类候选，也没有与 GT 接近重叠的局部错类候选可直接复用。
- Still recoverable by lightweight rules: `False`
- Next direction: 检查小目标/部件级候选生成与召回，而不是继续放宽后处理规则。
- Nearby wrong labels: `{"Safety Helmet": 2}`
- Reusable nearby wrong candidate exists: `False`

## Pipeline

- GT occurrences: `4`
- GT asset_ids: `test:phone_frame_000013, test:phone_frame_000014, test:phone_frame_000015`
- Primary upstream issue: `localization_extent_quality`
- Diagnosis: 同类候选已经存在并保留到 v1/v2，但宽度和高度覆盖明显不足，属于大结构范围/extent 回归失败，不是规则过滤。
- Still recoverable by lightweight rules: `False`
- Next direction: 优先检查长条大结构目标的范围回归、截短现象和 coverage 表达。
- Score summary: `{"min": 0.35713738203048706, "median": 0.36077478528022766, "max": 0.3750176727771759}`
- IoU summary: `{"min": 0.04889817560596085, "median": 0.10000827495184819, "max": 0.27908678811448223}`
- Width ratio summary: `{"min": 0.48047682639533945, "median": 0.48177042540063053, "max": 0.485186148469433}`
- Height ratio summary: `{"min": 0.2069438977001725, "median": 0.22924587389362522, "max": 0.5778172986751976}`
- Center dx summary: `{"min": 224.23133696993682, "median": 228.0694621192563, "max": 230.4489110282201}`
- Center dy summary: `{"min": -351.7959947596811, "median": -280.95954678265593, "max": -10.87153027264614}`
- Geometry failure mode: `长条目标被截短 / 覆盖范围不足`

## Pressure Gauge

- GT occurrences: `3`
- GT asset_ids: `test:phone_frame_000013, test:phone_frame_000014, test:phone_frame_000015`
- Primary upstream issue: `localization_quality`
- Diagnosis: 同类候选存在且保留到了 v1/v2，但中心持续向下偏移约一百多像素，框高约为 GT 的 2.5 倍，说明是稳定误定位而不是规则过滤。
- Still recoverable by lightweight rules: `False`
- Next direction: 优先检查小部件定位和 bbox 回归，尤其是为什么候选持续落在更低、更高的邻近部件上。
- Score summary: `{"min": 0.4669444262981415, "median": 0.4675089120864868, "max": 0.5259183645248413}`
- IoU summary: `{"min": 0.0, "median": 0.0, "max": 0.0}`
- Width ratio summary: `{"min": 0.5842156699994286, "median": 0.5847709172625059, "max": 0.5851520525731075}`
- Height ratio summary: `{"min": 2.5017883002669747, "median": 2.5080415066613115, "max": 2.571229321515121}`
- Center dx summary: `{"min": -94.52325140972266, "median": -2.4134491636289113, "max": -2.2427338315976613}`
- Center dy summary: `{"min": 164.25738541285466, "median": 166.20245377222966, "max": 166.20941178004216}`
- Geometry failure mode: `误定位到下方附近部件，且尺度过高`

## Why Fire Hydrant Was Recoverable

- Recoverable path: `stable_wrong_label_overlap`
- Overlap wrong-label counts: `{"Electrical Box": 3}`
- Overlap IoU summary: `{"min": 0.5725223070012978, "median": 0.5769677708656294, "max": 0.5829929937310752}`
- Diagnosis: Fire Hydrant 没有同类候选，但存在可稳定重标的错类重叠候选，因此能通过轻量后处理救回一部分。

## Postprocess Boundary

- Still possibly recoverable by lightweight rules: `none`
- Clearly beyond lightweight postprocess: `Valve, Pipeline, Pressure Gauge`

## Priority Ranking

- 1. `Pressure Gauge`: 定位质量检查。同类候选已经稳定出现且分数不低，但在三张图上都以近乎相同的方式向下误定位，属于一致性很强、最适合先做上游定位调试的问题。
- 2. `Valve`: 候选生成缺失检查。当前既没有同类候选，也没有可直接重标的重叠错类候选，需要确认小部件级召回是否在候选生成阶段就缺失。
- 3. `Pipeline`: 大结构范围/extent 检查。问题更像长条大结构被系统性截短和覆盖不足，通常比局部定位/召回问题更重，更适合放在前两项之后处理。
