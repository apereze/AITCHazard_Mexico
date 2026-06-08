"""Convert canonical Block 1 NetCDF output to SwAIther-compatible inputs."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import xarray as xr


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from aitchazard.block1.swaither_adapter import write_swaither_lowres  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Canonical Block 1 NetCDF input.")
    parser.add_argument("--output", required=True, help="SwAIther-compatible NetCDF output.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    ds = xr.open_dataset(args.input)
    output_path = write_swaither_lowres(ds, args.output)
    print(f"Wrote SwAIther-compatible NetCDF: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
