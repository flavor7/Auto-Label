# subset3 class coverage analysis

- IoU threshold for TP/FN matching: `0.5`
- GT classes in subset3: `Person, Pipeline`
- Baseline TP-hit classes: `Person, Pipeline`
- Refinement v1 TP-hit classes: `Person, Pipeline`
- Classes dropped in v1 vs baseline: `none`
- Refinement v2 TP-hit classes: `Person, Pipeline`
- Classes dropped in v2 vs baseline: `none`

## Variant metrics

### baseline
- TP/FP/FN: `7/28/2`
- Precision/Recall/F1: `0.2000/0.7778/0.3182`
- Avg FP per image: `9.3333`

### refinement_v1
- TP/FP/FN: `7/1/2`
- Precision/Recall/F1: `0.8750/0.7778/0.8235`
- Avg FP per image: `0.3333`

### refinement_v2
- TP/FP/FN: `7/12/2`
- Precision/Recall/F1: `0.3684/0.7778/0.5000`
- Avg FP per image: `4.0000`

