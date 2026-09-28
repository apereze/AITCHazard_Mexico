"""Unit tests for the Block 1 calendar and grid orientation (no network, no GPU)."""
import datetime as dt

import numpy as np
import pytest

from aitchazard.block1.dates import analysis_times, init_dates, n_tasks, task_dates
from aitchazard.block1.era5_inputs import orient_to_regrid_convention

DAYS_MAY_NOV = 31 + 30 + 31 + 31 + 30 + 31 + 30  # 214


def test_init_dates_one_season():
    inits = init_dates([2005])
    assert len(inits) == DAYS_MAY_NOV * 4
    assert inits[0] == dt.datetime(2005, 5, 1, 0)
    assert inits[-1] == dt.datetime(2005, 11, 30, 18)


def test_full_campaign_size():
    inits = init_dates(range(2000, 2026))
    assert len(inits) == 26 * DAYS_MAY_NOV * 4  # 22 256
    assert n_tasks(inits) == 26 * 7              # 182 array tasks


def test_analysis_times_are_unique_and_include_lag():
    times = analysis_times(init_dates([2005]))
    assert len(times) == DAYS_MAY_NOV * 4 + 1    # + 30 Apr 18 UTC
    assert times[0] == dt.datetime(2005, 4, 30, 18)


def test_task_dates_one_month():
    dates = task_dates(init_dates([2005]), 0)
    assert {(d.year, d.month) for d in dates} == {(2005, 5)}
    assert len(dates) == 31 * 4


def _lon_index_field(lon_first: float) -> np.ndarray:
    """Field whose value is the longitude of each column."""
    lons = lon_first + 0.25 * np.arange(1440)
    return np.tile(lons, (721, 1))


def test_no_roll_when_grid_starts_at_zero():
    out = orient_to_regrid_convention(_lon_index_field(0.0), 90.0, 0.0)
    assert out[0, 0] == 0.0 and out[0, 80] == 20.0 and out[0, 720] == 180.0


def test_roll_when_grid_starts_at_minus_180():
    out = orient_to_regrid_convention(_lon_index_field(-180.0), 90.0, -180.0)
    assert out[0, 0] == 0.0 and out[0, 80] == 20.0 and out[0, 1439] == -0.25


def test_latitude_flip():
    field = np.tile(np.linspace(-90, 90, 721)[:, None], (1, 1440))
    out = orient_to_regrid_convention(field, -90.0, 0.0)
    assert out[0, 0] == 90.0 and out[-1, 0] == -90.0


def test_wrong_shape_raises():
    with pytest.raises(ValueError):
        orient_to_regrid_convention(np.zeros((181, 360)), 90.0, 0.0)
