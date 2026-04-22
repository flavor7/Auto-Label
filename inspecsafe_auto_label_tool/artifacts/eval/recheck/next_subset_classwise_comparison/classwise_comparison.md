# next subset classwise comparison

- IoU threshold: `0.5`
- Variants: `baseline`, `next_subset_refinement_v1`, `next_subset_refinement_v2`
- Baseline totals: `TP/FP/FN=33/161/26`
- V1 totals: `TP/FP/FN=33/78/26`
- V2 totals: `TP/FP/FN=36/75/23`

## Change Summary

- V1 mainly improved FP: `Safety Helmet, Motor, Electrical Box, Fire Hydrant, Electronic Control Cabinet, Fire Extinguisher, Ladder, Direct-Blow Pipe, Sight Hole Cover`
- V1 mainly improved FN: `none`
- V1 almost no change: `Pipeline, Person, Open Flame, Valve, Smoke, Pressure Gauge`
- V2 mainly improved FP: `Safety Helmet, Motor, Electrical Box, Electronic Control Cabinet, Fire Extinguisher, Ladder, Direct-Blow Pipe, Sight Hole Cover`
- V2 mainly improved FN: `Fire Hydrant`
- V2 almost no change: `Pipeline, Person, Open Flame, Valve, Smoke, Pressure Gauge`

## Class Table

| Class | GT | Base TP/FP/FN | Base P/R | V1 TP/FP/FN | V1 P/R | V2 TP/FP/FN | V2 P/R | Change vs baseline |
| --- | ---: | --- | --- | --- | --- | --- | --- | --- |
| Pipeline | 4 | 0/13/4 | 0.000/0.000 | 0/13/4 | 0.000/0.000 | 0/13/4 | 0.000/0.000 | V1: No material change; V2: No material change |
| Person | 18 | 18/1/0 | 0.947/1.000 | 18/1/0 | 0.947/1.000 | 18/1/0 | 0.947/1.000 | V1: No material change; V2: No material change |
| Safety Helmet | 7 | 5/15/2 | 0.250/0.714 | 5/10/2 | 0.333/0.714 | 5/10/2 | 0.333/0.714 | V1: FP improved; V2: FP improved |
| Motor | 3 | 3/13/0 | 0.188/1.000 | 3/5/0 | 0.375/1.000 | 3/5/0 | 0.375/1.000 | V1: FP improved; V2: FP improved |
| Electrical Box | 3 | 3/21/0 | 0.125/1.000 | 3/3/0 | 0.500/1.000 | 3/3/0 | 0.500/1.000 | V1: FP improved; V2: FP improved |
| Fire Hydrant | 6 | 0/4/6 | 0.000/0.000 | 0/3/6 | 0.000/0.000 | 3/0/3 | 1.000/0.500 | V1: FP improved; V2: FN improved, FP improved |
| Open Flame | 3 | 1/7/2 | 0.125/0.333 | 1/7/2 | 0.125/0.333 | 1/7/2 | 0.125/0.333 | V1: No material change; V2: No material change |
| Valve | 6 | 0/8/6 | 0.000/0.000 | 0/8/6 | 0.000/0.000 | 0/8/6 | 0.000/0.000 | V1: No material change; V2: No material change |
| Electronic Control Cabinet | 0 | 0/24/0 | 0.000/0.000 | 0/0/0 | 0.000/0.000 | 0/0/0 | 0.000/0.000 | V1: FP improved; V2: FP improved |
| Fire Extinguisher | 3 | 2/6/1 | 0.250/0.667 | 2/5/1 | 0.286/0.667 | 2/5/1 | 0.286/0.667 | V1: FP improved; V2: FP improved |
| Smoke | 3 | 1/6/2 | 0.143/0.333 | 1/6/2 | 0.143/0.333 | 1/6/2 | 0.143/0.333 | V1: No material change; V2: No material change |
| Pressure Gauge | 3 | 0/17/3 | 0.000/0.000 | 0/17/3 | 0.000/0.000 | 0/17/3 | 0.000/0.000 | V1: No material change; V2: No material change |
| Ladder | 0 | 0/3/0 | 0.000/0.000 | 0/0/0 | 0.000/0.000 | 0/0/0 | 0.000/0.000 | V1: FP improved; V2: FP improved |
| Direct-Blow Pipe | 0 | 0/11/0 | 0.000/0.000 | 0/0/0 | 0.000/0.000 | 0/0/0 | 0.000/0.000 | V1: FP improved; V2: FP improved |
| Sight Hole Cover | 0 | 0/12/0 | 0.000/0.000 | 0/0/0 | 0.000/0.000 | 0/0/0 | 0.000/0.000 | V1: FP improved; V2: FP improved |

## Notes

- `GT` is the GT instance count for the fixed 12-image subset.
- `pred_instances` and `pred_image_count` are included in the JSON/CSV for paper table extraction.
- `tp_hit_image_count` records how many images achieved at least one TP for the class.
