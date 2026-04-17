# refinement v1 summary

- Baseline TP/FP/FN: `33/161/26`
- Refinement v1 TP/FP/FN: `33/78/26`
- Delta TP/FP/FN: `0/-83/0`
- Baseline Precision/Recall/F1: `0.1701/0.5593/0.2609`
- Refinement v1 Precision/Recall/F1: `0.2973/0.5593/0.3882`
- Baseline Avg FP per image: `13.4167`
- Refinement v1 Avg FP per image: `6.5000`

## High-FP focus classes (baseline -> v1)

- `Electronic Control Cabinet`: FP `24 -> 0`, TP `0 -> 0`, FN `0 -> 0`
- `Electrical Box`: FP `21 -> 3`, TP `3 -> 3`, FN `0 -> 0`
- `Pressure Gauge`: FP `17 -> 17`, TP `0 -> 0`, FN `3 -> 3`
- `Safety Helmet`: FP `15 -> 10`, TP `5 -> 5`, FN `2 -> 2`
- `Motor`: FP `13 -> 5`, TP `3 -> 3`, FN `0 -> 0`
- `Direct-Blow Pipe`: FP `11 -> 0`, TP `0 -> 0`, FN `0 -> 0`
- `Ladder`: FP `3 -> 0`, TP `0 -> 0`, FN `0 -> 0`
- `Sight Hole Cover`: FP `12 -> 0`, TP `0 -> 0`, FN `0 -> 0`

## High-FN focus classes (baseline -> v1)

- `Fire Hydrant`: FN `6 -> 6`, TP `0 -> 0`, FP `4 -> 3`
- `Valve`: FN `6 -> 6`, TP `0 -> 0`, FP `8 -> 8`
- `Pipeline`: FN `4 -> 4`, TP `0 -> 0`, FP `13 -> 13`
- `Pressure Gauge`: FN `3 -> 3`, TP `0 -> 0`, FP `17 -> 17`

## GT-hit coverage

- Baseline TP-hit classes: `Electrical Box, Fire Extinguisher, Motor, Open Flame, Person, Safety Helmet, Smoke`
- Refinement v1 TP-hit classes: `Electrical Box, Fire Extinguisher, Motor, Open Flame, Person, Safety Helmet, Smoke`
- Dropped TP-hit classes: `none`
- New TP-hit classes: `none`
