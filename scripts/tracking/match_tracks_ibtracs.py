"""Match AIFS + TempestExtremes tracks with IBTrACS for whole seasons (TCBench-style matching at t0).

For every initialisation, each IBTrACS storm (NA + EP files, spur tracks removed) with a record at t0 inside the
tracker search domain is matched one-to-one to the nearest stitched track with a node at t0 within --maxdist km
(greedy by distance). Tracks not matched at t0 are tested at their first time in common with any IBTrACS storm:
'late' if a storm is within --maxdist then (genesis inside the forecast or regeneration, e.g. John 2024), 'none'
otherwise (false alarm). A 'late' track may follow a storm already matched at t0 by another track.

Observed intensity: USA_WIND (kt, 1 min); fallback WMO_WIND, divided by 0.88 only when the WMO agency is not
NHC/CPHC (those already report 1-min winds). Pressure: USA_PRES, fallback WMO_PRES.
Forecast wind: StitchNodes 'wind' (max 10 m wind within 2 deg, m/s); fc_vmax_kt = wind * 1.943844 / 0.88
(TCBench convention, not a physical correction). At lead 0 the forecast fields are ERA5 (t0_source: era5).

Outputs (--out-dir):
  matches_long.csv  one row per matched track and lead (0..72 h, 6 h) where forecast or observation exists
  tracks.csv        one row per track: match type, storm, distance at match, first/last lead
  inits.csv         one row per initialisation: tracks, storms at t0 (all / NATURE == TS), hits, misses

Usage (Curnagl, inside the AIFS container; numpy + pandas only):
  python scripts/tracking/match_tracks_ibtracs.py --years 2023 2024 \
    --out-dir $BASE/outputs/tracking/match_d24
"""
import argparse
import os
from pathlib import Path

import numpy as np
import pandas as pd

R_EARTH_KM = 6371.0
MS_TO_KT = 1.943844
K_1MIN = 0.88
LEADS_H = range(0, 73, 6)
ONE_MIN_AGENCIES = {"hurdat_atl", "hurdat_epa", "cphc"}
# DetectNodes search box in te_month.sh (--minlat/--maxlat/--minlon/--maxlon), lon in -180..180
LAT_BOX = (1.5, 38.5)
LON_BOX = (226.5 - 360.0, 303.5 - 360.0)


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


def read_ibtracs(paths, seasons):
    frames = []
    for p in paths:
        # keep_default_na=False: otherwise BASIN "NA" becomes NaN; blanks are coerced below
        ib = pd.read_csv(p, skiprows=[1], low_memory=False, keep_default_na=False, dtype=str)
        frames.append(ib[pd.to_numeric(ib["SEASON"], errors="coerce").isin(seasons)])
    ib = pd.concat(frames, ignore_index=True).drop_duplicates(["SID", "ISO_TIME"])
    tt = ib["TRACK_TYPE"].str.strip()
    ib = ib[~tt.str.contains("spur", case=False)].copy()
    ib["provisional"] = ib["TRACK_TYPE"].str.contains("PROV", case=False)
    ib["t"] = pd.to_datetime(ib["ISO_TIME"])
    ib = ib[ib["t"].dt.hour.isin([0, 6, 12, 18]) & (ib["t"].dt.minute == 0)].copy()  # synoptic times only
    num = lambda c: pd.to_numeric(ib[c].str.strip(), errors="coerce")
    ib["lat"], ib["lon"] = num("LAT"), (num("LON") + 180.0) % 360.0 - 180.0
    wmo_w = num("WMO_WIND")
    wmo_w = wmo_w.where(ib["WMO_AGENCY"].str.strip().isin(ONE_MIN_AGENCIES), wmo_w / K_1MIN)
    ib["vmax_kt"] = num("USA_WIND").fillna(wmo_w)
    ib["pres_hPa"] = num("USA_PRES").fillna(num("WMO_PRES"))
    for c in ("NAME", "BASIN", "NATURE"):
        ib[c.lower()] = ib[c].str.strip()
    ib["in_box"] = ib["lat"].between(*LAT_BOX) & ib["lon"].between(*LON_BOX)
    return ib[["SID", "name", "basin", "nature", "provisional", "t", "lat", "lon", "vmax_kt", "pres_hPa",
               "in_box"]].reset_index(drop=True)


