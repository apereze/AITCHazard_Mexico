"""Run AITCHazard Block 1 AIFS Single v2 smoke or guarded real mode."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from aitchazard.block1.aifs_runner import (  # noqa: E402
    materialize_real_input_states,
    plan_real_input_states,
    run_real,
    run_smoke,
)
from aitchazard.block1.config import load_block1_config  # noqa: E402
from aitchazard.block1.io import write_block1_netcdf  # noqa: E402
from aitchazard.block1.materializer import MaterializationError  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, help="Path to Block 1 YAML configuration.")
    parser.add_argument(
        "--mode",
        choices=("smoke", "plan-states", "materialize-states", "real"),
        default="smoke",
        help=(
            "Execution mode. plan-states writes the t-6h/t0 manifest only; "
            "materialize-states also writes a compact input-state NetCDF."
        ),
    )
    parser.add_argument(
        "--output",
        help="Optional NetCDF output path overriding paths.block1_output in the config.",
    )
    parser.add_argument(
        "--credentials-dir",
        help="Optional credentials directory mounted from the host for real mode.",
    )
    parser.add_argument(
        "--state-manifest",
        help="Optional JSON path for the real-mode t-6h/t0 state manifest.",
    )
    parser.add_argument(
        "--states-output",
        help="Optional NetCDF path for materialized t-6h/t0 input states.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_block1_config(args.config)

    if args.mode == "smoke":
        ds = run_smoke(config)
        output_path = Path(args.output) if args.output else config.output_path
        write_block1_netcdf(ds, output_path)
        print(f"Wrote Block 1 NetCDF: {output_path}")
        return 0

    if args.mode == "plan-states":
        manifest_path = plan_real_input_states(config, manifest_path=args.state_manifest)
        print(f"Wrote Block 1 state manifest: {manifest_path}")
        return 0

    if args.mode == "materialize-states":
        try:
            result = materialize_real_input_states(
                config,
                manifest_path=args.state_manifest,
                output_path=args.states_output,
            )
        except MaterializationError as exc:
            print(f"State materialization failed: {exc}", file=sys.stderr)
            return 2

        materialized = result["materialized_states"]
        print(f"Wrote Block 1 state manifest: {result['manifest']}")
        print(f"Wrote materialized AIFS states: {materialized.output_path}")
        print(
            "Materialized "
            f"{materialized.variable_count} variables for "
            f"{len(materialized.analysis_times)} analysis times."
        )
        return 0

    run_real(
        config,
        credentials_dir=args.credentials_dir,
        manifest_path=args.state_manifest,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
