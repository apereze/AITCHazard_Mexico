"""Figures of a TC case from the Block 1 benchmark outputs (AIFS Single v1.1 + ERA5).

For each initialisation found in the run directory:
  - MSLP + 10 m wind and 6 h precipitation maps at several lead times;
  - centre followed by minimum MSLP from the IBTrACS position at t0 (illustrative
    tracker, not TempestExtremes);
plus a track figure and an intensity figure (Pmin, Vmax) against IBTrACS.

Usage (login node, inside the container):
  python scripts/block1/plot_case.py --run-dir $BASE/benchmarks/block1/20050717_<JOB> \
      --ibtracs $BASE/data/ibtracs/ibtracs.NA.list.v04r01.csv --name EMILY --season 2005 \
      --out outputs/figures/emily_2005
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

KT_TO_MS = 0.514444
R_EARTH_KM = 6371.0
PRECIP_LEVELS = [1, 2, 5, 10, 20, 30, 50, 75, 100, 150]  # mm / 6 h
WIND_LEVELS = np.arange(0, 42, 3)  # m s-1


# ---------------------------------------------------------------- best track
def read_ibtracs(path: Path, name: str, season: int) -> pd.DataFrame:
    """IBTrACS CSV -> time, lat, lon (0-360), vmax (m s-1, USA 1-min), pmin (hPa)."""
    df = pd.read_csv(path, skiprows=[1], low_memory=False,
                     usecols=["SID", "SEASON", "NAME", "ISO_TIME", "LAT", "LON", "USA_WIND", "USA_PRES"])
    df = df[(df.NAME.str.strip() == name.upper()) & (pd.to_numeric(df.SEASON, errors="coerce") == season)]
    if df.empty:
        raise ValueError(f"{name} {season} not found in {path}")
    sid = df.SID.iloc[0]  # first storm with that name and season
    df = df[df.SID == sid]
    num = lambda c: pd.to_numeric(df[c], errors="coerce")  # noqa: E731
    bt = pd.DataFrame({"time": pd.to_datetime(df.ISO_TIME), "lat": num("LAT"), "lon": num("LON") % 360,
                       "vmax": num("USA_WIND") * KT_TO_MS, "pmin": num("USA_PRES")})
    print(f"IBTrACS {sid}: {len(bt)} records, {bt.time.min()} to {bt.time.max()}")
    return bt.dropna(subset=["lat", "lon"]).reset_index(drop=True)


def interp_track(bt: pd.DataFrame, times) -> pd.DataFrame:
    """Best track linearly interpolated in time; NaN outside its period."""
    t = pd.to_datetime(times).values.astype("datetime64[s]").astype(float)
    tb = bt.time.values.astype("datetime64[s]").astype(float)
    out = {"time": pd.to_datetime(times)}
    for c in ("lat", "lon", "vmax", "pmin"):
        ok = bt[c].notna().values
        out[c] = np.interp(t, tb[ok], bt[c].values[ok], left=np.nan, right=np.nan)
    return pd.DataFrame(out)


def haversine_km(lat1, lon1, lat2, lon2):
    p1, p2 = np.deg2rad(lat1), np.deg2rad(lat2)
    a = np.sin((p2 - p1) / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(np.deg2rad(lon2 - lon1) / 2) ** 2
    return 2 * R_EARTH_KM * np.arcsin(np.sqrt(a))


# ---------------------------------------------------------------- forecasts
def load_forecast(path: Path) -> dict:
    """One forecast file -> numpy arrays in plotting units."""
    import xarray as xr

    with xr.open_dataset(path, decode_timedelta=False) as ds:  # lead_time stays in hours
        f = {"lat": ds["latitude"].values, "lon": ds["longitude"].values,
             "lead": ds["lead_time"].values.astype(int),
             "valid": pd.to_datetime(ds["valid_time"].values),
             "init": pd.Timestamp(ds["init_time"].values),
             "msl": ds["msl"].values / 100.0,                      # Pa -> hPa
             "wind": np.hypot(ds["u10"].values, ds["v10"].values),  # m s-1
             "tp": ds["tp"].values * 1000.0}                       # m -> mm / 6 h
    return f


def load_lsm(run_dir: Path):
    import xarray as xr

    with xr.open_dataset(run_dir / "single/extended/static_extended.nc") as ds:
        return ds["latitude"].values, ds["longitude"].values, ds["lsm"].values


def follow_min_mslp(f: dict, lat0: float, lon0: float, radius: float = 3.0, r_vmax: float = 3.0) -> pd.DataFrame:
    """Follow the MSLP minimum from (lat0, lon0) at t0; Vmax = max 10 m wind within r_vmax degrees."""
    lon2d, lat2d = np.meshgrid(f["lon"], f["lat"])
    rows, prev, guess = [], None, (lat0, lon0)
    for k, lead in enumerate(f["lead"]):
        dist = np.hypot(lat2d - guess[0], (lon2d - guess[1]) * np.cos(np.deg2rad(guess[0])))
        p = np.where(dist <= radius, f["msl"][k], np.nan)
        if np.all(np.isnan(p)):
            break
        i, j = np.unravel_index(np.nanargmin(p), p.shape)
        pos = (float(f["lat"][i]), float(f["lon"][j]))
        d_c = np.hypot(lat2d - pos[0], (lon2d - pos[1]) * np.cos(np.deg2rad(pos[0])))
        rows.append({"lead": int(lead), "time": f["valid"][k], "lat": pos[0], "lon": pos[1],
                     "pmin": float(p[i, j]), "vmax": float(np.nanmax(np.where(d_c <= r_vmax, f["wind"][k], np.nan)))})
        # first guess for the next step: persistence of the last displacement
        guess = pos if prev is None else (2 * pos[0] - prev[0], 2 * pos[1] - prev[1])
        prev = pos
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- plotting
def _lon_label(x, _pos=None):
    x = (x + 180) % 360 - 180
    return f"{abs(x):.0f}°{'W' if x < 0 else 'E'}"


def _map_axes(ax, extent, lsm):
    lat, lon, mask = lsm
    ax.contour(lon, lat, mask, levels=[0.5], colors="k", linewidths=0.6)
    ax.set_xlim(extent[0], extent[1])
    ax.set_ylim(extent[2], extent[3])
    ax.set_aspect(1 / np.cos(np.deg2rad(0.5 * (extent[2] + extent[3]))))
    ax.xaxis.set_major_formatter(plt.FuncFormatter(_lon_label))
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _p: f"{y:.0f}°N"))
    ax.tick_params(labelsize=7)


def plot_fields(f, trk, bt_i, extent, lsm, name, out: Path):
    """Row 1: MSLP (hPa) + 10 m wind (m s-1); row 2: precipitation (mm / 6 h)."""
    leads_a = [h for h in (0, 24, 48, 72) if h in f["lead"]]
    leads_b = [h for h in (6, 24, 48, 72) if h in f["lead"]]
    fig, axs = plt.subplots(2, 4, figsize=(15, 7.2), constrained_layout=True)
    for col, h in enumerate(leads_a):
        k = int(np.where(f["lead"] == h)[0][0])
        ax = axs[0, col]
        cw = ax.contourf(f["lon"], f["lat"], f["wind"][k], levels=WIND_LEVELS, cmap="YlOrRd", extend="max")
        ax.contour(f["lon"], f["lat"], f["msl"][k], levels=np.arange(940, 1032, 4), colors="0.25", linewidths=0.5)
        _mark(ax, trk, bt_i, f["valid"][k])
        _map_axes(ax, extent, lsm)
        ax.set_title(f"+{h} h · {f['valid'][k]:%d %b %H} UTC", fontsize=9)
    fig.colorbar(cw, ax=axs[0, :], shrink=0.85, label="viento a 10 m (m s$^{-1}$); contornos: PMNM cada 4 hPa")
    for col, h in enumerate(leads_b):
        k = int(np.where(f["lead"] == h)[0][0])
        ax = axs[1, col]
        cp = ax.contourf(f["lon"], f["lat"], f["tp"][k], levels=PRECIP_LEVELS, cmap="YlGnBu", extend="max")
        _mark(ax, trk, bt_i, f["valid"][k])
        _map_axes(ax, extent, lsm)
        ax.set_title(f"+{h} h · {f['valid'][k]:%d %b %H} UTC", fontsize=9)
    fig.colorbar(cp, ax=axs[1, :], shrink=0.85, label="precipitación (mm / 6 h)")
    fig.suptitle(f"{name} · AIFS Single v1.1 (CI ERA5), inicio {f['init']:%Y-%m-%d %H} UTC · "
                 "× IBTrACS, ○ mínimo de PMNM seguido", fontsize=10)
    fig.savefig(out, dpi=150)
    plt.close(fig)


def _mark(ax, trk, bt_i, t):
    b = bt_i[bt_i.time == t]
    if len(b) and np.isfinite(b.lat.iloc[0]):
        ax.plot(b.lon, b.lat, "kx", ms=8, mew=1.8)
    c = trk[trk.time == t]
    if len(c):
        ax.plot(c.lon, c.lat, "o", mfc="none", mec="w", ms=9, mew=1.6)


def plot_tracks(tracks, bt, extent, lsm, name, out: Path):
    fig, ax = plt.subplots(figsize=(8, 6), constrained_layout=True)
    t0 = min(t.time.min() for t in tracks.values()) - pd.Timedelta("24h")
    t1 = max(t.time.max() for t in tracks.values()) + pd.Timedelta("24h")
    b = bt[(bt.time >= t0) & (bt.time <= t1)]
    ax.plot(b.lon, b.lat, "k-", lw=2, label="IBTrACS")
    b6 = b[b.time.dt.hour % 6 == 0]
    ax.plot(b6.lon, b6.lat, "k.", ms=5)
    for init, t in tracks.items():
        ax.plot(t.lon, t.lat, "o-", ms=3, lw=1.2, label=f"AIFS {init:%d %H} UTC")
    _map_axes(ax, extent, lsm)
    ax.legend(fontsize=8, loc="lower left")
    ax.set_title(f"{name}: trayectoria de 0 a 72 h (mínimo de PMNM) frente a IBTrACS", fontsize=10)
    fig.savefig(out, dpi=150)
    plt.close(fig)


def plot_intensity(tracks, bt, name, out: Path):
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.2), constrained_layout=True)
    t0 = min(t.time.min() for t in tracks.values()) - pd.Timedelta("12h")
    t1 = max(t.time.max() for t in tracks.values()) + pd.Timedelta("12h")
    b = bt[(bt.time >= t0) & (bt.time <= t1)]
    for ax, col, lab in ((axs[0], "pmin", "presión mínima (hPa)"), (axs[1], "vmax", "viento máximo (m s$^{-1}$)")):
        ax.plot(b.time, b[col], "k-", lw=2, label="IBTrACS")
        for init, t in tracks.items():
            ax.plot(t.time, t[col], "o-", ms=3, lw=1.2, label=f"AIFS {init:%d %H} UTC")
        ax.set_ylabel(lab)
        ax.tick_params(axis="x", labelrotation=30, labelsize=8)
        ax.grid(alpha=0.3)
    axs[0].legend(fontsize=8)
    fig.suptitle(f"{name}: intensidad. AIFS = máximo en malla de 0.25° a 10 m; "
                 "IBTrACS = viento sostenido de 1 min (no son equivalentes)", fontsize=9)
    fig.savefig(out, dpi=150)
    plt.close(fig)


# ---------------------------------------------------------------- main
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-dir", type=Path, required=True)
    ap.add_argument("--ibtracs", type=Path, required=True)
    ap.add_argument("--name", default="EMILY")
    ap.add_argument("--season", type=int, default=2005)
    ap.add_argument("--out", type=Path, default=Path("outputs/figures/case"))
    ap.add_argument("--extent", default="255,295,8,32", help="lon0,lon1,lat0,lat1 (lon 0-360)")
    a = ap.parse_args()

    extent = [float(x) for x in a.extent.split(",")]
    a.out.mkdir(parents=True, exist_ok=True)
    bt = read_ibtracs(a.ibtracs, a.name, a.season)
    lsm = load_lsm(a.run_dir)
    files = sorted((a.run_dir / "single/extended").glob("aifs11_extended_*.nc"))
    if not files:
        raise FileNotFoundError(f"no forecasts in {a.run_dir / 'single/extended'}")

    tracks, errors = {}, []
    for p in files:
        f = load_forecast(p)
        bt_i = interp_track(bt, f["valid"])
        if not np.isfinite(bt_i.lat.iloc[0]):
            print(f"{p.name}: {a.name} not active at t0, skipped")
            continue
        trk = follow_min_mslp(f, bt_i.lat.iloc[0], bt_i.lon.iloc[0])
        tracks[f["init"]] = trk
        m = trk.merge(bt_i, on="time", suffixes=("", "_bt"))
        errors.append(pd.DataFrame({"init": f["init"], "lead": m.lead,
                                    "track_err_km": haversine_km(m.lat, m.lon, m.lat_bt, m.lon_bt),
                                    "pmin_err_hPa": m.pmin - m.pmin_bt, "vmax_err_ms": m.vmax - m.vmax_bt}))
        plot_fields(f, trk, bt_i, extent, lsm, a.name, a.out / f"{a.name.lower()}_{f['init']:%Y%m%d%H}_campos.png")
        print(f"{p.name}: {len(trk)} centres")

    if not tracks:
        raise SystemExit(f"{a.name} is not active at any initialisation in {a.run_dir}")
    plot_tracks(tracks, bt, extent, lsm, a.name, a.out / f"{a.name.lower()}_trayectorias.png")
    plot_intensity(tracks, bt, a.name, a.out / f"{a.name.lower()}_intensidad.png")
    err = pd.concat(errors)
    err.to_csv(a.out / f"{a.name.lower()}_errores.csv", index=False)
    print(err.groupby("lead")[["track_err_km", "pmin_err_hPa", "vmax_err_ms"]].mean().round(1).to_string())
    print("figures in", a.out)


if __name__ == "__main__":
    main()
