# High-FN Root Cause Analysis

- Fixed subset input: `/root/autodl-tmp/inspecsafe/program_git/inspecsafe_auto_label_tool/artifacts/eval/recheck/next_subset_baseline/baseline_subset_predictions.jsonl`
- Compared variants: `baseline`, `refinement_v1`, `refinement_v2`

## Valve

- GT occurrences: `6`
- GT asset_ids: `test:phone_frame_000013, test:phone_frame_000014, test:phone_frame_000015`
- Baseline same-label candidates: `none`
- Typical confusion labels: `{}`
- Nearest wrong labels: `{"Person": 6}`
- Primary failure mode: `A. 候选缺失`
- Reason: Valve 在 baseline 里没有同类候选，也没有能与 GT 形成有效重叠的错类候选。

### Typical Failures

- `test:phone_frame_000013` GT=[1490.3548140475173, 582.5777568341682, 73.02944126138073, 68.16081184395523]
  same-label best: `none`
  wrong-label best: `Person score=0.8712 iou=0.0000`
- `test:phone_frame_000013` GT=[1704.574508414234, 628.8297362997093, 87.63532951365687, 77.08663244256854]
  same-label best: `none`
  wrong-label best: `Person score=0.8712 iou=0.0000`
- `test:phone_frame_000014` GT=[1490.3548140475173, 582.5777568341682, 73.02944126138073, 68.16081184395523]
  same-label best: `none`
  wrong-label best: `Person score=0.8241 iou=0.0000`
- `test:phone_frame_000014` GT=[1704.574508414234, 628.8297362997093, 87.63532951365687, 77.08663244256854]
  same-label best: `none`
  wrong-label best: `Person score=0.8241 iou=0.0000`
- `test:phone_frame_000015` GT=[1490.3548140475173, 582.5777568341682, 73.02944126138073, 68.16081184395523]
  same-label best: `none`
  wrong-label best: `Person score=0.8425 iou=0.0000`
- `test:phone_frame_000015` GT=[1704.574508414234, 628.8297362997093, 87.63532951365687, 77.08663244256854]
  same-label best: `none`
  wrong-label best: `Person score=0.8425 iou=0.0000`

## Pipeline

- GT occurrences: `4`
- GT asset_ids: `test:phone_frame_000013, test:phone_frame_000014, test:phone_frame_000015`
- Baseline same-label candidate score range: `0.3571 .. 0.3750`
- Best same-label IoU range: `0.0489 .. 0.2791`
- Best same-label candidate kept by v1/v2: `4 / 4`
- Typical confusion labels: `{}`
- Nearest wrong labels: `{"Electronic Control Cabinet": 3, "Person": 1}`
- Primary failure mode: `D. 几何位置偏差太大，无法命中`
- Reason: Pipeline 的同类候选存在且保留到了 v1/v2，但 IoU 长期停留在命中阈值以下，属于定位/尺度偏差主导。

### Typical Failures

- `test:phone_frame_000013` GT=[9.740698985343855, 3.652762119503946, 1900.6538895152198, 295.87373167981957]
  same-label best: `Pipeline score=0.3608 iou=0.2791 kept_v1=True kept_v2=True`
  wrong-label best: `Person score=0.8712 iou=0.0000`
- `test:phone_frame_000013` GT=[0.0, 152.19842164599774, 1910.3945885005637, 680.6313416009019]
  same-label best: `Pipeline score=0.3608 iou=0.0489 kept_v1=True kept_v2=True`
  wrong-label best: `Electronic Control Cabinet score=0.4278 iou=0.0628`
- `test:phone_frame_000014` GT=[1.2175873731679818, 6.087936865839909, 1911.6121758737315, 830.3945885005637]
  same-label best: `Pipeline score=0.3750 iou=0.0994 kept_v1=True kept_v2=True`
  wrong-label best: `Electronic Control Cabinet score=0.4063 iou=0.0519`
- `test:phone_frame_000015` GT=[7.305524239007891, 10.958286358511836, 1892.130777903044, 821.8714768883879]
  same-label best: `Pipeline score=0.3571 iou=0.1006 kept_v1=True kept_v2=True`
  wrong-label best: `Electronic Control Cabinet score=0.3851 iou=0.0529`

## Pressure Gauge

- GT occurrences: `3`
- GT asset_ids: `test:phone_frame_000013, test:phone_frame_000014, test:phone_frame_000015`
- Baseline same-label candidate score range: `0.4539 .. 0.5259`
- Best same-label IoU range: `0.0000 .. 0.0000`
- Best same-label candidate kept by v1/v2: `3 / 3`
- Typical confusion labels: `{}`
- Nearest wrong labels: `{"Electronic Control Cabinet": 1, "Motor": 1, "Person": 1}`
- Primary failure mode: `D. 几何位置偏差太大，无法命中`
- Reason: Pressure Gauge 的同类候选存在且保留到了 v1/v2，但与 GT 基本不重叠，说明是严重的几何偏差而不是规则过滤。

### Typical Failures

- `test:phone_frame_000013` GT=[927.1566316691662, 556.3804746153949, 114.98079807486283, 28.48148209193846]
  same-label best: `Pressure Gauge score=0.5259 iou=0.0000 kept_v1=True kept_v2=True`
  wrong-label best: `Person score=0.8712 iou=0.0000`
- `test:phone_frame_000014` GT=[927.1566316691662, 556.3804746153949, 114.98079807486283, 28.48148209193846]
  same-label best: `Pressure Gauge score=0.4675 iou=0.0000 kept_v1=True kept_v2=True`
  wrong-label best: `Electronic Control Cabinet score=0.4512 iou=0.0470`
- `test:phone_frame_000015` GT=[927.1566316691662, 556.3804746153949, 114.98079807486283, 28.48148209193846]
  same-label best: `Pressure Gauge score=0.4669 iou=0.0000 kept_v1=True kept_v2=True`
  wrong-label best: `Motor score=0.3938 iou=0.0458`

## Why Fire Hydrant Was Recoverable

- Fire Hydrant GT asset_ids: `test:head_frame_000009, test:head_frame_000010, test:head_frame_000011, test:smog_frame_000005, test:smog_frame_000007, test:smog_frame_000010`
- Primary pattern: `C. 类别混淆主导`
- Reason: Fire Hydrant 没有同类候选，但存在和 GT 明显重叠的错类候选，可视为稳定混淆。
- Key difference vs Valve/Pipeline/Pressure Gauge: Fire Hydrant had stable wrong-label overlap candidates that could be relabeled, while the other three either lacked candidates entirely or had same-label boxes with unusable geometry.

