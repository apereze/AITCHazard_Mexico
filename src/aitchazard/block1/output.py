"""Output grid, sanity checks and NetCDF writers for Block 1 (migrated from notebook 02).

Forecast files use a CF time dimension (valid time), required by TempestExtremes;
lead_time (forecast_period, hours) and init_time (forecast_reference_time) are coordinates.
Readers indexing by lead time can use ds.swap_dims(time="lead_time").
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import numpy as np

from aitchazard.block1.campaign import tmp_name

G = 9.80665
RES = 0.25
LAT = 90.0 - RES * np.arange(721)  # N -> S
LON = RES * np.arange(1440)        # 0-360
UNITS = {"tp": "m", "cp": "m", "tcc": "1", "10u": "m s-1", "10v": "m s-1", "msl": "Pa",
         "q_500": "kg kg-1", "q_850": "kg kg-1", "t_500": "K", "t_850": "K",
         "z_300": "m2 s-2", "z_500": "m2 s-2", "z_850": "m2 s-2", "zs": "m", "lsm": "1"}
NC_NAME = {"10u": "u10", "10v": "v10"}
NAN_AT_T0 = ("tp", "cp", "tcc")  # not in the ERA5 inputs: NaN at lead_time 0

# Loose plausibility bounds (SI); values outside are reported, not corrected
RANGES = {
    "msl": (8.7e4, 1.09e5), "10u": (-100.0, 100.0), "10v": (-100.0, 100.0),
    "tp": (-1e-6, 0.5), "cp": (-1e-6, 0.5), "tcc": (-1e-3, 1.001),
    "t_500": (200.0, 300.0), "t_850": (200.0, 330.0), "q_500": (0.0, 0.03), "q_850": (0.0, 0.04),
    "z_300": (7.0e4, 1.0e5), "z_500": (4.5e4, 6.2e4), "z_850": (8.0e3, 1.8e4),
}
COORD_ENC = {"latitude": {"_FillValue": None}, "longitude": {"_FillValue": None}}


def box(dom: dict) -> tuple[slice, slice]:
    """Indices of a lat-lon domain in the global 0.25 deg grid (N->S, 0-360)."""
    (la0, la1), (lo0, lo1) = sorted(dom["lat"]), sorted(dom["lon"])
    if not 0 <= lo0 < lo1 < 360:
        raise ValueError("domain must lie within 0-360 deg without crossing 0 deg")
    return (slice(int(round((90 - la1) / RES)), int(round((90 - la0) / RES)) + 1),
            slice(int(round(lo0 / RES)), int(round(lo1 / RES)) + 1))


class OutputGrid:
    """Bounding box of all output domains and sub-indices of each domain within it."""

    def __init__(self, domains: dict[str, dict]):
        self.domains = domains
        lats = [x for d in domains.values() for x in d["lat"]]
        lons = [x for d in domains.values() for x in d["lon"]]
        self.bi, self.bj = box({"lat": [min(lats), max(lats)], "lon": [min(lons), max(lons)]})
        self.lat, self.lon = LAT[self.bi], LON[self.bj]
        self.variables = list(dict.fromkeys(v for d in domains.values() for v in d["variables"]))

    @property
    def shape(self) -> tuple[int, int]:
        return self.lat.size, self.lon.size

    def sub_index(self, name: str) -> tuple[slice, slice]:
        i, j = box(self.domains[name])
        return (slice(i.start - self.bi.start, i.stop - self.bi.start),
                slice(j.start - self.bj.start, j.stop - self.bj.start))


def check_forecast(data: dict[str, np.ndarray]) -> dict:
    """NaN outside the allowed t0 accumulations and values outside RANGES (axis 0 = lead)."""
    issues: dict = {}
    for v, a in data.items():
        checked = a[1:] if v in NAN_AT_T0 else a
        n_nan = int(np.isnan(checked).sum())
        if n_nan:
            issues[f"{v}: nan"] = n_nan
        if v in RANGES:
            finite = a[np.isfinite(a)]
            if finite.size:
                lo, hi = RANGES[v]
                mn, mx = float(finite.min()), float(finite.max())
                if mn < lo or mx > hi:
                    issues[f"{v}: range"] = [mn, mx]
    return issues


def _atomic_netcdf(ds, path: Path, complevel: int, chunks, coord_enc: dict | None = None) -> int:
    enc = {n: {"zlib": True, "complevel": complevel, "dtype": "float32", "chunksizes": chunks(ds[n])}
           for n in ds.data_vars}
    enc.update(coord_enc or {})
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = tmp_name(path)
    ds.to_netcdf(tmp, encoding=enc, engine="netcdf4")
    tmp.replace(path)
    return path.stat().st_size


def write_forecast(path: Path, data: dict, grid: OutputGrid, domain: str, t0: dt.datetime,
                   leads: np.ndarray, complevel: int = 4, attrs: dict | None = None) -> int:
    """One forecast (time, latitude, longitude) of one domain; returns bytes on disk."""
    import xarray as xr

    dom = grid.domains[domain]
    i, j = grid.sub_index(domain)
    leads = np.asarray(leads)
    t0n = np.datetime64(t0, "ns")
    ref = f"hours since {t0:%Y-%m-%d %H:%M:%S}"
    ds = xr.Dataset(
        {NC_NAME.get(v, v): (("time", "latitude", "longitude"), data[v][:, i, j], {"units": UNITS[v]})
         for v in dom["variables"]},
        coords={"time": ("time", t0n + leads.astype("timedelta64[h]"), {"standard_name": "time"}),
                "lead_time": ("time", leads.astype("int32"),
                              {"units": "hours", "standard_name": "forecast_period"}),
                "init_time": ((), t0n, {"standard_name": "forecast_reference_time"}),
                "latitude": ("latitude", grid.lat[i], {"units": "degrees_north"}),
                "longitude": ("longitude", grid.lon[j], {"units": "degrees_east"})},
        attrs={"model": "aifs-single-1.1", "initial_conditions": "ERA5 (CDS)",
               "accumulation": "tp, cp: 6 h totals ending at time; NaN at lead_time 0 (t0 from ERA5)",
               **(attrs or {})},
    )
    coord_enc = {**COORD_ENC,
                 "time": {"units": ref, "calendar": "standard", "dtype": "int32"},
                 "init_time": {"units": ref, "calendar": "standard", "dtype": "int32"}}
    return _atomic_netcdf(ds, path, complevel, lambda da: (1, *da.shape[1:]), coord_enc)


def write_static(path: Path, static: dict, grid: OutputGrid, domain: str, complevel: int = 4) -> int:
    """zs (m) and lsm of one domain, written once."""
    import xarray as xr

    i, j = grid.sub_index(domain)
    ds = xr.Dataset({k: (("latitude", "longitude"), v[i, j], {"units": UNITS[k]}) for k, v in static.items()},
                    coords={"latitude": grid.lat[i], "longitude": grid.lon[j]})
    return _atomic_netcdf(ds, path, complevel, lambda da: da.shape, COORD_ENC)
