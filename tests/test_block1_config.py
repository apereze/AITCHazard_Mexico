from pathlib import Path

import pytest
import yaml

from aitchazard.block1.config import load_block1_config, validate_block1_config


CONFIG_PATH = Path("conf/aitchazard_mexico/block1_aifs_single_v2.yaml")


def test_block1_config_targets_aifs_single_v2_and_mexico_domain():
    config = load_block1_config(CONFIG_PATH)

    assert config.checkpoint == "ecmwf/aifs-single-2.0"
    assert config.lead_hours == list(range(0, 73, 6))
    assert config.raw["domain"]["latitude_min"] == 5.0
    assert config.raw["domain"]["latitude_max"] == 35.0
    assert config.raw["domain"]["longitude_min"] == 230.0
    assert config.raw["domain"]["longitude_max"] == 300.0


def test_block1_config_rejects_aifs_single_v1():
    raw = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    raw["aifs"]["checkpoint"] = "ecmwf/aifs-single-1.0"

    with pytest.raises(ValueError, match="ecmwf/aifs-single-2.0"):
        validate_block1_config(raw)


def test_block1_config_rejects_wrong_lead_hours():
    raw = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    raw["forecast"]["lead_hours"] = [0, 6, 12]

    with pytest.raises(ValueError, match="must end at 72"):
        validate_block1_config(raw)
