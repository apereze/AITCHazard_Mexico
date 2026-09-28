"""Local ERA5 initial conditions for AIFS Single v1.1 

Replaces the per-date CDS retrieval of the prototype notebook: GRIB files are
pre-staged monthly by scripts/block1/download_era5.py and read here.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import numpy as np

from aitchazard.block1.era5_params import normalise_field_name

ERA5_SHAPE = (721, 1440)
GROUPS = ("sfc", "pl", "soil")

# Inputs generated internally by anemoi-inference rather than read from ERA5.
# Names are indicative: confirm against the checkpoint metadata before relying on them.
COMPUTED_FORCINGS = {
    "cos_latitude", "sin_latitude", "cos_longitude", "sin_longitude",
    "cos_julian_day", "sin_julian_day", "cos_local_time", "sin_local_time",
    "cos_solar_zenith_angle", "insolation",
}


def orient_to_regrid_convention(values: np.ndarray, lat_first: float, lon_first: float) -> np.ndarray:
    """Return a (721, 1440) field ordered N->S and starting at 0 deg longitude.

    This is the regular 0.25 deg layout expected by earthkit-regrid. The roll is
    applied only when the source grid starts at -180 deg (e.g. ECMWF open data);
    ERA5 GRIB from CDS already starts at 0 deg and must not be rolled.
    """
    if values.shape != ERA5_SHAPE:
        raise ValueError(f"Expected global 0.25 deg grid {ERA5_SHAPE}, got {values.shape}")
    if lat_first < 0:
        values = values[::-1]
    if lon_first < 0:
        values = np.roll(values, -values.shape[1] // 2, axis=1)
    return values


def field_to_n320(field) -> np.ndarray:
    """Orient an ERA5 GRIB field from its metadata and interpolate 0.25 deg -> N320."""
    import earthkit.regrid as ekr

    values = orient_to_regrid_convention(
        field.to_numpy(),
        float(field.metadata("latitudeOfFirstGridPointInDegrees")),
        float(field.metadata("longitudeOfFirstGridPointInDegrees")),
    )
    return ekr.interpolate(values, {"grid": (0.25, 0.25)}, {"grid": "N320"})


def era5_path(root: Path, t: dt.datetime, group: str) -> Path:
    """Monthly GRIB path: {root}/{YYYY}/{MM}/{group}.grib."""
    return Path(root) / f"{t:%Y}" / f"{t:%m}" / f"{group}.grib"


def _month_index(year: int, month: int) -> int:
    return 12 * year + month - 1


class ERA5Local:
    """Build AIFS input states from pre-staged monthly ERA5 GRIB files.

    Initialisations must be processed in chronological order: the t0 fields of
    one cycle are reused as the t-6 h fields of the next.
    """

    def __init__(self, root: Path | str, lag_h: int = 6):
        self.root = Path(root)
        self.lag = dt.timedelta(hours=lag_h)
        self._sources: dict[tuple[int, int, str], object] = {}
        self._last: dict[dt.datetime, dict[str, np.ndarray]] = {}

    def _source(self, t: dt.datetime, group: str):
        import earthkit.data as ekd

        key = (t.year, t.month, group)
        if key not in self._sources:
            # keep only current and previous month open (t-6 h can fall in the previous month)
            current = _month_index(t.year, t.month)
            self._sources = {
                k: v for k, v in self._sources.items() if current - _month_index(k[0], k[1]) <= 1
            }
            path = era5_path(self.root, t, group)
            if not path.exists():
                raise FileNotFoundError(path)
            self._sources[key] = ekd.from_source("file", str(path))
        return self._sources[key]

    def read_time(self, t: dt.datetime) -> dict[str, np.ndarray]:
        """All ERA5 fields at analysis time t, interpolated to N320."""
        if t in self._last:
            return self._last[t]
        fields: dict[str, np.ndarray] = {}
        for group in GROUPS:
            selected = self._source(t, group).sel(
                dataDate=int(t.strftime("%Y%m%d")), dataTime=t.hour * 100
            )
            n = 0
            for f in selected:
                fields[normalise_field_name(field=f, source=group)] = field_to_n320(f)
                n += 1
            if n == 0:
                raise KeyError(f"No ERA5 '{group}' fields for {t:%Y-%m-%d %H} UTC")
        self._last = {t: fields}  # next cycle's t-6 h
        return fields

    def input_state(self, date: dt.datetime) -> dict:
        """anemoi-inference input state with fields stacked as [t-6 h, t0]."""
        prev = self.read_time(date - self.lag)
        curr = self.read_time(date)
        if prev.keys() != curr.keys():
            raise ValueError(f"Field sets differ between t-6 h and t0: {prev.keys() ^ curr.keys()}")
        return {"date": date, "fields": {k: np.stack([prev[k], curr[k]]) for k in curr}}


def checkpoint_input_variables(runner) -> set[str]:
    """Input variables expected by the checkpoint, excluding computed forcings.

    Attribute name valid for recent anemoi-inference versions; if missing,
    inspect the checkpoint metadata manually.
    """
    ckpt = runner.checkpoint
    if not hasattr(ckpt, "variable_to_input_tensor_index"):
        raise AttributeError("Checkpoint has no 'variable_to_input_tensor_index'; inspect metadata.")
    return set(ckpt.variable_to_input_tensor_index) - COMPUTED_FORCINGS


def compare_inputs(fields: dict, required: set[str]) -> dict[str, list[str]]:
    """Missing and extra variables of an input state relative to the checkpoint."""
    return {
        "missing": sorted(required - set(fields)),
        "extra": sorted(set(fields) - required),
    }
