"""Block 1 campaign helpers and writers (no network, no GPU)."""
import datetime as dt
import json

import numpy as np
import pytest

from aitchazard.block1.campaign import (
    forecast_path, git_commit, layout_domains, pending_inits, required_months, task_index, write_json_atomic,
)
from aitchazard.block1.dates import init_dates, task_dates
from aitchazard.block1.output import OutputGrid, box, check_forecast, write_forecast

INITS = init_dates(range(2000, 2026))
OUT_CFG = {"layout": "split", "domains": {
    "regional": {"lat": [5.0, 35.0], "lon": [230.0, 300.0], "variables": ["tp", "msl"]},
    "tempest": {"lat": [-5.0, 45.0], "lon": [220.0, 310.0], "variables": ["msl", "10u"]},
}}


def test_task_index_pilot():
    assert task_index(INITS, 2023, 5) == 161
    assert {(d.year, d.month) for d in task_dates(INITS, 161)} == {(2023, 5)}


def test_task_index_roundtrip():
    for k in range(182):
        d = task_dates(INITS, k)[0]
        assert task_index(INITS, d.year, d.month) == k


def test_task_index_outside_schedule():
    with pytest.raises(ValueError):
        task_index(INITS, 2023, 12)


def test_required_months_include_previous():
    assert required_months(task_dates(INITS, 161), 6) == [(2023, 4), (2023, 5)]
    assert required_months(task_dates(INITS, 162), 6) == [(2023, 5), (2023, 6)]


def test_layouts():
    assert set(layout_domains(OUT_CFG)) == {"regional", "tempest"}
    single = layout_domains({**OUT_CFG, "layout": "single"})
    assert list(single) == ["extended"]
    assert single["extended"]["variables"] == ["tp", "msl", "10u"]


def test_box_regional():
    i, j = box({"lat": [5.0, 35.0], "lon": [230.0, 300.0]})
    assert (i.start, i.stop, j.start, j.stop) == (220, 341, 920, 1201)


def test_sub_index_within_bbox():
    grid = OutputGrid(layout_domains(OUT_CFG))
    assert grid.shape == (201, 361)
    i, j = grid.sub_index("regional")
    assert grid.lat[i][0] == 35.0 and grid.lat[i][-1] == 5.0
    assert grid.lon[j][0] == 230.0 and grid.lon[j][-1] == 300.0


def test_pending_skips_complete_keeps_partial(tmp_path):
    doms = layout_domains(OUT_CFG)
    t = task_dates(INITS, 161)[:3]
    for d in doms:
        p = forecast_path(tmp_path, d, t[0])
        p.parent.mkdir(parents=True, exist_ok=True)
        p.touch()
    forecast_path(tmp_path, "regional", t[1]).touch()  # tempest missing -> rerun
    assert pending_inits(tmp_path, doms, t) == t[1:]


def _data(n=13):
    d = {v: np.full((n, 3, 4), val, np.float32) for v, val in {"tp": 1e-3, "msl": 1.01e5, "10u": 5.0}.items()}
    d["tp"][0] = np.nan
    return d


def test_check_clean_forecast():
    assert check_forecast(_data()) == {}


def test_check_flags_nan_and_range():
    d = _data()
    d["msl"][5, 0, 0] = np.nan
    d["10u"][3, 1, 1] = 250.0
    issues = check_forecast(d)
    assert issues["msl: nan"] == 1
    assert issues["10u: range"][1] == 250.0
    assert "tp: nan" not in issues


def test_write_forecast_roundtrip(tmp_path):
    xr = pytest.importorskip("xarray")
    pytest.importorskip("netCDF4")
    grid = OutputGrid({"box": {"lat": [10.0, 11.0], "lon": [260.0, 261.0], "variables": ["tp", "10u"]}})
    leads = np.arange(0, 73, 6)
    data = {"tp": np.random.default_rng(0).random((13, *grid.shape)).astype(np.float32),
            "10u": np.ones((13, *grid.shape), np.float32)}
    data["tp"][0] = np.nan
    p = tmp_path / "f.nc"
    write_forecast(p, data, grid, "box", dt.datetime(2023, 5, 1, 0), leads)
    with xr.open_dataset(p) as ds:
        assert set(ds.data_vars) == {"tp", "u10"}
        assert ds.tp.dims == ("lead_time", "latitude", "longitude")
        assert ds.valid_time.values[-1] == np.datetime64("2023-05-04T00:00", "ns")
        np.testing.assert_array_equal(ds.tp.values[1:], data["tp"][1:])
    assert not list(tmp_path.glob("*.tmp*"))


def test_write_json_atomic(tmp_path):
    p = tmp_path / "m" / "x.json"
    write_json_atomic(p, {"a": dt.datetime(2023, 5, 1)})
    assert json.loads(p.read_text())["a"].startswith("2023-05-01")
    assert len(list(p.parent.iterdir())) == 1


def test_git_commit_loose_and_packed(tmp_path):
    g = tmp_path / ".git"
    (g / "refs" / "heads").mkdir(parents=True)
    (g / "HEAD").write_text("ref: refs/heads/main\n")
    (g / "packed-refs").write_text("# pack-refs with: peeled\nabc123 refs/heads/main\n")
    assert git_commit(tmp_path) == "abc123"
    (g / "refs" / "heads" / "main").write_text("def456\n")
    assert git_commit(tmp_path) == "def456"
