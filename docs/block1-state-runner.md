# Block 1 State Runner

Block 1 real mode needs two AIFS Single v2 input states before Anemoi can run:
`t-6h` and `t0`. The legacy `state_runner*.py` scripts are useful references,
but they combine state retrieval, inference, and output writing in one place.

The production path now starts with a small state-planning layer:

- `config.py` validates the AIFS Single v2 checkpoint, Mexico domain, cadence,
  lead times, and output paths.
- `state_builder.py` converts the config into a JSON manifest describing the
  required input states and fields.
- `aifs_runner.py` keeps real mode guarded while exposing the manifest builder.
- `scripts/block1/run_aifs_single_v2.py --mode plan-states` writes the manifest
  without requiring credentials, GPU, MARS access, or Anemoi.

Run the planning step with:

```bash
python scripts/block1/run_aifs_single_v2.py \
  --config conf/aitchazard_mexico/block1_aifs_single_v2.yaml \
  --mode plan-states
```

The output is `outputs/block1_state_plan.json` by default. It records:

- the AIFS checkpoint;
- the initialization time;
- the two analysis times, `init_time - 6h` and `init_time`;
- the 6-hourly lead times through `t+72h`;
- the Mexico domain in 0-360 longitude convention;
- required surface fields and pressure-level fields such as `q_500`.

The next implementation step is a materializer that reads this manifest,
retrieves the planned MARS states, verifies all required fields, and passes the
assembled state to Anemoi inference.
