# screenshot candidates

Canonical comparison inputs:

- `baseline`: `/root/autodl-tmp/inspecsafe/program_git/inspecsafe_auto_label_tool/artifacts/eval/recheck/next_subset_baseline/baseline_subset_predictions.jsonl`
- `v1`: `/root/autodl-tmp/inspecsafe/program_git/inspecsafe_auto_label_tool/artifacts/eval/recheck/next_subset_refinement_v1/refined_predictions.jsonl`
- `v2`: `/root/autodl-tmp/inspecsafe/program_git/inspecsafe_auto_label_tool/artifacts/eval/recheck/next_subset_refinement_v2/refined_predictions.jsonl`
- Classwise reference: `/root/autodl-tmp/inspecsafe/program_git/inspecsafe_auto_label_tool/artifacts/eval/recheck/next_subset_classwise_comparison/classwise_comparison.json`
- High-FN root cause reference: `/root/autodl-tmp/inspecsafe/program_git/inspecsafe_auto_label_tool/artifacts/eval/recheck/next_subset_error_analysis/high_fn_root_cause_analysis.json`
- Upstream recoverability reference: `/root/autodl-tmp/inspecsafe/program_git/inspecsafe_auto_label_tool/artifacts/eval/recheck/next_subset_upstream_analysis/upstream_recoverability_analysis.json`

## Primary candidates

### 1. `test:smog_frame_000007`

- Recommended comparison: `baseline vs v1 vs v2`
- Best conclusion to show:
  - `v1` has already removed a large block of high-FP noise.
  - `v2` then newly recovers `Fire Hydrant` without giving those FP boxes back.
  - Asset-level totals move from `2/14/2` in baseline to `2/6/2` in `v1`, then to `3/6/1` in `v2`.
- Why this is strong:
  - It is the cleanest single-image story for the retained pipeline: first suppress noise, then selectively add a truly useful recovery.
  - `Fire Hydrant` is the only high-FN class that was actually recovered by `v2`, so this is the key positive sample for the paper正文.
- Use recommendation:
  - Paper正文 priority: high
  - 答辩展示 priority: high

### 2. `test:cigarette_frame_000009`

- Recommended comparison: `baseline vs v1`, with optional `v2` appended as the retained final version
- Best conclusion to show:
  - High-FP suppression is real and does not rely on deleting true positives.
  - Asset-level totals move from `4/15/0` in baseline to `4/7/0` in `v1`, then to `4/6/0` in `v2`.
  - The image keeps all GT-hit classes while removing typical clutter from `Electronic Control Cabinet`, `Direct-Blow Pipe`, `Sight Hole Cover`, plus extra false boxes on `Safety Helmet` and `Motor`.
- Why this is strong:
  - It is visually simpler than the head/smog images, so readers can see the FP cleanup effect quickly.
  - It supports the claim that classwise refinement improves precision without sacrificing coverage.
- Use recommendation:
  - Paper正文 priority: high
  - 答辩展示 priority: medium

### 3. `test:phone_frame_000013`

- Recommended comparison: `baseline vs v1 vs v2`
- Best conclusion to show:
  - This is the clearest negative/control sample proving that post-processing has limits.
  - `v1` and `v2` remove some unrelated FP clutter, but the hard classes remain unresolved.
  - Asset-level totals move from `2/10/5` in baseline to `2/3/5` in `v1`, and stay `2/3/5` in `v2`.
  - `Valve` still has no usable same-class candidate, `Pipeline` remains too short / under-covered, and `Pressure Gauge` stays stably mislocalized downward.
- Why this is strong:
  - One image simultaneously carries the three unresolved high-FN classes: `Valve`, `Pipeline`, `Pressure Gauge`.
  - It directly supports the stage conclusion that the next step must move upstream to candidate generation / localization quality.
- Use recommendation:
  - Paper正文 priority: high
  - 答辩展示 priority: high

## Secondary backups

### `test:smog_frame_000010`

- Similar to `smog_frame_000007`, but also keeps a correct `Open Flame` TP while `Fire Hydrant` is added in `v2`.
- Better for答辩 if a second positive recovery sample is needed.

### `test:head_frame_000009`

- Strongest single-image FP drop by count: asset-level FP goes from `19` to `7`.
- Better for答辩 than paper正文, because the frame is visually noisy and the “suppression before/after” effect is dramatic, but the story is less clean than the cigarette sample.

## Minimal screenshot preparation notes

- Preferred render mode:
  - one original image
  - three overlays for `baseline / v1 / v2`
  - for `phone_frame_000013`, add one tight crop around the equipment region if the full image is too wide
- Caption framing:
  - `smog_frame_000007`: `v2` recovers `Fire Hydrant` after `v1` has already removed most noise
  - `cigarette_frame_000009`: classwise FP suppression preserves all true-positive hits
  - `phone_frame_000013`: remaining failure is upstream candidate/localization quality, not post-processing thresholding
