"""Initialisation calendar for Block 1 retrospective AIFS forecasts."""
from __future__ import annotations

import datetime as dt
from collections import defaultdict
from typing import Iterable


def init_dates(
    years: Iterable[int], month_start: int = 5, month_end: int = 11, freq_h: int = 6
) -> list[dt.datetime]:
    """All cycles from {month_start}-01 00 UTC to the last cycle of month_end, every freq_h."""
    step = dt.timedelta(hours=freq_h)
    out: list[dt.datetime] = []
    for year in years:
        t = dt.datetime(year, month_start, 1)
        end = dt.datetime(year + 1, 1, 1) if month_end == 12 else dt.datetime(year, month_end + 1, 1)
        while t < end:
            out.append(t)
            t += step
    return out


def init_dates_from_config(cfg: dict) -> list[dt.datetime]:
    """Build the initialisation list from the Block 1 YAML config."""
    s = cfg["schedule"]
    y0, y1 = s["years"]
    m0, m1 = s["months"]
    return init_dates(range(y0, y1 + 1), m0, m1, s["init_frequency_hours"])


def analysis_times(inits: Iterable[dt.datetime], lag_h: int = 6) -> list[dt.datetime]:
    """Unique ERA5 analysis times required (t - lag and t0 of every initialisation)."""
    lag = dt.timedelta(hours=lag_h)
    need: set[dt.datetime] = set()
    for d in inits:
        need.update((d - lag, d))
    return sorted(need)


def group_by_year_month(times: Iterable[dt.datetime]) -> dict[tuple[int, int], list[dt.datetime]]:
    """Group times by (year, month), sorted."""
    groups: dict[tuple[int, int], list[dt.datetime]] = defaultdict(list)
    for t in times:
        groups[(t.year, t.month)].append(t)
    return {k: sorted(v) for k, v in sorted(groups.items())}


def task_dates(inits: Iterable[dt.datetime], task_id: int) -> list[dt.datetime]:
    """SLURM array mapping: task_id -> initialisations of one (year, month)."""
    return list(group_by_year_month(inits).values())[task_id]


def n_tasks(inits: Iterable[dt.datetime]) -> int:
    """Number of (year, month) tasks; use --array=0-(n_tasks-1)."""
    return len(group_by_year_month(inits))
