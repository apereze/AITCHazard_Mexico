"""TC cases per season in the Block 1 regional domain from IBTrACS (NA + EP), plus two checks.

Counts systems with at least one synoptic fix (00/06/12/18 UTC) inside 5-35 N, 230-300 E
(-130..-60 E) between 1 May and 30 November, and how many of them reach 34 kt (USA_WIND)
inside the domain. Checks: systems active in May 2023 (pilot month) and Eugene 2005 near
the node found on 2005-07-18 18 UTC (16.0 N, 104.75 W).
Usage: python scripts/tracking/ibtracs_counts.py $BASE/data/ibtracs
"""
import sys
from pathlib import Path

import pandas as pd

COLS = ["SID", "SEASON", "BASIN", "NAME", "ISO_TIME", "NATURE", "LAT", "LON", "USA_WIND"]
root = Path(sys.argv[1])
df = pd.concat(
    pd.read_csv(root / f"ibtracs.{b}.list.v04r01.csv", usecols=COLS, skiprows=[1],
                keep_default_na=False, low_memory=False) for b in ("NA", "EP"))
df["t"] = pd.to_datetime(df["ISO_TIME"])
for c in ("LAT", "LON", "USA_WIND"):
    df[c] = pd.to_numeric(df[c], errors="coerce")
df = df[(df.t.dt.minute == 0) & (df.t.dt.hour % 6 == 0)].drop_duplicates(["SID", "t"])

dom = df[df.LAT.between(5, 35) & df.LON.between(-130, -60) & df.t.dt.month.between(5, 11)]
g = dom.groupby("SID").agg(year=("t", lambda s: s.dt.year.min()), basin=("BASIN", "first"),
                           vmax=("USA_WIND", "max"))
tab = pd.crosstab(g.year, g.basin)
tab["all"] = tab.sum(axis=1)
tab["ts_in_domain"] = g[g.vmax >= 34].groupby("year").size()
tab = tab.reindex(range(2000, 2026)).fillna(0).astype(int)  # years without cases count as 0
print("Systems with >= 1 fix in the regional domain, May-Nov (NA + EP):")
print(tab.to_string())
print("\nmean 2000-2022:", tab.loc[2000:2022, ["all", "ts_in_domain"]].mean().round(1).to_dict())
print("2023-2025:", tab.loc[2023:2025, ["all", "ts_in_domain"]].to_dict("index"))

may = df[(df.t >= "2023-05-01") & (df.t < "2023-06-01")]
print("\nActive May 2023 (any basin in NA/EP):", sorted(set(may.NAME + " " + may.SID)) or "none")

eu = df[(df.NAME == "EUGENE") & (df.SEASON.astype(str) == "2005")]
print("\nEugene 2005, first fixes:")
print(eu[["t", "LAT", "LON", "USA_WIND", "NATURE"]].head(6).to_string(index=False))
near = eu[(eu.t == "2005-07-18 18:00")]
print("at 2005-07-18 18 UTC:", near[["LAT", "LON", "USA_WIND"]].to_dict("records") or "no fix")
