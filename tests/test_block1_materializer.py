from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest
import xarray as xr

from aitchazard.block1.config import Block1Config, load_block1_config
from aitchazard.block1.materializer import MissingFieldsError, materialize_state_plans
from aitchazard.block1.state_builder import build_state_plans


CONFIG_PATH = Path("conf/aitchazard_mexico/block1_aifs_single_v2.yaml")


def test_materializer_writes_required_fields_from_local_netcdf(tmp_path):
    source_path = tmp_path / "input_states.nc"
    output_path = tmp_path / "materialized_states.nc"
    _write_synthetic_state_source(source_path)
    config = _synthetic_config(source_path, output_path)

    result = materialize_state_plans(
        build_state_plans(config),
        config.state_source,
        output_path,
    )

    assert result.variable_count == 6
    assert "q_500" in result.variables
    assert "t_850" in result.variables
    assert result.analysis_times == (
        "2023-09-30T18:00:00Z",
        "2023-10-01T00:00:00Z",
    )

    with xr.open_dataset(output_path) as materialized:
        assert "10u" in materialized.data_vars
        assert "2t" in materialized.data_vars
        assert "q_500" in materialized.data_vars
        assert "q_850" in materialized.data_vars
        assert materialized.sizes["time"] == 2
        assert float(materialized.latitude.min()) >= 5.0
        assert float(materialized.latitude.max()) <= 35.0
        assert float(materialized.longitude.min()) >= 230.0
        assert float(materialized.longitude.max()) <= 300.0


def test_materializer_reports_missing_required_fields(tmp_path):
    source_path = tmp_path / "input_states.nc"
    output_path = tmp_path / "materialized_states.nc"
    _write_synthetic_state_source(source_path, include_temperature=False)
    config = _synthetic_config(source_path, output_path)

    with pytest.raises(MissingFieldsError) as raised:
        materialize_state_plans(
            build_state_plans(config),
            config.state_source,
            output_path,
        )

    assert "t_500" in raised.value.missing_fields
    assert "t_850" in raised.value.missing_fields


def _synthetic_config(source_path: Path, output_path: Path) -> Block1Config:
    base = load_block1_config(CONFIG_PATH)
    raw = deepcopy(base.raw)
    raw["state_source"] = {
        "kind": "netcdf",
        "uri": str(source_path),
    }
    raw["variables"] = {
        "surface": ["10u", "2t"],
        "pressure_families": ["q", "t"],
        "pressure_levels_hpa": [500, 850],
    }
    raw["paths"]["materialized_states"] = str(output_path)
    return Block1Config(raw=raw, path=Path("synthetic_block1.yaml"))


def _write_synthetic_state_source(
    path: Path, *, include_temperature: bool = True
) -> None:
    times = np.array(
        ["2023-09-30T18:00:00", "2023-10-01T00:00:00"],
        dtype="datetime64[ns]",
    )
    latitudes = np.array([0.0, 10.0, 20.0, 30.0, 40.0])
    longitudes = np.array([220.0, 230.0, 250.0, 300.0, 310.0])
    levels = np.array([500, 850])

    surface_shape = (len(times), len(latitudes), len(longitudes))
    pressure_shape = (len(times), len(levels), len(latitudes), len(longitudes))
    data_vars = {
        "10u": (("time", "latitude", "longitude"), np.ones(surface_shape)),
        "2t": (("time", "latitude", "longitude"), np.full(surface_shape, 280.0)),
        "q": (("time", "level", "latitude", "longitude"), np.ones(pressure_shape)),
    }
    if include_temperature:
        data_vars["t"] = (
            ("time", "level", "latitude", "longitude"),
            np.full(pressure_shape, 250.0),
        )

    dataset = xr.Dataset(
        data_vars=data_vars,
        coords={
            "time": times,
            "level": levels,
            "latitude": latitudes,
            "longitude": longitudes,
        },
    )
    dataset.to_netcdf(path)
