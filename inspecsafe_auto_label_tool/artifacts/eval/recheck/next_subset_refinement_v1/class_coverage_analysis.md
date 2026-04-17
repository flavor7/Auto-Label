# class coverage analysis

- IoU threshold for TP/FN matching: `0.5`
- GT classes in selected subset: `Electrical Box, Fire Extinguisher, Fire Hydrant, Motor, Open Flame, Person, Pipeline, Pressure Gauge, Safety Helmet, Smoke, Valve`
- Baseline TP-hit classes: `Electrical Box, Fire Extinguisher, Motor, Open Flame, Person, Safety Helmet, Smoke`
- Refinement v1 TP-hit classes: `Electrical Box, Fire Extinguisher, Motor, Open Flame, Person, Safety Helmet, Smoke`
- Classes dropped in v1 vs baseline: `none`

## Variant metrics

### baseline
- TP/FP/FN: `33/161/26`
- Precision/Recall/F1: `0.1701/0.5593/0.2609`
- Avg FP per image: `13.4167`

### refinement_v1
- TP/FP/FN: `33/78/26`
- Precision/Recall/F1: `0.2973/0.5593/0.3882`
- Avg FP per image: `6.5000`

