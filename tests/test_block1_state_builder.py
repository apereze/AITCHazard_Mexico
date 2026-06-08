from pathlib import Path

from aitchazard.block1.config import load_block1_config
from aitchazard.block1.state_builder import build_state_plans


CONFIG_PATH = Path("conf/aitchazard_mexico/block1_aifs_single_v2.yaml")


def test_state_builder_creates_t_minus_6_and_t0_plan():
    config = load_block1_config(CONFIG_PATH)

    plans = build_state_plans(config)

    assert len(plans) == 1
    plan = plans[0]
    assert plan.analysis_times[0].isoformat() == "2023-09-30T18:00:00+00:00"
    assert plan.analysis_times[1].isoformat() == "2023-10-01T00:00:00+00:00"
    assert plan.lead_hours == tuple(range(0, 73, 6))
    assert plan.domain["longitude_min"] == 230.0
    assert plan.domain["longitude_max"] == 300.0
    assert "10u" in plan.surface_variables
    assert "q_500" in plan.required_pressure_fields


def test_state_builder_writes_manifest(tmp_path):
    config = load_block1_config(CONFIG_PATH)
    plans = build_state_plans(config)

    from aitchazard.block1.state_builder import write_state_manifest

    manifest_path = write_state_manifest(plans, tmp_path / "state_plan.json")

    text = manifest_path.read_text(encoding="utf-8")
    assert "aitchazard.block1.state-plan.v1" in text
    assert "2023-09-30T18:00:00Z" in text
