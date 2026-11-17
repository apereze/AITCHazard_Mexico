#!/usr/bin/env python
"""Detection example: StitchNodes tracks (AIFS) vs IBTrACS for one forecast initialisation.

Panels: (a) map of detected and best-track positions; (b) minimum MSLP vs lead time;
(c) maximum 10 m wind vs lead time. Each detected track is paired with the nearest
IBTrACS system at its first time step (great-circle distance <= --max-dist-km).

Example:
  python scripts/tracking/plot_detection_example.py \
    --stitch $BASE/tests/te/ctrl55/tracks.txt \
    --ibtracs $BASE/data/ibtracs/ibtracs.EP.list.v04r01.csv $BASE/data/ibtracs/ibtracs.NA.list.v04r01.csv \
    --init 2005071700 --cols msl,wind --title "Emily y Eugene 2005" --out det.png
"""
import argparse

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

KT2MS = 0.514444
R_EARTH_KM = 6371.0
COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]  # fixed categorical order


def to180(lon):
    lon = np.asarray(lon, dtype=float)
    return np.where(lon > 180.0, lon - 360.0, lon)


def gc_km(lat1, lon1, lat2, lon2):
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dl = np.radians(np.asarray(lon2) - np.asarray(lon1))
    c = np.sin(p1) * np.sin(p2) + np.cos(p1) * np.cos(p2) * np.cos(dl)
    return R_EARTH_KM * np.arccos(np.clip(c, -1.0, 1.0))


def read_stitch(path, cols):
    """StitchNodes text output: 'start N yyyy mm dd hh', then rows i j lon lat <cols...> yyyy mm dd hh."""
    tracks, cur = [], None
    with open(path) as f:
        for line in f:
            tok = line.split()
            if not tok:
                continue
            if tok[0] == "start":
                cur = []
                tracks.append(cur)
                continue
            vals = tok[2:]  # drop grid indices i, j
            lon, lat = float(vals[0]), float(vals[1])
            data = [float(v) for v in vals[2:2 + len(cols)]]
            y, m, d, h = (int(v) for v in vals[-4:])
            cur.append(dict(time=pd.Timestamp(y, m, d, h), lon=lon, lat=lat, **dict(zip(cols, data))))
    out = []
    for k, t in enumerate(tracks):
        df = pd.DataFrame(t)
        df["lon"] = to180(df["lon"])
        df["track"] = k
        out.append(df)
    return out


def read_ibtracs(paths, t0, t1):
    frames = []
    for p in paths:
        df = pd.read_csv(p, skiprows=[1], low_memory=False, na_values=[" ", ""], keep_default_na=False)
        df["time"] = pd.to_datetime(df["ISO_TIME"])
        df = df[(df["time"] >= t0) & (df["time"] <= t1) & (df["time"].dt.hour % 6 == 0) & (df["time"].dt.minute == 0)]
        frames.append(df)
    df = pd.concat(frames).drop_duplicates(subset=["SID", "ISO_TIME"])
    for c in ["LAT", "LON", "USA_WIND", "USA_PRES", "WMO_WIND", "WMO_PRES"]:
        df[c] = pd.to_numeric(df.get(c), errors="coerce")
    df["wind"] = df["USA_WIND"].fillna(df["WMO_WIND"]) * KT2MS  # 1-min sustained, m/s
    df["msl"] = df["USA_PRES"].fillna(df["WMO_PRES"])  # hPa
    df["lon"] = to180(df["LON"])
    df["lat"] = df["LAT"]
    return {sid: g.sort_values("time") for sid, g in df.groupby("SID")}


def pair_tracks(tracks, best, max_km):
    pairs = []
    for tr in tracks:
        r0 = tr.iloc[0]
        cand = []
        for sid, g in best.items():
            g0 = g[g["time"] == r0["time"]]
            if len(g0):
                cand.append((float(gc_km(r0["lat"], r0["lon"], g0["lat"].iloc[0], g0["lon"].iloc[0])), sid))
        cand.sort()
        if cand and cand[0][0] <= max_km:
            pairs.append((tr, cand[0][1], cand[0][0]))
        else:
            pairs.append((tr, None, cand[0][0] if cand else np.nan))
    return pairs


def add_land_shp(ax, path):
    """Land polygons from a Natural Earth shapefile (e.g. ne_50m_land.shp), read with pyshp."""
    try:
        import shapefile
        for shp in shapefile.Reader(path).shapes():
            pts = np.asarray(shp.points)
            idx = list(shp.parts) + [len(pts)]
            for i0, i1 in zip(idx[:-1], idx[1:]):
                ax.fill(pts[i0:i1, 0], pts[i0:i1, 1], facecolor="#ecebe6", edgecolor="#8a8a85", lw=0.6, zorder=0)
        return True
    except Exception as e:  # optional layer
        print(f"[coast] not drawn: {e}")
        return False


