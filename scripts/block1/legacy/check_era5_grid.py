"""Check ERA5 grid orientation with the land-sea mask before interpolation (action 7).

Usage:
    python scripts/block1/check_era5_grid.py data/era5/2005/05/sfc.grib

Expected with correct orientation: lsm = 1 at (0N, 20E, Congo basin) and
lsm = 0 at (0N, 180E, Pacific). The unconditional np.roll of the prototype
notebook is also evaluated to show whether it shifts the field by 180 deg.
"""
from __future__ import annotations

import sys

import earthkit.data as ekd
import numpy as np

from aitchazard.block1.era5_inputs import orient_to_regrid_convention

# Row/column indices on the 0.25 deg grid ordered N->S and starting at 0 deg
POINTS = {"Congo (0N, 20E)": (360, 80, 1.0), "Pacific (0N, 180E)": (360, 720, 0.0)}


def main(path: str) -> int:
    lsm = ekd.from_source("file", path).sel(shortName="lsm")[0]
    lat0 = float(lsm.metadata("latitudeOfFirstGridPointInDegrees"))
    lon0 = float(lsm.metadata("longitudeOfFirstGridPointInDegrees"))
    raw = lsm.to_numpy()
    print(f"first grid point: lat={lat0}, lon={lon0}, shape={raw.shape}")

    candidates = {
        "metadata-based orientation": orient_to_regrid_convention(raw, lat0, lon0),
        "notebook unconditional roll": np.roll(raw, -(raw.shape[1] // 2), axis=1),
    }
    ok = True
    for label, arr in candidates.items():
        print(f"\n{label}:")
        for name, (i, j, expected) in POINTS.items():
            passed = abs(float(arr[i, j]) - expected) < 0.5
            print(f"  {name}: lsm={arr[i, j]:.2f} expected={expected} {'OK' if passed else 'FAIL'}")
            if label.startswith("metadata"):
                ok &= passed
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
