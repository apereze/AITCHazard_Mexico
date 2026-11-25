"""Environmental predictors along AIFS forecast tracks matched to IBTrACS (pilot of the intensity correction).

For every row of matches_long.csv with a forecast position (match == t0), the AIFS regional file of that
initialisation is read at the valid time and, around the forecast centre:
  shr_ms      850-200 hPa vertical wind shear magnitude of the 200-800 km annulus means (as SHIPS SHRD)
  rh500, rh850  relative humidity (0-1, over water, Bolton 1980) averaged in the 200-800 km annulus
  ann_frac    fraction of the 200-800 km annulus inside the regional domain (< 1 near the edges)
  skt_K       ERA5 skin temperature at t0 (SST proxy; AIFS does not output SST), mean of ocean points within
              100 km of the forecast centre; NaN over land
  dtl_km      distance from the forecast centre to the nearest land point of the regional lsm (0 over land)
All predictors are known at forecast time (forecast fields at the valid time; ERA5 only at t0).

Usage (Curnagl, CPU node, inside the AIFS container: xarray, cfgrib, scipy):
  python scripts/tracking/env_predictors.py \
    --matches $BASE/outputs/tracking/match_d24/matches_long.csv \
    --out $BASE/outputs/tracking/match_d24/env_predictors.csv
"""
import argparse
import os
from pathlib import Path

import numpy as np
import pandas as pd

R_EARTH_KM = 6371.0
ANNULUS_KM = (200.0, 800.0)
SST_RADIUS_KM = 100.0


def gc_dist_km(lon0, lat0, lon, lat):
    """Great-circle distance (km) from one point to arrays of points (degrees)."""
    lon0, lat0, lon, lat = map(np.radians, (lon0, lat0, lon, lat))
    a = np.sin((lat - lat0) / 2) ** 2 + np.cos(lat0) * np.cos(lat) * np.sin((lon - lon0) / 2) ** 2
    return 2 * R_EARTH_KM * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))


def rel_hum(q, t_k, p_hpa):
    """Relative humidity (0-1) from specific humidity (kg/kg), temperature (K) and pressure (hPa)."""
    e = q * p_hpa / (0.622 + 0.378 * q)
    es = 6.112 * np.exp(17.67 * (t_k - 273.15) / (t_k - 29.65))
    return e / es


def annulus_frac(lon0, lat0, lon2d, lat2d, inner, outer, step_km=25.0):
    """Fraction of the annulus area covered by the domain, estimated on a polar sampling of the annulus."""
    r = np.arange(inner + step_km / 2, outer, step_km)
    th = np.radians(np.arange(0, 360, 10))
    rr, tt = np.meshgrid(r, th)
    dlat = np.degrees(rr * np.cos(tt) / R_EARTH_KM)
    dlon = np.degrees(rr * np.sin(tt) / (R_EARTH_KM * np.cos(np.radians(lat0))))
    lat, lon = lat0 + dlat, lon0 + dlon
    inside = (lat >= lat2d.min()) & (lat <= lat2d.max()) & (lon >= lon2d.min()) & (lon <= lon2d.max())
    return float((inside * rr).sum() / rr.sum())  # area weight ~ r


def land_tree(lsm, lon2d, lat2d):
    from scipy.spatial import cKDTree
    land = lsm >= 0.5
    la, lo = np.radians(lat2d[land]), np.radians(lon2d[land])
    xyz = np.c_[np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)]
    return cKDTree(xyz)


def dist_to_land_km(tree, lon0, lat0):
    la, lo = np.radians(lat0), np.radians(lon0)
    chord, _ = tree.query([np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)])
    return 2 * R_EARTH_KM * np.arcsin(min(chord / 2, 1.0))


def load_skt_month(era5_root, ts, lat, lon):
    """ERA5 skin temperature of one month on the regional grid (cfgrib, no index files written)."""
    import xarray as xr
    f = Path(era5_root) / f"{ts:%Y}" / f"{ts:%m}" / "sfc.grib"
    ds = xr.open_dataset(f, engine="cfgrib", backend_kwargs={"filter_by_keys": {"shortName": "skt"}, "indexpath": ""})
    return ds["skt"].sel(latitude=lat, longitude=lon, method="nearest").load()


def main():
    base = Path(os.environ.get("BASE", "/work/FAC/FGSE/IDYST/tbeucler/default/apereze"))
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--matches", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--regional-root", type=Path, default=base / "outputs/block1/regional")
    ap.add_argument("--era5-root", type=Path, default=base / "data/era5")
    a = ap.parse_args()

    import xarray as xr
    long = pd.read_csv(a.matches, parse_dates=["init", "valid"])
    rows = long[(long["match"] == "t0") & long["fc_lon"].notna()].copy()
    print(f"{len(rows)} forecast positions, {rows['init'].nunique()} initialisations")

    st = xr.open_dataset(a.regional_root / "static_regional.nc")
    lat, lon = st["latitude"].values, st["longitude"].values
    lon2d, lat2d = np.meshgrid(lon, lat)
    lsm = st["lsm"].values
    tree = land_tree(lsm, lon2d, lat2d)

    out, skt_cache = [], {}
    for k, (ini, g) in enumerate(rows.groupby("init")):
        f = a.regional_root / f"{ini:%Y}" / f"{ini:%m}" / f"aifs11_regional_{ini:%Y%m%d%H}.nc"
        if not f.exists():
            print("missing", f)
            continue
        ds = xr.open_dataset(f, decode_timedelta=True)
        mkey = (ini.year, ini.month)
        if mkey not in skt_cache:
            skt_cache.clear()  # one month in memory
            skt_cache[mkey] = load_skt_month(a.era5_root, ini, lat, lon)
        skt0 = skt_cache[mkey].sel(time=ini).values
        for _, r in g.iterrows():
            lon0 = r["fc_lon"] % 360.0
            lat0 = r["fc_lat"]
            x = ds.sel(time=r["valid"])
            dist = gc_dist_km(lon0, lat0, lon2d, lat2d)
            ann = (dist >= ANNULUS_KM[0]) & (dist <= ANNULUS_KM[1])
            ocean_near = (dist <= SST_RADIUS_KM) & (lsm < 0.5)
            m = lambda v: float(np.nanmean(x[v].values[ann])) if ann.any() else np.nan
            du, dv = m("u_200") - m("u_850"), m("v_200") - m("v_850")
            out.append(dict(init=ini, SID=r["SID"], track=r["track"], lead_h=r["lead_h"],
                            shr_ms=np.hypot(du, dv),
                            rh500=float(np.nanmean(rel_hum(x["q_500"].values, x["t_500"].values, 500.0)[ann])),
                            rh850=float(np.nanmean(rel_hum(x["q_850"].values, x["t_850"].values, 850.0)[ann])),
                            ann_frac=annulus_frac(lon0, lat0, lon2d, lat2d, *ANNULUS_KM),
                            skt_K=float(np.nanmean(skt0[ocean_near])) if ocean_near.any() else np.nan,
                            dtl_km=0.0 if lsm[np.unravel_index(np.argmin(dist), dist.shape)] >= 0.5
                            else dist_to_land_km(tree, lon0, lat0)))
        ds.close()
        if k % 100 == 0:
            print(f"{k} inits, {len(out)} rows")
    res = pd.DataFrame(out)
    res.to_csv(a.out, index=False, float_format="%.4f")
    print(res.describe().round(2).to_string())
    print("saved", a.out)


if __name__ == "__main__":
    main()
