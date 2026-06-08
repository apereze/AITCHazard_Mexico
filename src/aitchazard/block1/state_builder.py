"""AIFS Single v2 input-state planning for Block 1.

The legacy state runners proved the Anemoi/MARS/Zarr mechanics, but they mixed
date selection, state retrieval, model execution, and output writing. This
module keeps the first production step small and inspectable: build the
declarative t-6h/t0 state plan that a future materializer will retrieve.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from typing import Any

from .config import Block1Config
from .constants import PRESSURE_LEVELS_HPA, SURFACE_VARIABLES


@dataclass(frozen=True)
class StatePlan:
    """Declarative input-state plan for one AIFS initialization."""

    checkpoint: str
    init_time: datetime
    analysis_times: tuple[datetime, datetime]
    lead_hours: tuple[int, ...]
    domain: dict[str, Any]
    surface_variables: tuple[str, ...]
    pressure_families: tuple[str, ...]
    pressure_levels_hpa: tuple[int, ...]
    state_lag_hours: int
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def required_pressure_fields(self) -> tuple[str, ...]:
        return tuple(
            f"{family}_{level}"
            for family in self.pressure_families
            for level in self.pressure_levels_hpa
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "checkpoint": self.checkpoint,
            "init_time": _format_utc(self.init_time),
            "analysis_times": [_format_utc(value) for value in self.analysis_times],
            "lead_hours": list(self.lead_hours),
            "domain": self.domain,
            "state_lag_hours": self.state_lag_hours,
            "required_fields": {
                "surface": list(self.surface_variables),
                "pressure_families": list(self.pressure_families),
                "pressure_levels_hpa": list(self.pressure_levels_hpa),
                "pressure_level": list(self.required_pressure_fields),
            },
            "metadata": self.metadata,
        }


def build_state_plans(config: Block1Config) -> list[StatePlan]:
    """Build one t-6h/t0 state plan per configured initialization time."""

    variables = config.raw["variables"]
    surface_variables = tuple(variables.get("surface", SURFACE_VARIABLES))
    pressure_families = tuple(variables.get("pressure_families", ("t", "u", "v", "z", "q")))
    pressure_levels = tuple(
        int(value) for value in variables.get("pressure_levels_hpa", PRESSURE_LEVELS_HPA)
    )

    plans = []
    for raw_init_time in config.init_times:
        init_time = parse_utc_datetime(raw_init_time)
        previous_time = init_time - timedelta(hours=config.state_lag_hours)
        plan = StatePlan(
            checkpoint=config.checkpoint,
            init_time=init_time,
            analysis_times=(previous_time, init_time),
            lead_hours=tuple(config.lead_hours),
            domain=dict(config.raw["domain"]),
            surface_variables=surface_variables,
            pressure_families=pressure_families,
            pressure_levels_hpa=pressure_levels,
            state_lag_hours=config.state_lag_hours,
            metadata={
                "purpose": "AIFS Single v2 MARS input-state plan for Block 1",
                "source": "config-driven replacement for legacy state_runner prototypes",
            },
        )
        validate_state_plan(plan)
        plans.append(plan)

    return plans


def validate_state_plan(plan: StatePlan) -> None:
    """Validate the t-6h/t0 state relationship and required field groups."""

    expected_previous_time = plan.init_time - timedelta(hours=plan.state_lag_hours)
    if plan.analysis_times != (expected_previous_time, plan.init_time):
        raise ValueError("State plan must contain init_time - lag and init_time")
    if not plan.lead_hours or plan.lead_hours[0] != 0:
        raise ValueError("State plan lead_hours must start at 0")
    if not plan.surface_variables:
        raise ValueError("State plan requires at least one surface variable")
    if not plan.pressure_families:
        raise ValueError("State plan requires pressure families")
    if not plan.pressure_levels_hpa:
        raise ValueError("State plan requires pressure levels")


def state_manifest_payload(plans: list[StatePlan]) -> dict[str, Any]:
    return {
        "schema": "aitchazard.block1.state-plan.v1",
        "plan_count": len(plans),
        "plans": [plan.to_dict() for plan in plans],
    }


def write_state_manifest(plans: list[StatePlan], path: str | Path) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(state_manifest_payload(plans), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_path


def parse_utc_datetime(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        dt = datetime.fromisoformat(text)

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _format_utc(value: datetime) -> str:
    dt = value.astimezone(timezone.utc).replace(tzinfo=None)
    return dt.isoformat(timespec="seconds") + "Z"
