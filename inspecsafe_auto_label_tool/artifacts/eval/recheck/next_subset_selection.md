# next subset selection

- Sample count: `12`
- Task group IDs: `cigarette, head, phone, smog`
- GT classes: `Electrical Box, Fire Extinguisher, Fire Hydrant, Motor, Open Flame, Person, Pipeline, Pressure Gauge, Safety Helmet, Smoke, Valve`

## Asset IDs

- `test:cigarette_frame_000009`
- `test:cigarette_frame_000010`
- `test:cigarette_frame_000011`
- `test:head_frame_000009`
- `test:head_frame_000010`
- `test:head_frame_000011`
- `test:phone_frame_000013`
- `test:phone_frame_000014`
- `test:phone_frame_000015`
- `test:smog_frame_000005`
- `test:smog_frame_000007`
- `test:smog_frame_000010`

## GT class presence

- `Electrical Box`: appears in `3` images / `3` GT instances
- `Fire Extinguisher`: appears in `3` images / `3` GT instances
- `Fire Hydrant`: appears in `6` images / `6` GT instances
- `Motor`: appears in `3` images / `3` GT instances
- `Open Flame`: appears in `3` images / `3` GT instances
- `Person`: appears in `12` images / `18` GT instances
- `Pipeline`: appears in `3` images / `4` GT instances
- `Pressure Gauge`: appears in `3` images / `3` GT instances
- `Safety Helmet`: appears in `6` images / `7` GT instances
- `Smoke`: appears in `3` images / `3` GT instances
- `Valve`: appears in `3` images / `6` GT instances

## Why this subset is better than subset3

- `subset3` only had `Person` and `Pipeline`, so it was too narrow for class-generalization checks.
- This subset covers 11 GT classes across 4 logical task groups: `cigarette`, `head`, `phone`, `smog`.
- It includes equipment classes (`Electrical Box`, `Motor`, `Pressure Gauge`, `Valve`, `Pipeline`), PPE classes (`Safety Helmet`), human class (`Person`), and anomaly/safety classes (`Fire Extinguisher`, `Fire Hydrant`, `Open Flame`, `Smoke`).
- The sample count stays at 12, which is still small enough for repeated baseline/refinement verification.

## Per-image GT classes

- `cigarette_frame_000009` (`cigarette`): `Electrical Box, Motor, Person, Safety Helmet`
- `cigarette_frame_000010` (`cigarette`): `Electrical Box, Motor, Person, Safety Helmet`
- `cigarette_frame_000011` (`cigarette`): `Electrical Box, Motor, Person, Safety Helmet`
- `head_frame_000009` (`head`): `Fire Extinguisher, Fire Hydrant, Person, Safety Helmet`
- `head_frame_000010` (`head`): `Fire Extinguisher, Fire Hydrant, Person, Safety Helmet`
- `head_frame_000011` (`head`): `Fire Extinguisher, Fire Hydrant, Person, Safety Helmet`
- `phone_frame_000013` (`phone`): `Person, Pipeline, Pressure Gauge, Valve`
- `phone_frame_000014` (`phone`): `Person, Pipeline, Pressure Gauge, Valve`
- `phone_frame_000015` (`phone`): `Person, Pipeline, Pressure Gauge, Valve`
- `smog_frame_000005` (`smog`): `Fire Hydrant, Open Flame, Person, Smoke`
- `smog_frame_000007` (`smog`): `Fire Hydrant, Open Flame, Person, Smoke`
- `smog_frame_000010` (`smog`): `Fire Hydrant, Open Flame, Person, Smoke`