def add_coast(ax, nc, var):
    """Coastline from the land-sea mask of the forecast file (no network needed)."""
    try:
        import xarray as xr
        ds = xr.open_dataset(nc)
        lsm = ds[var]
        lsm = lsm.isel({d: 0 for d in lsm.dims if d not in ("latitude", "longitude", "lat", "lon")})
        lat = lsm[[d for d in lsm.dims if "lat" in d][0]].values
        lon = to180(lsm[[d for d in lsm.dims if "lon" in d][0]].values)
        order = np.argsort(lon)
        ax.contourf(lon[order], lat, lsm.values[:, order], levels=[0.5, 1.5], colors=["#ecebe6"], zorder=0)
        ax.contour(lon[order], lat, lsm.values[:, order], levels=[0.5], colors="#8a8a85", linewidths=0.6, zorder=1)
        return True
    except Exception as e:  # optional layer
        print(f"[coast] not drawn: {e}")
        return False


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stitch", required=True)
    ap.add_argument("--ibtracs", nargs="+", required=True)
    ap.add_argument("--init", required=True, help="YYYYMMDDHH")
    ap.add_argument("--cols", default="msl,wind", help="columns after lon,lat in --in_fmt of StitchNodes")
    ap.add_argument("--max-dist-km", type=float, default=500.0)
    ap.add_argument("--domain", default="1.5,38.5,226.5,303.5", help="minlat,maxlat,minlon,maxlon of DetectNodes")
    ap.add_argument("--margin", type=float, default=6.5, help="closed-contour radius (deg) to show inner edge")
    ap.add_argument("--coast-nc", default=None, help="NetCDF with a land-sea mask (e.g. emily_00_time.nc)")
    ap.add_argument("--coast-var", default="lsm")
    ap.add_argument("--land-shp", default=None, help="Natural Earth land shapefile (preferred over --coast-nc)")
    ap.add_argument("--zoom-pad", type=float, default=8.0, help="map padding (deg) around tracks; large = full domain")
    ap.add_argument("--title", default="")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    cols = a.cols.split(",")
    t0 = pd.Timestamp(pd.to_datetime(a.init, format="%Y%m%d%H"))
    tracks = read_stitch(a.stitch, cols)
    if not tracks:
        raise SystemExit("no tracks in --stitch file")
    for tr in tracks:
        if tr["msl"].median() > 2000.0:  # Pa -> hPa
            tr["msl"] /= 100.0
        tr["lead"] = (tr["time"] - t0) / pd.Timedelta(hours=1)
    t1 = max(tr["time"].max() for tr in tracks)
    best = read_ibtracs(a.ibtracs, t0, t1)
    pairs = pair_tracks(tracks, best, a.max_dist_km)

    print(f"tracks detected: {len(tracks)} | IBTrACS systems in window: {len(best)}")
    for sid, g in best.items():
        print(f"  IBTrACS {sid} {g['NAME'].iloc[0]} ({g['BASIN'].iloc[0]}), {len(g)} points")
    for k, (tr, sid, d) in enumerate(pairs):
        name = best[sid]["NAME"].iloc[0] if sid else "unmatched"
        print(f"  track {k}: {len(tr)} pts from {tr['time'].iloc[0]:%Y-%m-%d %HZ} -> {name} {sid or ''} "
              f"| t0 distance {d:.0f} km")

    fig = plt.figure(figsize=(13, 6.5), constrained_layout=True)
    gs = fig.add_gridspec(2, 2, width_ratios=[1.6, 1])
    ax_m, ax_p, ax_w = fig.add_subplot(gs[:, 0]), fig.add_subplot(gs[0, 1]), fig.add_subplot(gs[1, 1])

    la0, la1, lo0, lo1 = (float(v) for v in a.domain.split(","))
    lo0, lo1 = float(to180(lo0)), float(to180(lo1))
    if a.land_shp:
        add_land_shp(ax_m, a.land_shp)
    elif a.coast_nc:
        add_coast(ax_m, a.coast_nc, a.coast_var)
    ax_m.plot([lo0, lo1, lo1, lo0, lo0], [la0, la0, la1, la1, la0], color="#8a8a85", lw=1.0, zorder=2)
    m = a.margin
    ax_m.plot([lo0 + m, lo1 - m, lo1 - m, lo0 + m, lo0 + m], [la0 + m, la0 + m, la1 - m, la1 - m, la0 + m],
              color="#8a8a85", lw=0.8, ls=":", zorder=2)

    for k, (tr, sid, d) in enumerate(pairs):
        c = COLORS[k % len(COLORS)]
        label = best[sid]["NAME"].iloc[0].title() if sid else f"track {k}"
        ax_m.plot(tr["lon"], tr["lat"], "-o", color=c, lw=2, ms=5, zorder=4)
        ax_m.plot(tr["lon"].iloc[0], tr["lat"].iloc[0], "o", color=c, ms=9, mec="white", mew=2, zorder=5)
        ax_m.annotate(label, (tr["lon"].iloc[-1], tr["lat"].iloc[-1]), xytext=(6, 4),
                      textcoords="offset points", fontsize=10, color="#2b2b29")
        ax_p.plot(tr["lead"], tr["msl"], "-o", color=c, lw=2, ms=4)
        ax_w.plot(tr["lead"], tr["wind"], "-o", color=c, lw=2, ms=4)
        if sid:
            g = best[sid].copy()
            g["lead"] = (g["time"] - t0) / pd.Timedelta(hours=1)
            ax_m.plot(g["lon"], g["lat"], "--o", color=c, lw=1.5, ms=4, mfc="white", zorder=3)
            ax_p.plot(g["lead"], g["msl"], "--o", color=c, lw=1.5, ms=4, mfc="white")
            ax_w.plot(g["lead"], g["wind"], "--o", color=c, lw=1.5, ms=4, mfc="white")

    allx = np.concatenate([tr["lon"].values for tr in tracks])
    ally = np.concatenate([tr["lat"].values for tr in tracks])
    z = a.zoom_pad
    ax_m.set_xlim(max(lo0 - 2, allx.min() - z), min(lo1 + 2, allx.max() + z))
    ax_m.set_ylim(max(la0 - 2, ally.min() - z), min(la1 + 2, ally.max() + z))
    ax_m.set_aspect(1.0 / np.cos(np.radians(0.5 * (la0 + la1))))
    ax_m.set_xlabel("longitude (°)")
    ax_m.set_ylabel("latitude (°)")
    ax_m.grid(color="#e4e3de", lw=0.6)
    ax_m.set_title("(a) trayectorias", loc="left", fontsize=11)

    ax_p.set_ylabel("presión mínima (hPa)")
    ax_p.set_title("(b) presión mínima al nivel del mar", loc="left", fontsize=11)
    ax_w.set_ylabel("viento máximo a 10 m (m s$^{-1}$)")
    ax_w.set_xlabel("plazo (h)")
    ax_w.set_title("(c) viento máximo a 10 m", loc="left", fontsize=11)
    for ax in (ax_p, ax_w):
        ax.grid(color="#e4e3de", lw=0.6)
        ax.set_xlim(left=0)
    for ax in (ax_m, ax_p, ax_w):
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)

    handles = [Line2D([], [], color="#2b2b29", ls="-", marker="o", ms=4, lw=2, label="AIFS + TempestExtremes"),
               Line2D([], [], color="#2b2b29", ls="--", marker="o", ms=4, mfc="white", lw=1.5, label="IBTrACS"),
               Line2D([], [], color="#2b2b29", marker="o", ms=9, mec="white", mew=2, ls="", label="t0"),
               ]
    xl, yl = ax_m.get_xlim(), ax_m.get_ylim()
    vis = lambda x0, x1, y0, y1: (xl[0] < x0 < xl[1] or xl[0] < x1 < xl[1] or yl[0] < y0 < yl[1] or yl[0] < y1 < yl[1])
    if vis(lo0, lo1, la0, la1):
        handles.append(Line2D([], [], color="#8a8a85", lw=1.0, label="dominio"))
    if vis(lo0 + m, lo1 - m, la0 + m, la1 - m):
        handles.append(Line2D([], [], color="#8a8a85", lw=0.8, ls=":", label=f"dominio − {a.margin:g}° (contorno)"))
    ax_m.legend(handles=handles, loc="lower left", fontsize=9, frameon=True, framealpha=0.9)
    fig.suptitle(a.title, fontsize=13, x=0.01, ha="left")
    ax_w.annotate("IBTrACS: viento sostenido 1 min (USA_WIND)\nAIFS: máximo de |v10| en 2°, malla 0.25°",
                  (0.99, 0.97), xycoords="axes fraction", ha="right", va="top", fontsize=8, color="#6b6b66")
    fig.savefig(a.out, dpi=200)
    print(f"saved: {a.out}")


if __name__ == "__main__":
    main()
