"""Adapter from canonical Block 1 output to SwAIther-compatible input."""

from __future__ import annotations

from pathlib import Path
import xarray as xr

from aitchazard.block2.constants import CANONICAL_TO_SWAITHER


def to_swaither_lowres(ds: xr.Dataset) -> xr.Dataset:
    """Return a SwAIther-style low-resolution input dataset."""
    rename_dims = {}
    if "lead_time" in ds.dims:
        rename_dims["lead_time"] = "prediction_delta"
    if "latitude" in ds.dims:
        rename_dims["latitude"] = "lat"
    if "longitude" in ds.dims:
        rename_dims["longitude"] = "lon"

    out = ds.rename(rename_dims)
    if "prediction_delta" not in out.dims:
        raise ValueError("Block 1 dataset must include a lead_time/prediction_delta dimension")

    init_time = out.coords.get("init_time")
    if "time" not in out.dims:
        if init_time is None:
            raise ValueError("Block 1 dataset must include init_time to build SwAIther time dimension")
        out = out.expand_dims(time=[init_time.values])

    if "valid_time" in out.coords and out["valid_time"].dims == ("prediction_delta",):
        valid_time = out["valid_time"].values
        out = out.assign_coords(
            valid_time=(("time", "prediction_delta"), valid_time.reshape(1, -1))
        )

    for canonical, alias in CANONICAL_TO_SWAITHER.items():
        if canonical in out and alias not in out:
            out[alias] = out[canonical].clip(min=0) if canonical in ("tp_6h", "cp_6h") else out[canonical]
            out[alias].attrs.update({"source": canonical})

    keep_vars = [alias for alias in CANONICAL_TO_SWAITHER.values() if alias in out]
    if not keep_vars:
        raise ValueError("No SwAIther-compatible variables found in Block 1 dataset")

    result = out[keep_vars]
    expected_dims = {"time", "prediction_delta", "lat", "lon"}
    missing_dims = expected_dims.difference(result.dims)
    if missing_dims:
        raise ValueError(f"Missing SwAIther dimension(s): {', '.join(sorted(missing_dims))}")

    result.attrs.update(
        {
            "title": "AITCHazard SwAIther-compatible low-resolution input",
            "source": "AITCHazard Block 1 canonical output",
        }
    )
    return result


def write_swaither_lowres(ds: xr.Dataset, path: str | Path) -> Path:
    """Write SwAIther-compatible low-resolution input NetCDF."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    to_swaither_lowres(ds).to_netcdf(output_path)
    return output_path
