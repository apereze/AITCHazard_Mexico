"""Block 1 utilities for retrospective AIFS forecast outputs."""

from .constants import (
    DEFAULT_FORECAST_HORIZON_HOURS,
    DEFAULT_OUTPUT_FREQUENCY_HOURS,
    MEXICO_DOMAIN,
    PRESSURE_LEVELS_HPA,
)
from .config import Block1Config, load_block1_config, validate_block1_config
from .io import validate_block1_dataset, write_block1_netcdf
from .materializer import (
    AIFSStateMaterializer,
    MaterializationResult,
    materialize_state_plans,
)
from .postprocess import add_block1_diagnostics, derive_interval_precipitation, derive_ws10
from .swaither_adapter import to_swaither_lowres, write_swaither_lowres
from .state_builder import build_state_plans, write_state_manifest
from .synthetic import create_synthetic_block1_dataset

__all__ = [
    "Block1Config",
    "AIFSStateMaterializer",
    "DEFAULT_FORECAST_HORIZON_HOURS",
    "DEFAULT_OUTPUT_FREQUENCY_HOURS",
    "MEXICO_DOMAIN",
    "MaterializationResult",
    "PRESSURE_LEVELS_HPA",
    "add_block1_diagnostics",
    "build_state_plans",
    "create_synthetic_block1_dataset",
    "derive_interval_precipitation",
    "derive_ws10",
    "load_block1_config",
    "materialize_state_plans",
    "to_swaither_lowres",
    "validate_block1_config",
    "validate_block1_dataset",
    "write_block1_netcdf",
    "write_state_manifest",
    "write_swaither_lowres",
]
