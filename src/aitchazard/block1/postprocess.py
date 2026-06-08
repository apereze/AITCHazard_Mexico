"""Post-processing helpers for Block 1 forecast outputs."""

from __future__ import annotations

import numpy as np
import xarray as xr


def derive_interval_precipitation(
    ds: xr.Dataset,
    accumulated_var: str,
    output_var: str,
    *,
    time_dim: str = "lead_time",
    clip_negative: bool = True,
) -> xr.Dataset:
    """Add interval precipitation from consecutive accumulated fields.

    The first interval keeps the first accumulated value. For standard forecast
    accumulations this should be zero at `lead_time=0`; later intervals are
    computed as differences between consecutive forecast outputs.
    """
    if accumulated_var not in ds:
        raise KeyError(f"Missing accumulated precipitation variable: {accumulated_var}")
    if time_dim not in ds[accumulated_var].dims:
        raise ValueError(f"{accumulated_var!r} must include dimension {time_dim!r}")

    accumulated = ds[accumulated_var]
    first = accumulated.isel({time_dim: [0]})
    differences = accumulated.diff(time_dim)
    interval = xr.concat([first, differences], dim=time_dim)
    interval = interval.assign_coords({time_dim: accumulated[time_dim]})

    if clip_negative:
        interval = interval.clip(min=0)

    result = ds.copy()
    result[output_var] = interval
    result[output_var].attrs.update(
        {
            "long_name": f"Interval precipitation derived from {accumulated_var}",
            "units": accumulated.attrs.get("units", "unknown"),
            "source": accumulated_var,
            "derivation": "first value followed by consecutive differences",
        }
    )
    return result


def derive_ws10(
    ds: xr.Dataset,
    *,
    u_var: str = "10u",
    v_var: str = "10v",
    output_var: str = "ws10",
) -> xr.Dataset:
    """Add 10 m wind speed from 10 m wind components."""
    missing = [var for var in (u_var, v_var) if var not in ds]
    if missing:
        raise KeyError(f"Missing wind component variable(s): {', '.join(missing)}")

    result = ds.copy()
    result[output_var] = np.hypot(result[u_var], result[v_var])
    result[output_var].attrs.update(
        {
            "long_name": "10 m wind speed",
            "units": result[u_var].attrs.get("units", "m s-1"),
            "source": f"{u_var}, {v_var}",
        }
    )
    return result


def add_block1_diagnostics(ds: xr.Dataset, *, time_dim: str = "lead_time") -> xr.Dataset:
    """Add standard Block 1 derived variables when their inputs are available."""
    result = ds.copy()

    precipitation_sources = {
        "tp_raw": "tp_6h",
        "tp": "tp_6h",
        "cp_raw": "cp_6h",
        "cp": "cp_6h",
    }
    for source, target in precipitation_sources.items():
        if source in result and target not in result:
            result = derive_interval_precipitation(
                result,
                source,
                target,
                time_dim=time_dim,
            )

    if "10u" in result and "10v" in result and "ws10" not in result:
        result = derive_ws10(result)

    return result
