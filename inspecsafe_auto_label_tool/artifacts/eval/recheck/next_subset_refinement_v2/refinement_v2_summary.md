# refinement v2 summary

- Baseline TP/FP/FN: `33/161/26`
- Refinement v1 TP/FP/FN: `33/78/26`
- Refinement v2 TP/FP/FN: `36/75/23`
- Delta v2 vs baseline: `TP +3 / FP -86 / FN -3`
- Delta v2 vs v1: `TP +3 / FP -3 / FN -3`
- Baseline Precision/Recall/F1/AvgFP: `0.1701/0.5593/0.2609/13.4167`
- Refinement v1 Precision/Recall/F1/AvgFP: `0.2973/0.5593/0.3882/6.5000`
- Refinement v2 Precision/Recall/F1/AvgFP: `0.3243/0.6102/0.4235/6.2500`

## High-FN focus classes

- `Fire Hydrant`: baseline `0/4/6`, v1 `0/3/6`, v2 `3/0/3`
- `Valve`: baseline `0/8/6`, v1 `0/8/6`, v2 `0/8/6`
- `Pipeline`: baseline `0/13/4`, v1 `0/13/4`, v2 `0/13/4`
- `Pressure Gauge`: baseline `0/17/3`, v1 `0/17/3`, v2 `0/17/3`

## Coverage

- Baseline TP-hit classes: `Electrical Box, Fire Extinguisher, Motor, Open Flame, Person, Safety Helmet, Smoke`
- V1 TP-hit classes: `Electrical Box, Fire Extinguisher, Motor, Open Flame, Person, Safety Helmet, Smoke`
- V2 TP-hit classes: `Electrical Box, Fire Extinguisher, Fire Hydrant, Motor, Open Flame, Person, Safety Helmet, Smoke`
- New TP-hit classes in v2 vs baseline: `Fire Hydrant`
- Dropped TP-hit classes in v2 vs baseline: `none`
