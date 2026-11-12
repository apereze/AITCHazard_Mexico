#!/usr/bin/env python
"""Block 1 production: AIFS Single v1.1 forecasts for one (year, month) task

Usage (inside the container, from the repo root):
    python scripts/block1/run_aifs_month.py --config conf/aitchazard_mexico/block1_aifs_single_v1_1.yaml --task-id 161
    python scripts/block1/run_aifs_month.py --config ... --year-month 2023-05 --dry-run
    python scripts/block1/run_aifs_month.py --config ... --year-month 2023-05 --limit 2

Without --task-id or --year-month the task comes from SLURM_ARRAY_TASK_ID. Forecasts whose
files exist for every domain are skipped, so a task can be resubmitted after a timeout.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import platform
import signal
import socket
import sys
import time
import traceback
from importlib import metadata
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))  # repo src, not the copy installed in the container

import numpy as np
import yaml

from aitchazard.block1.campaign import (
    forecast_path, git_commit, layout_domains, manifest_path, pending_inits,
    required_months, static_path, task_index, write_json_atomic,
)
from aitchazard.block1.dates import init_dates_from_config, task_dates
from aitchazard.block1.era5_inputs import GROUPS, era5_path
from aitchazard.block1.output import G, OutputGrid, check_forecast, write_forecast, write_static

PACKAGES = ("torch", "torch_geometric", "anemoi-inference", "anemoi-models", "anemoi-utils",
            "earthkit-data", "earthkit-regrid", "xarray", "netCDF4", "numpy")
MAX_CONSECUTIVE_FAILURES = 3
GIB = 2**30


def _version(pkg: str):
    try:
        return metadata.version(pkg)
    except metadata.PackageNotFoundError:
        return None


def _rss_peak_gib() -> float | None:
    for line in Path("/proc/self/status").read_text().splitlines():
        if line.startswith("VmHWM"):
            return round(int(line.split()[1]) * 1024 / GIB, 2)
    return None


def _sigterm(signum, frame):
    raise SystemExit(143)  # Slurm time limit: let the finally blocks write the manifest


def parse_args():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--config", type=Path, required=True)
    g = p.add_mutually_exclusive_group()
    g.add_argument("--task-id", type=int)
    g.add_argument("--year-month", help="YYYY-MM, alternative to --task-id")
    p.add_argument("--limit", type=int, default=None, help="run at most N pending forecasts")
    p.add_argument("--dry-run", action="store_true", help="check inputs and pending forecasts; no GPU")
    return p.parse_args()


def resolve_task(inits, a) -> int:
    if a.year_month:
        y, m = (int(x) for x in a.year_month.split("-"))
        return task_index(inits, y, m)
    if a.task_id is not None:
        return a.task_id
    if "SLURM_ARRAY_TASK_ID" in os.environ:
        return int(os.environ["SLURM_ARRAY_TASK_ID"])
    raise SystemExit("give --task-id or --year-month, or run as a Slurm array task")


def run_forecasts(cfg: dict, todo: list, domains: dict, man: dict, mpath: Path) -> None:
    if not todo:
        return
    for k, v in cfg["environment"].get("env", {}).items():
        os.environ.setdefault(k, str(v))  # must be set before CUDA initialisation

    import pandas as pd
    import torch
    from anemoi.inference.runners.simple import SimpleRunner

    from aitchazard.block1.era5_inputs import ERA5Local
    from aitchazard.block1.regrid import Regridder

    sched, ic, out = cfg["schedule"], cfg["initial_conditions"], cfg["output"]
    out_root = Path(out["root"])
    lead_h, step_h = sched["lead_time_hours"], sched["output_step_hours"]
    leads = np.arange(0, lead_h + 1, step_h)
    complevel = out["compression"]["complevel"]
    grid = OutputGrid(domains)
    regrid = Regridder.from_grids("N320", "LL025", box=(grid.bi, grid.bj))  # same weights as earthkit

    def to_box(fields: dict, names) -> dict:
        names = [v for v in names if v in fields]
        return dict(zip(names, regrid(np.stack([np.asarray(fields[v]) for v in names]), dtype=np.float32)))

    man["versions"] = {p: _version(p) for p in PACKAGES}
    man["gpu"] = torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
    t = time.perf_counter()
    runner = SimpleRunner(cfg["model"]["checkpoint_path"], device=cfg["model"]["device"])
    man["timing"]["load_checkpoint_s"] = round(time.perf_counter() - t, 1)
    era5 = ERA5Local(ic["root"], lag_h=ic["lag_hours"])  # chronological order reuses t0 as next t-6 h
    attrs = {"git_commit": man["git_commit"] or "unknown"}
    static_done = all(static_path(out_root, d).exists() for d in domains)
    consecutive = 0

    for t0 in todo:
        rec = {"init": t0.isoformat()}
        w0 = time.perf_counter()
        try:
            state0 = era5.input_state(t0)
            last = {k: v[-1] for k, v in state0["fields"].items()}
            data = {v: np.full((leads.size, *grid.shape), np.nan, np.float32) for v in grid.variables}
            for v, arr in to_box(last, grid.variables).items():
                data[v][0] = arr  # t0 from ERA5; tp, cp, tcc stay NaN
            if not static_done:
                st = to_box(last, ["z", "lsm"])
                static = {"zs": st["z"] / G, "lsm": st["lsm"]}
                for d in domains:
                    write_static(static_path(out_root, d), static, grid, d, complevel)
                static_done = True
            w1 = time.perf_counter()

            n_states = 0
            for state in runner.run(input_state=state0, lead_time=lead_h):
                lead = int((pd.Timestamp(state["date"]) - pd.Timestamp(t0)).total_seconds() // 3600)
                if lead == 0:
                    continue
                for v, arr in to_box(state["fields"], grid.variables).items():
                    data[v][lead // step_h] = arr
                n_states += 1
            w2 = time.perf_counter()

            issues = check_forecast(data)
            if n_states != leads.size - 1:
                issues["n_states"] = n_states
            for d in domains:
                write_forecast(forecast_path(out_root, d, t0), data, grid, d, t0, leads, complevel, attrs)
            w3 = time.perf_counter()

            rec.update(input_s=round(w1 - w0, 2), forecast_s=round(w2 - w1, 2),
                       write_s=round(w3 - w2, 2), total_s=round(w3 - w0, 2))
            man["forecasts"].append(rec)
            man["written"] += 1
            if issues:
                man["issues"][rec["init"]] = issues
            consecutive = 0
            print(f"{t0:%Y-%m-%d %H} UTC: {rec['total_s']:.1f} s" + (f" | issues {issues}" if issues else ""),
                  flush=True)
        except Exception as exc:
            consecutive += 1
            man["failed"].append({"init": rec["init"], "error": repr(exc),
                                  "traceback": traceback.format_exc(limit=8)})
            print(f"{t0:%Y-%m-%d %H} UTC: FAILED {exc!r}", flush=True)
            if consecutive >= MAX_CONSECUTIVE_FAILURES:
                raise RuntimeError(f"{consecutive} consecutive failures; aborting task") from exc
        finally:
            write_json_atomic(mpath, man)  # progress survives a kill

    if man["forecasts"]:
        tot = np.array([r["total_s"] for r in man["forecasts"]])
        man["timing"].update(median_forecast_s=round(float(np.median(tot)), 2),
                             max_forecast_s=round(float(tot.max()), 2),
                             sum_forecasts_h=round(float(tot.sum()) / 3600, 3))
    man["timing"]["rss_peak_gib"] = _rss_peak_gib()
    if torch.cuda.is_available():
        man["timing"]["vram_peak_reserved_gib"] = round(torch.cuda.max_memory_reserved() / GIB, 2)


def main() -> int:
    a = parse_args()
    cfg = yaml.safe_load(a.config.read_text())
    ic, out = cfg["initial_conditions"], cfg["output"]
    inits = init_dates_from_config(cfg)
    task_id = resolve_task(inits, a)
    dates = task_dates(inits, task_id)
    year, month = dates[0].year, dates[0].month
    out_root, era5_root = Path(out["root"]), Path(ic["root"])
    domains = layout_domains(out)
    pending = pending_inits(out_root, domains, dates)
    todo = pending[: a.limit] if a.limit else pending
    months = required_months(dates, ic["lag_hours"])
    era5_files = [era5_path(era5_root, dt.datetime(y, m, 1), g) for y, m in months for g in GROUPS]
    missing = [str(p) for p in era5_files if not p.exists()]

    print(f"task {task_id} = {year}-{month:02d}: {len(dates)} forecasts, {len(dates) - len(pending)} present, "
          f"{len(todo)} to run | layout {out['layout']} {list(domains)}", flush=True)
    print("ERA5 months:", [f"{y}-{m:02d}" for y, m in months], "| missing:", missing or "none", flush=True)
    if a.dry_run:
        return 0 if not missing else 2
    if missing:
        print("ERROR: ERA5 inputs missing; run scripts/block1/download_era5.py first", flush=True)
        return 2

    man = {
        "task_id": task_id, "year_month": f"{year}-{month:02d}", "status": "running",
        "expected": len(dates), "present_before": len(dates) - len(pending), "to_run": len(todo),
        "written": 0, "present_after": None, "failed": [], "issues": {}, "forecasts": [], "timing": {},
        "domains": list(domains), "era5_files": [str(p) for p in era5_files], "config": str(a.config),
        "git_commit": git_commit(REPO), "host": socket.gethostname(), "python": platform.python_version(),
        "slurm": {k: os.environ.get(k) for k in ("SLURM_JOB_ID", "SLURM_ARRAY_JOB_ID", "SLURM_ARRAY_TASK_ID",
                                                 "SLURM_CPUS_PER_TASK", "SLURM_MEM_PER_NODE")},
        "started": dt.datetime.now().isoformat(timespec="seconds"),
    }
    mpath = manifest_path(out_root, year, month)
    signal.signal(signal.SIGTERM, _sigterm)
    status = "failed"
    try:
        run_forecasts(cfg, todo, domains, man, mpath)
        present = len(dates) - len(pending_inits(out_root, domains, dates))
        man["present_after"] = present
        if present == len(dates):
            status = "complete"
        else:
            status = "incomplete" if man["failed"] else "partial"  # partial: --limit without failures
    except SystemExit:
        status = "interrupted"
        raise
    finally:
        man["status"] = status
        man["finished"] = dt.datetime.now().isoformat(timespec="seconds")
        write_json_atomic(mpath, man)
        print(f"status {status}: written {man['written']}, failed {len(man['failed'])}, "
              f"with issues {len(man['issues'])} -> {mpath}", flush=True)
    return 0 if status in ("complete", "partial") else 1


if __name__ == "__main__":
    sys.exit(main())
