"""Synthetic Block 1 datasets used by smoke tests."""

from __future__ import annotations

import numpy as np
import pandas as pd
import xarray as xr

from .postprocess import add_block1_diagnostics


def create_synthetic_block1_dataset(config) -> xr.Dataset:
    """Create a tiny deterministic Block 1-like dataset for smoke tests."""
    raw = config.raw if hasattr(config, "raw") else config
    domain = raw["domain"]
    forecast = raw["forecast"]
    smoke = raw.get("smoke", {})

    lat_count = int(smoke.get("latitude_count", 4))
    lon_count = int(smoke.get("longitude_count", 5))
    seed = int(smoke.get("random_seed", 42))
    rng = np.random.default_rng(seed)

    lead_hours = np.asarray(forecast["lead_hours"], dtype=np.int32)
    init_time = pd.Timestamp(forecast["init_time"]).tz_convert(None)
    valid_time = init_time + pd.to_timedelta(lead_hours, unit="h")
    latitudes = np.linspace(domain["latitude_min"], domain["latitude_max"], lat_count)
    longitudes = np.linspace(domain["longitude_min"], domain["longitude_max"], lon_count)
    shape = (len(lead_hours), lat_count, lon_count)

    increments = rng.gamma(shape=1.5, scale=1.0, size=shape).astype("float32")
    increments[0, :, :] = 0.0
    tp_raw = np.cumsum(increments, axis=0)
    cp_raw = 0.35 * tp_raw

    ds = xr.Dataset(
        data_vars={
            "tp_raw": (("lead_time", "latitude", "longitude"), tp_raw),
            "cp_raw": (("lead_time", "latitude", "longitude"), cp_raw.astype("float32")),
            "10u": (("lead_time", "latitude", "longitude"), rng.normal(5.0, 2.0, shape).astype("float32")),
            "10v": (("lead_time", "latitude", "longitude"), rng.normal(0.0, 2.0, shape).astype("float32")),
            "q_500": (("lead_time", "latitude", "longitude"), rng.uniform(0.001, 0.01, shape).astype("float32")),
            "q_850": (("lead_time", "latitude", "longitude"), rng.uniform(0.004, 0.018, shape).astype("float32")),
            "t_500": (("lead_time", "latitude", "longitude"), rng.normal(255.0, 4.0, shape).astype("float32")),
            "t_850": (("lead_time", "latitude", "longitude"), rng.normal(290.0, 4.0, shape).astype("float32")),
            "z_500": (("lead_time", "latitude", "longitude"), rng.normal(56000.0, 500.0, shape).astype("float32")),
            "z_850": (("lead_time", "latitude", "longitude"), rng.normal(14500.0, 250.0, shape).astype("float32")),
        },
        coords={
            "init_time": init_time.to_datetime64(),
            "lead_time": lead_hours,
            "valid_time": ("lead_time", valid_time.to_numpy(dtype="datetime64[ns]")),
            "latitude": latitudes.astype("float32"),
            "longitude": longitudes.astype("float32"),
        },
        attrs={
            "title": "AITCHazard Block 1 synthetic smoke dataset",
            "aifs_checkpoint": raw["aifs"]["checkpoint"],
            "mode": "smoke",
        },
    )
    ds["tp_raw"].attrs["units"] = "mm"
    ds["cp_raw"].attrs["units"] = "mm"
    ds["10u"].attrs["units"] = "m s-1"
    ds["10v"].attrs["units"] = "m s-1"
    return add_block1_diagnostics(ds, time_dim="lead_time")
