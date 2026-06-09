"""AIFS Single v2 runner boundary.

Smoke mode is implemented locally. Real mode is guarded until MARS credentials
and production input-state retrieval are configured on Curnagl.
"""

from __future__ import annotations

from pathlib import Path

from aitchazard.credentials import check_credentials

from .materializer import materialize_state_plans
from .state_builder import build_state_plans, write_state_manifest
from .synthetic import create_synthetic_block1_dataset


def run_smoke(config):
    """Run the synthetic smoke path."""
    return create_synthetic_block1_dataset(config)


def plan_real_input_states(config, *, manifest_path: str | Path | None = None) -> Path:
    """Write the t-6h/t0 input-state manifest for real AIFS mode."""
    return write_state_manifest(
        build_state_plans(config),
        Path(manifest_path) if manifest_path else config.state_manifest_path,
    )


def materialize_real_input_states(
    config,
    *,
    manifest_path: str | Path | None = None,
    output_path: str | Path | None = None,
):
    """Write the state manifest and materialized t-6h/t0 input-state NetCDF."""

    plans = build_state_plans(config)
    manifest = write_state_manifest(
        plans,
        Path(manifest_path) if manifest_path else config.state_manifest_path,
    )
    materialized = materialize_state_plans(
        plans,
        config.state_source,
        Path(output_path) if output_path else config.materialized_states_path,
    )
    return {
        "manifest": manifest,
        "materialized_states": materialized,
    }


def run_real(
    config,
    *,
    credentials_dir: str | None = None,
    manifest_path: str | Path | None = None,
):
    """Guarded placeholder for real AIFS Single v2 inference."""
    result = check_credentials(
        profile=config.raw.get("credentials", {}).get("profile", "mars"),
        credentials_dir=credentials_dir,
        accepted_files=config.raw.get("credentials", {}).get("accepted_files", (".ecmwfapirc", ".cdsapirc", ".netrc")),
        accepted_env=config.raw.get("credentials", {}).get("accepted_env", ()),
    )
    if not result.ok:
        raise RuntimeError(
            "Real mode requires MARS/ECMWF credentials mounted into the container "
            "or provided via environment variables. " + result.summary()
        )
    mars_files = {".ecmwfapirc", ".cdsapirc", ".netrc"}
    mars_env = {"ECMWF_API_URL", "ECMWF_API_KEY", "ECMWF_API_EMAIL", "CDSAPI_URL", "CDSAPI_KEY"}
    has_mars_file = any(Path(path).name in mars_files for path in result.found_files)
    has_mars_env = any(name in mars_env for name in result.found_env)
    if not (has_mars_file or has_mars_env):
        raise RuntimeError(
            "Real mode requires a MARS/ECMWF/CDS credential handle; HF_TOKEN alone is not sufficient. "
            + result.summary()
        )

    plan_real_input_states(config, manifest_path=manifest_path)

    try:
        from anemoi.inference.config.run import RunConfiguration  # noqa: F401
        from anemoi.inference.runners.default import DefaultRunner  # noqa: F401
    except ImportError as exc:
        raise RuntimeError(
            "Real mode requires anemoi-inference inside the AITCHazard container."
        ) from exc

    raise NotImplementedError(
        "Real AIFS Single v2 inference is intentionally not launched yet. "
        "State materialization is available through --mode materialize-states; "
        "the next implementation step is passing those states to Anemoi."
    )
