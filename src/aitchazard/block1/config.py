"""Configuration helpers for Block 1 execution."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import yaml

from .constants import (
    DEFAULT_FORECAST_HORIZON_HOURS,
    DEFAULT_OUTPUT_FREQUENCY_HOURS,
    MEXICO_DOMAIN,
)


@dataclass(frozen=True)
class Block1Config:
    """Validated Block 1 configuration."""

    raw: dict[str, Any]
    path: Path

    @property
    def checkpoint(self) -> str:
        return self.raw["aifs"]["checkpoint"]

    @property
    def lead_hours(self) -> list[int]:
        return [int(value) for value in self.raw["forecast"]["lead_hours"]]

    @property
    def output_path(self) -> Path:
        return Path(self.raw["paths"]["block1_output"])

    @property
    def swaither_output_path(self) -> Path:
        return Path(self.raw["paths"]["swaither_output"])


def load_block1_config(path: str | Path) -> Block1Config:
    """Load and validate a Block 1 YAML configuration."""
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    validate_block1_config(raw)
    return Block1Config(raw=raw, path=config_path)


def validate_block1_config(raw: dict[str, Any]) -> None:
    """Validate the minimum contract needed by smoke and real modes."""
    required_sections = ("aifs", "domain", "forecast", "variables", "paths")
    missing = [section for section in required_sections if section not in raw]
    if missing:
        raise ValueError(f"Missing required config section(s): {', '.join(missing)}")

    checkpoint = raw["aifs"].get("checkpoint")
    if checkpoint != "ecmwf/aifs-single-2.0":
        raise ValueError("Block 1 must target ecmwf/aifs-single-2.0")

    domain = raw["domain"]
    for key in ("latitude_min", "latitude_max", "longitude_min", "longitude_max"):
        if key not in domain:
            raise ValueError(f"Missing domain key: {key}")
    if domain["latitude_min"] >= domain["latitude_max"]:
        raise ValueError("latitude_min must be lower than latitude_max")
    if domain["longitude_min"] >= domain["longitude_max"]:
        raise ValueError("longitude_min must be lower than longitude_max")
    expected_domain = {
        "latitude_min": MEXICO_DOMAIN["latitude_min"],
        "latitude_max": MEXICO_DOMAIN["latitude_max"],
        "longitude_min": MEXICO_DOMAIN["longitude_360_min"],
        "longitude_max": MEXICO_DOMAIN["longitude_360_max"],
    }
    mismatched_domain = [
        key for key, expected in expected_domain.items() if float(domain[key]) != expected
    ]
    if mismatched_domain:
        raise ValueError(
            "Block 1 config must use the Mexico domain "
            f"{expected_domain}; mismatched: {', '.join(mismatched_domain)}"
        )

    forecast = raw["forecast"]
    if int(forecast.get("output_frequency_hours", 0)) != DEFAULT_OUTPUT_FREQUENCY_HOURS:
        raise ValueError(f"forecast.output_frequency_hours must be {DEFAULT_OUTPUT_FREQUENCY_HOURS}")
    if int(forecast.get("horizon_hours", 0)) != DEFAULT_FORECAST_HORIZON_HOURS:
        raise ValueError(f"forecast.horizon_hours must be {DEFAULT_FORECAST_HORIZON_HOURS}")
    lead_hours = [int(value) for value in forecast.get("lead_hours", [])]
    if not lead_hours:
        raise ValueError("forecast.lead_hours cannot be empty")
    if lead_hours[0] != 0:
        raise ValueError("forecast.lead_hours must start at 0")
    if lead_hours[-1] != DEFAULT_FORECAST_HORIZON_HOURS:
        raise ValueError(f"forecast.lead_hours must end at {DEFAULT_FORECAST_HORIZON_HOURS}")
    expected = list(range(0, DEFAULT_FORECAST_HORIZON_HOURS + 1, DEFAULT_OUTPUT_FREQUENCY_HOURS))
    if lead_hours != expected:
        raise ValueError(f"forecast.lead_hours must be {expected}")

    if "block1_output" not in raw["paths"]:
        raise ValueError("paths.block1_output is required")
    if "swaither_output" not in raw["paths"]:
        raise ValueError("paths.swaither_output is required")
