"""Check that AIFS tp at valid time T is the 6 h total of (T-6 h, T], like MSWEP V3.16 6 h.

For each forecast of one month, AIFS tp at a fixed lead (6 and 24 h) is compared with MSWEP
shifted by k in {-12, -6, 0, +6, +12} h. If the windows agree, the correlation peaks at k = 0;
a peak at k = -6 or +6 h means a one-step offset. MSWEP (0.1 deg) is smoothed with a 3 x 3
running mean and taken at the nearest point of the AIFS 0.25 deg grid (no scipy needed).
Usage: python scripts/block2/check_tp_window.py <regional dir YYYY/MM> <mswep_v3_6h_YYYY.nc>
"""
import sys
from pathlib import Path

import numpy as np
import xarray as xr

LEADS, LAGS = (6, 24), (-12, -6, 0, 6, 12)


def std_coords(ds):
    ren = {k: v for k, v in {"latitude": "lat", "longitude": "lon"}.items() if k in ds.coords}
    ds = ds.rename(ren)
    ds = ds.assign_coords(lon=ds.lon % 360).sortby("lon").sortby("lat")
    return ds


reg_dir, msw_path = Path(sys.argv[1]), Path(sys.argv[2])
files = sorted(reg_dir.glob("aifs11_regional_*.nc"))
msw = std_coords(xr.open_dataset(msw_path))["precipitation"]
print(f"{len(files)} AIFS files | MSWEP {dict(msw.sizes)} | units: {msw.attrs.get('units', '?')}")

aifs = {L: [] for L in LEADS}
for f in files:
    with xr.open_dataset(f) as ds:
        ds = std_coords(ds)
        for L in LEADS:
            i = int(np.flatnonzero(ds.lead_time.values == L)[0])
            aifs[L].append((ds["tp"].isel(time=i) * 1000.0).load())  # m -> mm per 6 h
aifs = {L: xr.concat(v, "time") for L, v in aifs.items()}
grid = aifs[LEADS[0]]

# MSWEP: only the times needed, domain of the AIFS grid, 3 x 3 mean, nearest 0.25 point
mt = msw.time.values.astype("datetime64[h]")
need = sorted({t + np.timedelta64(k, "h") for a in aifs.values()
               for t in a.time.values.astype("datetime64[h]") for k in LAGS} & set(mt))
msw_s = msw.sel(time=np.array(need, dtype="datetime64[ns]"),
                lat=slice(float(grid.lat.min()) - 0.2, float(grid.lat.max()) + 0.2),
                lon=slice(float(grid.lon.min()) - 0.2, float(grid.lon.max()) + 0.2)).load()
msw_s = msw_s.rolling(lat=3, lon=3, center=True, min_periods=5).mean()
msw_s = msw_s.sel(lat=grid.lat.values, lon=grid.lon.values, method="nearest")
msw_s = msw_s.assign_coords(lat=grid.lat.values, lon=grid.lon.values)
have = set(np.array(need, dtype="datetime64[h]"))

for L, a in aifs.items():
    print(f"\nlead {L} h: {a.sizes['time']} fields, AIFS domain mean {float(a.mean()):.3f} mm/6h")
    for k in LAGS:
        vt = a.time.values.astype("datetime64[h]") + np.timedelta64(k, "h")
        ok = np.array([t in have for t in vt])
        x = a.values[ok]
        y = msw_s.sel(time=vt[ok].astype("datetime64[ns]")).values
        m = np.isfinite(x) & np.isfinite(y)
        pat = [np.corrcoef(xi[mi], yi[mi])[0, 1] for xi, yi, mi in zip(x, y, m) if mi.sum() > 100]
        r_all = np.corrcoef(x[m], y[m])[0, 1]
        r_log = np.corrcoef(np.log1p(np.clip(x[m], 0, None)), np.log1p(np.clip(y[m], 0, None)))[0, 1]
        tag = "  <- expected peak" if k == 0 else ""
        print(f"  MSWEP at T{k:+d} h: n={ok.sum():3d}  mean pattern r={np.nanmean(pat):.3f}  "
              f"pooled r={r_all:.3f}  pooled r(log1p)={r_log:.3f}  MSWEP mean {np.nanmean(y[m]):.3f}{tag}")
