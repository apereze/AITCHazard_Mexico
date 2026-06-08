from pathlib import Path
import subprocess
import sys

import yaml

from aitchazard.block1.config import load_block1_config
from aitchazard.block1.swaither_adapter import to_swaither_lowres
from aitchazard.block1.synthetic import create_synthetic_block1_dataset


CONFIG_PATH = Path("conf/aitchazard_mexico/block1_aifs_single_v2.yaml")


def test_synthetic_smoke_dataset_contains_block1_derived_variables():
    config = load_block1_config(CONFIG_PATH)

    ds = create_synthetic_block1_dataset(config)

    assert "tp_6h" in ds
    assert "cp_6h" in ds
    assert "ws10" in ds
    assert ds.sizes["lead_time"] == 13
    assert float(ds.latitude.min()) == 5.0
    assert float(ds.latitude.max()) == 35.0


def test_swaither_adapter_uses_time_prediction_delta_lat_lon_contract():
    config = load_block1_config(CONFIG_PATH)
    ds = create_synthetic_block1_dataset(config)

    result = to_swaither_lowres(ds)

    assert set(("time", "prediction_delta", "lat", "lon")).issubset(result.dims)
    assert result.sizes["time"] == 1
    assert result.sizes["prediction_delta"] == 13
    assert "total_precipitation_NoNeg" in result
    assert "convective_precipitation_NoNeg" in result
    assert "wind_10m_u" in result


def test_block1_cli_smoke_writes_block1_and_swaither_outputs(tmp_path):
    raw = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    block1_output = tmp_path / "block1_smoke.nc"
    swaither_output = tmp_path / "swaither_inputs_smoke.nc"
    raw["paths"]["block1_output"] = str(block1_output)
    raw["paths"]["swaither_output"] = str(swaither_output)
    config_path = tmp_path / "block1.yaml"
    config_path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            "scripts/block1/run_aifs_single_v2.py",
            "--config",
            str(config_path),
            "--mode",
            "smoke",
        ],
        check=True,
    )
    subprocess.run(
        [
            sys.executable,
            "scripts/block1/prepare_swaither_inputs.py",
            "--input",
            str(block1_output),
            "--output",
            str(swaither_output),
        ],
        check=True,
    )

    assert block1_output.is_file()
    assert swaither_output.is_file()
