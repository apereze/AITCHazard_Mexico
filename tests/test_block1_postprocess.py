import numpy as np
import xarray as xr

from aitchazard.block1 import (
    DEFAULT_FORECAST_HORIZON_HOURS,
    MEXICO_DOMAIN,
    PRESSURE_LEVELS_HPA,
    add_block1_diagnostics,
    derive_interval_precipitation,
    derive_ws10,
)


def test_block1_constants_match_project_scope():
    assert MEXICO_DOMAIN["latitude_min"] == 5.0
    assert MEXICO_DOMAIN["latitude_max"] == 35.0
    assert MEXICO_DOMAIN["longitude_360_min"] == 230.0
    assert MEXICO_DOMAIN["longitude_360_max"] == 300.0
    assert DEFAULT_FORECAST_HORIZON_HOURS == 72
    assert PRESSURE_LEVELS_HPA[0] == 1000
    assert PRESSURE_LEVELS_HPA[-1] == 50


def test_derive_interval_precipitation_from_accumulation():
    ds = xr.Dataset(
        {
            "tp_raw": (
                ("lead_time", "latitude", "longitude"),
                np.array([[[0.0]], [[10.0]], [[25.0]]]),
            )
        },
        coords={"lead_time": [0, 6, 12], "latitude": [20.0], "longitude": [250.0]},
    )

    result = derive_interval_precipitation(ds, "tp_raw", "tp_6h")

    np.testing.assert_allclose(result["tp_6h"].values[:, 0, 0], [0.0, 10.0, 15.0])
    assert result["tp_6h"].attrs["source"] == "tp_raw"


def test_derive_interval_precipitation_clips_negative_resets():
    ds = xr.Dataset(
        {"tp_raw": ("lead_time", np.array([0.0, 6.0, 2.0]))},
        coords={"lead_time": [0, 6, 12]},
    )

    result = derive_interval_precipitation(ds, "tp_raw", "tp_6h")

    np.testing.assert_allclose(result["tp_6h"].values, [0.0, 6.0, 0.0])


def test_derive_ws10_from_components():
    ds = xr.Dataset({"10u": ("x", [3.0]), "10v": ("x", [4.0])})

    result = derive_ws10(ds)

    np.testing.assert_allclose(result["ws10"].values, [5.0])


def test_add_block1_diagnostics_adds_available_products_only():
    ds = xr.Dataset(
        {
            "tp_raw": ("lead_time", [0.0, 1.5]),
            "10u": ("lead_time", [3.0, 0.0]),
            "10v": ("lead_time", [4.0, 5.0]),
        },
        coords={"lead_time": [0, 6]},
    )

    result = add_block1_diagnostics(ds)

    assert "tp_6h" in result
    assert "ws10" in result
    assert "cp_6h" not in result
    np.testing.assert_allclose(result["tp_6h"].values, [0.0, 1.5])
    np.testing.assert_allclose(result["ws10"].values, [5.0, 5.0])
