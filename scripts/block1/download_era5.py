"""Stage ERA5 initial conditions monthly from CDS

Usage:
    python scripts/block1/download_era5.py --config conf/aitchazard_mexico/block1_aifs_single_v1_1.yaml --year 2005
    python scripts/block1/download_era5.py --config ... --year 2005 --dry-run
    python scripts/block1/download_era5.py --config ... --year 2023 --months 5 --dry-run
"""
from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

import yaml

from aitchazard.block1.dates import analysis_times, group_by_year_month, init_dates
from aitchazard.block1.era5_inputs import era5_path
from aitchazard.block1.era5_params import (
    GROUP_PARAMS,
    build_monthly_cds_request,
    translate_params_to_cds,
)


def monthly_blocks(year: int, cfg: dict, months: list[int] | None = None):
    """(year, month, days, hours) blocks covering all analysis times of one season.

    With `months`, keep the blocks of those months plus the full-season block of the
    preceding month (holds the t0 - lag analyses of the first inits). Blocks are never
    trimmed, so a monthly file has the same content however it was requested and the
    existence-based skip stays valid.
    """
    s = cfg["schedule"]
    inits = init_dates([year], s["months"][0], s["months"][1], s["init_frequency_hours"])
    times = analysis_times(inits, cfg["initial_conditions"]["lag_hours"])
    blocks = group_by_year_month(times)
    if months is not None:
        missing = [m for m in months if (year, m) not in blocks]
        if missing:
            raise SystemExit(f"months {missing} not in the {year} season schedule")
        need = set()
        for m in months:
            need.add((year, m))
            need.add((year, m - 1) if m > 1 else (year - 1, 12))
        blocks = {k: v for k, v in blocks.items() if k in need}
    for (y, m), ts in sorted(blocks.items()):
        days = sorted({f"{t.day:02d}" for t in ts})
        hours = sorted({f"{t.hour:02d}:00" for t in ts})
        yield y, m, days, hours


def main(config: Path, year: int, months: list[int] | None, dry_run: bool) -> None:
    cfg = yaml.safe_load(config.read_text())
    ic = cfg["initial_conditions"]
    root = Path(ic["root"])
    client = None
    if not dry_run:
        import cdsapi  # only needed on the download node
        client = cdsapi.Client()

    for y, m, days, hours in monthly_blocks(year, cfg, months):
        t_ref = dt.datetime(y, m, 1)
        for group, (params, levels) in GROUP_PARAMS.items():
            target = era5_path(root, t_ref, group)
            if target.exists():
                print(f"{y}-{m:02d} {group}: exists, skip -> {target}")
                continue  # idempotent
            dataset, variables, pl_levels = translate_params_to_cds(
                source=group, param=params, levelist=levels
            )
            request = build_monthly_cds_request(
                year=y, month=m, days=days, hours=hours, variables=variables,
                pressure_levels=pl_levels, grid=tuple(ic["grid"]),
            )
            n_fields = len(variables) * len(days) * len(hours) * max(len(pl_levels), 1)
            print(f"{y}-{m:02d} {group}: {len(days)} days x {len(hours)} times, {n_fields} fields -> {target}")
            if dry_run:
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            tmp = target.with_suffix(".grib.tmp")
            t_start = dt.datetime.now()
            client.retrieve(dataset, request, str(tmp))
            tmp.rename(target)  # atomic: partial downloads never look complete
            print(f"  done in {dt.datetime.now() - t_start}", flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--year", type=int, required=True)
    p.add_argument("--months", type=int, nargs="+", default=None,
                   help="restrict to these months (plus the preceding month's block)")
    p.add_argument("--dry-run", action="store_true", help="print requests without downloading")
    a = p.parse_args()
    main(a.config, a.year, a.months, a.dry_run)
