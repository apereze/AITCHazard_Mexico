"""Run AITCHazard Block 1 AIFS Single v2 smoke or guarded real mode."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from aitchazard.block1.aifs_runner import run_real, run_smoke  # noqa: E402
from aitchazard.block1.config import load_block1_config  # noqa: E402
from aitchazard.block1.io import write_block1_netcdf  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, help="Path to Block 1 YAML configuration.")
    parser.add_argument(
        "--mode",
        choices=("smoke", "real"),
        default="smoke",
        help="Execution mode. Smoke mode is synthetic and does not require credentials.",
    )
    parser.add_argument(
        "--output",
        help="Optional NetCDF output path overriding paths.block1_output in the config.",
    )
    parser.add_argument(
        "--credentials-dir",
        help="Optional credentials directory mounted from the host for real mode.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_block1_config(args.config)

    if args.mode == "smoke":
        ds = run_smoke(config)
    else:
        ds = run_real(config, credentials_dir=args.credentials_dir)

    output_path = Path(args.output) if args.output else config.output_path
    write_block1_netcdf(ds, output_path)
    print(f"Wrote Block 1 NetCDF: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
