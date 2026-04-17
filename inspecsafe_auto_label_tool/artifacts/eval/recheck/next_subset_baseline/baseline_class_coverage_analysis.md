# next subset baseline class coverage analysis

- Sample count: `12`
- Task group IDs: `cigarette, head, phone, smog`
- GT classes: `Electrical Box, Fire Extinguisher, Fire Hydrant, Motor, Open Flame, Person, Pipeline, Pressure Gauge, Safety Helmet, Smoke, Valve`
- Baseline hit classes: `Electrical Box, Fire Extinguisher, Motor, Open Flame, Person, Safety Helmet, Smoke`
- Missed GT classes: `Fire Hydrant, Pipeline, Pressure Gauge, Valve`
- FP-only classes: `Direct-Blow Pipe, Electronic Control Cabinet, Ladder, Sight Hole Cover`

## Totals

- TP/FP/FN: `33/161/26`
- Precision/Recall/F1: `0.1701/0.5593/0.2609`
- Pred instances total: `194`
- Avg FP per image: `13.4167`

## Hardest miss classes

- `Fire Hydrant`: FN `6`, TP `0`, GT `6`
- `Valve`: FN `6`, TP `0`, GT `6`
- `Pipeline`: FN `4`, TP `0`, GT `4`
- `Pressure Gauge`: FN `3`, TP `0`, GT `3`
- `Safety Helmet`: FN `2`, TP `5`, GT `7`
- `Open Flame`: FN `2`, TP `1`, GT `3`
- `Smoke`: FN `2`, TP `1`, GT `3`
- `Fire Extinguisher`: FN `1`, TP `2`, GT `3`

## Highest-FP classes

- `Electronic Control Cabinet`: FP `24`, TP `0`, Pred `24`
- `Electrical Box`: FP `21`, TP `3`, Pred `24`
- `Pressure Gauge`: FP `17`, TP `0`, Pred `17`
- `Safety Helmet`: FP `15`, TP `5`, Pred `20`
- `Motor`: FP `13`, TP `3`, Pred `16`
- `Pipeline`: FP `13`, TP `0`, Pred `13`
- `Sight Hole Cover`: FP `12`, TP `0`, Pred `12`
- `Direct-Blow Pipe`: FP `11`, TP `0`, Pred `11`

## Assessment

- This subset is clearly better than subset3 for refinement generalization validation because GT coverage grows from 2 classes to 11 classes.
- It exposes multiple failure modes together: equipment confusion, PPE false positives, fire/smoke confusion, and measurement/pipeline misses.
