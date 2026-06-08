"""NetCDF I/O helpers for Block 1 outputs."""

from __future__ import annotations

from pathlib import Path
import xarray as xr


def validate_block1_dataset(ds: xr.Dataset) -> None:
    """Validate the minimal Block 1 NetCDF schema used downstream."""
    required_coords = ("init_time", "lead_time", "valid_time", "latitude", "longitude")
    missing_coords = [coord for coord in required_coords if coord not in ds.coords]
    if missing_coords:
        raise ValueError(f"Missing required coordinate(s): {', '.join(missing_coords)}")

    required_vars = ("tp_6h", "ws10")
    missing_vars = [var for var in required_vars if var not in ds.data_vars]
    if missing_vars:
        raise ValueError(f"Missing required variable(s): {', '.join(missing_vars)}")

    if ds.sizes.get("lead_time", 0) < 2:
        raise ValueError("Block 1 dataset must include at least two lead times")


def write_block1_netcdf(ds: xr.Dataset, path: str | Path) -> Path:
    """Validate and write a Block 1 dataset."""
    validate_block1_dataset(ds)
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ds.to_netcdf(output_path)
    return output_path