def match_init(tracks, ib_t, ini, maxdist):
    """Return {track index: (SID, distance km, match type, match time)} and the SIDs at t0 not matched."""
    s0 = ib_t.get(ini, pd.DataFrame(columns=["SID"]))
    s0 = s0[s0["in_box"]] if len(s0) else s0
    cands = []
    for k, tr in enumerate(tracks):
        if ini in tr.index and len(s0):
            d = haversine_km(tr.at[ini, "lon"], tr.at[ini, "lat"], s0["lon"].values, s0["lat"].values)
            cands += [(dj, k, sid) for dj, sid in zip(d, s0["SID"].values) if dj <= maxdist]
    pairs, used_st = {}, set()
    for d, k, sid in sorted(cands):  # greedy one-to-one by distance
        if k not in pairs and sid not in used_st:
            pairs[k] = (sid, d, "t0", ini)
            used_st.add(sid)
    for k, tr in enumerate(tracks):  # late matches: first common time with any storm within maxdist
        if k in pairs:
            continue
        for t in tr.index:
            st = ib_t.get(t)
            if st is None or not len(st):
                continue
            d = haversine_km(tr.at[t, "lon"], tr.at[t, "lat"], st["lon"].values, st["lat"].values)
            j = int(np.argmin(d))
            if d[j] <= maxdist:
                pairs[k] = (st["SID"].values[j], d[j], "late", t)
                break
    missed = [s for s in s0["SID"].values if s not in used_st] if len(s0) else []
    return pairs, missed, s0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    base = Path(os.environ.get("BASE", "/work/FAC/FGSE/IDYST/tbeucler/default/apereze"))
    ap.add_argument("--years", type=int, nargs="+", required=True)
    ap.add_argument("--months", type=int, nargs="+", default=list(range(5, 12)))
    ap.add_argument("--tracks-root", type=Path, default=base / "outputs/tracking/te_tcbench")
    ap.add_argument("--ibtracs", type=Path, nargs="+",
                    default=[base / "data/ibtracs/ibtracs.NA.list.v04r01.csv",
                             base / "data/ibtracs/ibtracs.EP.list.v04r01.csv"])
    ap.add_argument("--maxdist", type=float, default=500.0, help="matching distance (km)")
    ap.add_argument("--out-dir", type=Path, required=True)
    a = ap.parse_args()
    a.out_dir.mkdir(parents=True, exist_ok=True)

    ib = read_ibtracs(a.ibtracs, a.years)
    ib_t = {t: g for t, g in ib.groupby("t")}
    ib_s = {s: g.set_index("t") for s, g in ib.groupby("SID")}
    print(f"IBTrACS: {ib['SID'].nunique()} storms in {a.years}, provisional rows: {int(ib['provisional'].sum())}")

    rows, trows, irows = [], [], []
    for y in a.years:
        for m in a.months:
            files = sorted((a.tracks_root / f"{y}" / f"{m:02d}").glob("aifs11_tempest_*_tracks.txt"))
            if not files:
                print(f"{y}-{m:02d}: no track files")
            for f in files:
                ini = pd.to_datetime(f.name.split("_")[2], format="%Y%m%d%H")
                tracks = read_tracks(f)
                pairs, missed, s0 = match_init(tracks, ib_t, ini, a.maxdist)
                n_ts = int((s0["nature"] == "TS").sum()) if len(s0) else 0
                hit_sids = {v[0] for v in pairs.values() if v[2] == "t0"}
                irows.append(dict(init=ini, n_tracks=len(tracks), n_storms_t0=len(s0), n_storms_t0_TS=n_ts,
                                  hits_t0=len(hit_sids),
                                  hits_t0_TS=int(s0[s0["SID"].isin(hit_sids)]["nature"].eq("TS").sum()) if len(s0) else 0,
                                  misses_t0=len(missed),
                                  late=sum(v[2] == "late" for v in pairs.values()),
                                  unmatched=len(tracks) - len(pairs),
                                  missed=";".join(ib_s[s]["name"].iloc[0] for s in missed)))
                for k, tr in enumerate(tracks):
                    lead = (tr.index - ini) / pd.Timedelta(hours=1)
                    sid, d, mtype, tm = pairs.get(k, (None, np.nan, "none", pd.NaT))
                    obs = ib_s[sid] if sid else None
                    trows.append(dict(init=ini, track=k, match=mtype, SID=sid,
                                      name=obs["name"].iloc[0] if sid else None,
                                      basin=obs["basin"].iloc[0] if sid else None,
                                      dist_match_km=round(d) if np.isfinite(d) else np.nan, t_match=tm,
                                      first_lead_h=int(lead.min()), last_lead_h=int(lead.max()),
                                      first_lon=tr["lon"].iloc[0], first_lat=tr["lat"].iloc[0]))
                    if sid is None:
                        continue
                    ob0 = obs.loc[ini] if ini in obs.index else None
                    fc0 = tr.loc[ini] if ini in tr.index else None
                    for L in LEADS_H:
                        t = ini + pd.Timedelta(hours=L)
                        if mtype == "late" and t < tm:
                            continue
                        fc = tr.loc[t] if t in tr.index else None
                        ob = obs.loc[t] if t in obs.index else None
                        if fc is None and ob is None:
                            continue
                        r = dict(init=ini, track=k, match=mtype, SID=sid, name=obs["name"].iloc[0],
                                 basin=obs["basin"].iloc[0], lead_h=L, valid=t)
                        if fc is not None:
                            r.update(fc_lon=fc["lon"], fc_lat=fc["lat"], fc_msl_hPa=fc["msl"] / 100.0,
                                     fc_wind_ms=fc["wind"], fc_vmax_kt=fc["wind"] * MS_TO_KT / K_1MIN)
                        if ob is not None:
                            r.update(ob_lon=ob["lon"], ob_lat=ob["lat"], ob_vmax_kt=ob["vmax_kt"],
                                     ob_pres_hPa=ob["pres_hPa"], ob_nature=ob["nature"],
                                     ob_provisional=bool(ob["provisional"]))
                        if fc is not None and ob is not None:
                            r["dist_km"] = haversine_km(fc["lon"], fc["lat"], ob["lon"], ob["lat"])
                        if ob0 is not None:  # observed and analysed (ERA5) intensity at t0: predictors
                            r.update(ob_vmax_kt_t0=ob0["vmax_kt"], ob_pres_hPa_t0=ob0["pres_hPa"])
                        if fc0 is not None:
                            r.update(fc_vmax_kt_t0=fc0["wind"] * MS_TO_KT / K_1MIN, fc_msl_hPa_t0=fc0["msl"] / 100.0)
                        rows.append(r)

    long, trk, inits = pd.DataFrame(rows), pd.DataFrame(trows), pd.DataFrame(irows)
    if long.empty:
        raise SystemExit("no matched tracks")
    long["err_vmax_kt"] = long["fc_vmax_kt"] - long["ob_vmax_kt"]
    long["err_pres_hPa"] = long["fc_msl_hPa"] - long["ob_pres_hPa"]
    for name, df in (("matches_long", long), ("tracks", trk), ("inits", inits)):
        df.to_csv(a.out_dir / f"{name}.csv", index=False, float_format="%.3f")

    # Console summary
    inits["ym"] = inits["init"].dt.strftime("%Y-%m")
    trk["ym"] = trk["init"].dt.strftime("%Y-%m")
    s = inits.groupby("ym").agg(forecasts=("init", "size"), storm_inits_TS=("n_storms_t0_TS", "sum"),
                                hits_TS=("hits_t0_TS", "sum"), storm_inits=("n_storms_t0", "sum"),
                                hits=("hits_t0", "sum"), late=("late", "sum"), false_alarms=("unmatched", "sum"))
    s["POD_TS"] = (s["hits_TS"] / s["storm_inits_TS"]).round(2)
    print("\nDetection at t0 (TS = IBTrACS NATURE TS at t0):")
    print(s.to_string())
    t0 = long[(long["match"] == "t0") & long["dist_km"].notna() & (long["ob_nature"] == "TS")]
    g = t0.groupby("lead_h").agg(n=("dist_km", "size"), track_med_km=("dist_km", "median"),
                                 vmax_bias_kt=("err_vmax_kt", "mean"), vmax_mae_kt=("err_vmax_kt", lambda e: e.abs().mean()),
                                 pres_bias_hPa=("err_pres_hPa", "mean"), n_storms=("SID", "nunique"))
    print("\nt0 matches, NATURE TS at the valid time, error by lead (fc - obs; wind /0.88):")
    print(g.round(1).to_string())
    print(f"\nsaved {a.out_dir}/matches_long.csv, tracks.csv, inits.csv")


if __name__ == "__main__":
    main()
