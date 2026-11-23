"""Compare AIFS + TempestExtremes tracks with IBTrACS for one storm, init by init.

For each initialisation, keeps every stitched track within maxdist km of the IBTrACS storm at the first
time both exist (TCBench-style matching; one row per track, so a storm that regenerates can appear twice) and reports position errors by lead time, how long the
storm is followed, and the forecast intensity against IBTrACS.

Usage (Curnagl, inside the AIFS container or any env with numpy + pandas):
  python scripts/tracking/john_tracks_vs_ibtracs.py \
    --tracks-dir $BASE/outputs/tracking/te_tcbench/2024/09 \
    --ibtracs $BASE/data/ibtracs/ibtracs.EP.list.v04r01.csv \
    --name JOHN --season 2024 --first 2024092000 --last 2024092718 \
    --out $BASE/outputs/tracking/john2024_vs_ibtracs.csv
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

R_EARTH_KM = 6371.0
LEADS_H = (0, 24, 48, 72)


def haversine_km(lon1, lat1, lon2, lat2):
    lon1, lat1, lon2, lat2 = map(np.radians, (lon1, lat1, lon2, lat2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 2 * R_EARTH_KM * np.arcsin(np.sqrt(a))


def read_tracks(path):
    # StitchNodes text output: "start N yyyy mm dd hh", then "i j lon lat msl wind yyyy mm dd hh" per node
    tracks, cur = [], None
    for line in open(path):
        p = line.split()
        if not p:
            continue
        if p[0] == "start":
            cur = []
            tracks.append(cur)
            continue
        lon, lat, msl, wind = map(float, p[2:6])
        y, m, d, h = map(int, p[6:10])
        cur.append((pd.Timestamp(y, m, d, h), lon - 360.0 if lon > 180 else lon, lat, msl, wind))
    return [pd.DataFrame(t, columns=["t", "lon", "lat", "msl", "wind"]).set_index("t") for t in tracks if t]


def read_ibtracs(path, name, season):
    ib = pd.read_csv(path, skiprows=[1], low_memory=False)
    ib = ib[(ib["NAME"].str.strip() == name) & (ib["SEASON"].astype(int) == season)].copy()
    if ib.empty:
        raise SystemExit(f"{name} {season} not found in {path}")
    ib["t"] = pd.to_datetime(ib["ISO_TIME"])
    for c in ("LAT", "LON", "USA_WIND", "USA_PRES", "WMO_PRES"):
        ib[c] = pd.to_numeric(ib.get(c), errors="coerce")
    ib["pres"] = ib["USA_PRES"].fillna(ib["WMO_PRES"])
    return ib.set_index("t")[["LON", "LAT", "USA_WIND", "pres"]].rename(columns=str.lower)


def match(tracks, ib, maxdist):
    # every track within maxdist of the storm at the first time it shares with IBTrACS
    # (a storm that dissipates and regenerates can be followed by two tracks in one forecast)
    hits, closest = [], np.inf
    for tr in tracks:
        common = tr.index.intersection(ib.index)
        if len(common) == 0:
            continue
        t0 = common[0]
        d = haversine_km(tr.at[t0, "lon"], tr.at[t0, "lat"], ib.at[t0, "lon"], ib.at[t0, "lat"])
        closest = min(closest, d)
        if d <= maxdist:
            hits.append((tr, d))
    return sorted(hits, key=lambda h: h[0].index.min()), closest


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tracks-dir", required=True, type=Path)
    ap.add_argument("--ibtracs", required=True, type=Path)
    ap.add_argument("--name", default="JOHN")
    ap.add_argument("--season", type=int, default=2024)
    ap.add_argument("--first", default="2024092000")
    ap.add_argument("--last", default="2024092718")
    ap.add_argument("--maxdist", type=float, default=500.0, help="matching distance (km)")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()

    ib = read_ibtracs(a.ibtracs, a.name, a.season)
    print(f"IBTrACS {a.name} {a.season}: {ib.index.min()} -> {ib.index.max()}, "
          f"min pres {ib['pres'].min():.0f} hPa, max wind {ib['usa_wind'].max():.0f} kt")
    fmt = "%Y%m%d%H"
    inits = pd.date_range(pd.to_datetime(a.first, format=fmt), pd.to_datetime(a.last, format=fmt), freq="6h")
    rows = []
    for ini in inits:
        f = a.tracks_dir / f"aifs11_tempest_{ini:%Y%m%d%H}_tracks.txt"
        row = {"init": ini}
        if not f.exists():
            rows.append({**row, "status": "no file"})
            continue
        tracks = read_tracks(f)
        hits, closest = match(tracks, ib, a.maxdist)
        row.update(n_tracks=len(tracks))
        if not hits:
            rows.append({**row, "status": "no match" if np.isfinite(closest) else "storm not in window",
                         "closest_km": round(closest) if np.isfinite(closest) else np.nan})
            continue
        for k, (tr, d0) in enumerate(hits, start=1):
            r = dict(row)
            lead = (tr.index - ini) / pd.Timedelta(hours=1)
            r.update(status="match", track=k, first_valid=tr.index.min(), first_lead_h=int(lead.min()),
                     last_lead_h=int(lead.max()), dist_first_km=round(d0))
            for L in LEADS_H:
                t = ini + pd.Timedelta(hours=L)
                if t in tr.index and t in ib.index:
                    r[f"err_{L}h_km"] = round(haversine_km(tr.at[t, "lon"], tr.at[t, "lat"], ib.at[t, "lon"], ib.at[t, "lat"]))
            common = tr.index.intersection(ib.index)
            r.update(fc_min_msl_hPa=round(tr["msl"].min() / 100.0, 1),
                     ib_min_pres_hPa=ib.loc[common, "pres"].min() if len(common) else np.nan,
                     fc_max_wind_kt=round(tr["wind"].max() * 1.943844),
                     ib_max_wind_kt=ib.loc[common, "usa_wind"].max() if len(common) else np.nan)
            rows.append(r)
    res = pd.DataFrame(rows)
    cols = ["init", "status", "n_tracks", "track", "first_valid", "first_lead_h", "last_lead_h", "dist_first_km"]
    cols += [f"err_{L}h_km" for L in LEADS_H] + ["fc_min_msl_hPa", "ib_min_pres_hPa", "fc_max_wind_kt",
                                               "ib_max_wind_kt", "closest_km"]
    res = res.reindex(columns=[c for c in cols if c in res.columns])
    with pd.option_context("display.width", 200, "display.max_columns", 30):
        print(res.to_string(index=False))
    if a.out:
        res.to_csv(a.out, index=False)
        print("saved", a.out)


if __name__ == "__main__":
    main()
