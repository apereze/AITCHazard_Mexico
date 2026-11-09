"""Preflight del benchmark de un día del bloque 1: versiones, accesos y pre-descarga.

Correr en el nodo de login, dentro del contenedor (sin GPU):
    BASE=/work/FAC/FGSE/IDYST/tbeucler/default/apereze
    apptainer exec --bind /work --env PYTHONPATH=$BASE/aifs/pylibs/aifs11 $BASE/aifs/aifs_single_v2_era5.sif \
        python scripts/block1/bench_preflight.py --base $BASE --day 2005-05-15 --try-load
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
from importlib import metadata
from pathlib import Path

import numpy as np
import yaml

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))  # código del repo, no la copia instalada en el contenedor

from aitchazard.block1.dates import analysis_times  # noqa: E402
from aitchazard.block1.era5_inputs import era5_path  # noqa: E402
from aitchazard.block1.era5_params import (  # noqa: E402
    GROUP_PARAMS,
    build_monthly_cds_request,
    translate_params_to_cds,
)

PKGS = ("torch", "anemoi-inference", "anemoi-models", "anemoi-utils", "earthkit-data", "earthkit-regrid",
        "eccodes", "cdsapi", "flash-attn", "huggingface-hub", "xarray", "netCDF4", "nbconvert", "ipykernel")
CKPT_NAME = "aifs-single-mse-1.1.ckpt"  # único .ckpt en ecmwf/aifs-single-1.1


def report(tag: str, ok: bool, msg: str = "") -> bool:
    print(f"[{'OK' if ok else 'FALLA'}] {tag} {msg}")
    return ok


def check_versions() -> None:
    for p in PKGS:
        try:
            print(f"  {p:18s} {metadata.version(p)}")
        except metadata.PackageNotFoundError:
            print(f"  {p:18s} -- no instalado")


def check_paths(base: Path) -> bool:
    ok = report("base visible en el contenedor", base.is_dir(), str(base))
    probe = base / "benchmarks" / ".write_test"
    try:
        probe.parent.mkdir(parents=True, exist_ok=True)
        probe.write_text("ok")
        probe.unlink()
        ok &= report("escritura en benchmarks/", True)
    except OSError as err:
        ok &= report("escritura en benchmarks/", False, repr(err))
    ok &= report("~/.cdsapirc", (Path.home() / ".cdsapirc").exists(), str(Path.home()))
    return ok


def stage_checkpoint(dest: Path, repo_id: str) -> bool:
    if not dest.exists():
        from huggingface_hub import hf_hub_download
        dest.parent.mkdir(parents=True, exist_ok=True)
        hf_hub_download(repo_id=repo_id, filename=CKPT_NAME, local_dir=dest.parent)
    return report("checkpoint", dest.exists(), f"{dest} ({dest.stat().st_size / 1e9:.2f} GB)" if dest.exists() else "")


def try_load(dest: Path) -> bool:
    # Deserializa en CPU: falla aquí igual que fallaría en el runner (p. ej., flash_attn ausente)
    import torch
    try:
        torch.load(dest, map_location="cpu", weights_only=False)
        return report("checkpoint deserializa en CPU", True)
    except Exception as err:
        return report("checkpoint deserializa en CPU", False, f"{type(err).__name__}: {err}")


def stage_era5_day(root: Path, day: dt.date, cfg: dict) -> bool:
    import cdsapi
    inits = [dt.datetime(day.year, day.month, day.day, h) for h in (0, 6, 12, 18)]
    times = analysis_times(inits, cfg["initial_conditions"]["lag_hours"])
    if {(t.year, t.month) for t in times} != {(day.year, day.month)}:
        return report("ERA5", False, "elegir un día distinto del 1 (t-6 h cae en el mes previo)")
    days = sorted({f"{t.day:02d}" for t in times})
    hours = sorted({f"{t.hour:02d}:00" for t in times})
    ref = dt.datetime(day.year, day.month, 1)
    client = None
    for group, (params, levels) in GROUP_PARAMS.items():
        target = era5_path(root, ref, group)
        if target.exists():
            continue
        client = client or cdsapi.Client()
        dataset, variables, pl = translate_params_to_cds(source=group, param=params, levelist=levels)
        req = build_monthly_cds_request(year=day.year, month=day.month, days=days, hours=hours,
                                        variables=variables, pressure_levels=pl,
                                        grid=tuple(cfg["initial_conditions"]["grid"]))
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(".grib.tmp")
        client.retrieve(dataset, req, str(tmp))
        tmp.rename(target)  # atómico
    sizes = {g: era5_path(root, ref, g).stat().st_size / 1e9 for g in GROUP_PARAMS}
    return report("ERA5 del día", True, " ".join(f"{g}={s:.2f}GB" for g, s in sizes.items()))


def warm_regrid() -> bool:
    # earthkit-regrid descarga las matrices de interpolación la primera vez y las guarda en caché
    import earthkit.regrid as ekr
    x = ekr.interpolate(np.zeros((721, 1440)), {"grid": (0.25, 0.25)}, {"grid": "N320"})
    y = ekr.interpolate(x, {"grid": "N320"}, {"grid": (0.25, 0.25)})
    return report("matrices earthkit-regrid", x.shape == (542080,) and y.shape == (721, 1440),
                  f"{x.shape} / {y.shape}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--base", type=Path, required=True)
    p.add_argument("--day", type=dt.date.fromisoformat, default=dt.date(2005, 5, 15))
    p.add_argument("--config", type=Path, default=REPO / "conf/aitchazard_mexico/block1_aifs_single_v1_1.yaml")
    p.add_argument("--try-load", action="store_true", help="deserializar el checkpoint en CPU (~1 GB de RAM)")
    a = p.parse_args()

    cfg = yaml.safe_load(a.config.read_text())
    ckpt = a.base / "aifs/checkpoints" / CKPT_NAME  # misma ruta que usa el notebook 02
    check_versions()
    ok = check_paths(a.base)
    ok &= stage_checkpoint(ckpt, cfg["model"]["huggingface_repo"])
    if a.try_load:
        ok &= try_load(ckpt)
    ok &= stage_era5_day(a.base / "benchmarks/era5_day", a.day, cfg)  # misma ruta que usa el notebook 02
    ok &= warm_regrid()
    print("\nPREFLIGHT", "OK" if ok else "CON FALLAS")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
