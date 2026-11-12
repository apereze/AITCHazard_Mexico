"""Pure helpers for the Block 1 production campaign (no GPU, no earthkit)."""
from __future__ import annotations

import datetime as dt
import json
import os
import socket
from pathlib import Path
from typing import Iterable

from aitchazard.block1.dates import analysis_times, group_by_year_month


def task_keys(inits: Iterable[dt.datetime]) -> list[tuple[int, int]]:
    """(year, month) of every array task, in task-id order."""
    return list(group_by_year_month(inits))


def task_index(inits: Iterable[dt.datetime], year: int, month: int) -> int:
    """Array task id of one (year, month); inverse of dates.task_dates."""
    keys = task_keys(inits)
    try:
        return keys.index((year, month))
    except ValueError as exc:
        raise ValueError(f"{year}-{month:02d} is not in the campaign schedule") from exc


def required_months(task_inits: Iterable[dt.datetime], lag_h: int) -> list[tuple[int, int]]:
    """ERA5 monthly files needed by one task (includes the month holding t0 - lag of the first init)."""
    return sorted({(t.year, t.month) for t in analysis_times(task_inits, lag_h)})


def layout_domains(output_cfg: dict) -> dict[str, dict]:
    """Output domains of the configured layout: split (regional + tempest) or single (extended)."""
    doms = output_cfg["domains"]
    layout = output_cfg["layout"]
    if layout == "split":
        return {k: dict(v) for k, v in doms.items()}
    if layout == "single":
        union = list(dict.fromkeys(doms["regional"]["variables"] + doms["tempest"]["variables"]))
        return {"extended": {**doms["tempest"], "variables": union}}
    raise ValueError(f"layout must be 'split' or 'single', got {layout!r}")


def forecast_path(root: Path | str, domain: str, t0: dt.datetime) -> Path:
    """{root}/{domain}/{YYYY}/{MM}/aifs11_{domain}_{YYYYMMDDHH}.nc"""
    return Path(root) / domain / f"{t0:%Y}" / f"{t0:%m}" / f"aifs11_{domain}_{t0:%Y%m%d%H}.nc"


def static_path(root: Path | str, domain: str) -> Path:
    return Path(root) / domain / f"static_{domain}.nc"


def manifest_path(root: Path | str, year: int, month: int) -> Path:
    return Path(root) / "manifests" / f"{year:04d}-{month:02d}.json"


def pending_inits(root: Path | str, domains: Iterable[str], inits: Iterable[dt.datetime]) -> list[dt.datetime]:
    """Initialisations missing the file of at least one domain."""
    domains = list(domains)
    return [t for t in inits if not all(forecast_path(root, d, t).exists() for d in domains)]


def tmp_name(path: Path) -> Path:
    """Temporary sibling unique per host and process (safe when array tasks share files)."""
    return path.with_name(f"{path.name}.tmp.{socket.gethostname()}.{os.getpid()}")


def write_json_atomic(path: Path, obj: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = tmp_name(path)
    tmp.write_text(json.dumps(obj, indent=2, default=str))
    tmp.replace(path)


def git_commit(repo: Path | str) -> str | None:
    """HEAD commit read from .git directly (git may be absent in the container)."""
    git = Path(repo) / ".git"
    try:
        head = (git / "HEAD").read_text().strip()
        if not head.startswith("ref: "):
            return head  # detached HEAD
        ref = head[5:]
        loose = git / ref
        if loose.exists():
            return loose.read_text().strip()
        for line in (git / "packed-refs").read_text().splitlines():
            if not line.startswith(("#", "^")) and line.endswith(" " + ref):
                return line.split()[0]
    except OSError:
        return None
    return None
