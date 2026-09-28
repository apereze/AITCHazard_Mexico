"""ERA5/CDS parameter mappings for AIFS Single v1.1 initial conditions.

Migrated from the prototype notebook. Changes with respect to the notebook:
- PARAM_PL_CDS now contains "z" (the notebook requested "z" but only mapped "gh").
- build_monthly_cds_request added for month-level retrievals.
"""
from __future__ import annotations

from typing import Iterable

# Open Data/MARS shortName -> ERA5 CDS variable name
PARAM_SFC_CDS = {
    "10u": "10m_u_component_of_wind",
    "10v": "10m_v_component_of_wind",
    "2d": "2m_dewpoint_temperature",
    "2t": "2m_temperature",
    "msl": "mean_sea_level_pressure",
    "skt": "skin_temperature",
    "sp": "surface_pressure",
    "tcw": "total_column_water",
    "lsm": "land_sea_mask",
    "z": "geopotential",
    "slor": "slope_of_sub_gridscale_orography",
    "sdor": "standard_deviation_of_orography",
}

PARAM_SOIL_CDS = {
    "vsw": {1: "volumetric_soil_water_layer_1", 2: "volumetric_soil_water_layer_2"},
    "sot": {1: "soil_temperature_level_1", 2: "soil_temperature_level_2"},
}

PARAM_PL_CDS = {
    "z": "geopotential",   # ERA5 provides geopotential directly (m2 s-2); no g scaling
    "gh": "geopotential",  # kept for backwards compatibility; not used with ERA5
    "t": "temperature",
    "u": "u_component_of_wind",
    "v": "v_component_of_wind",
    "w": "vertical_velocity",
    "q": "specific_humidity",
}

CDS_DATASETS = {
    "sfc": "reanalysis-era5-single-levels",
    "soil": "reanalysis-era5-single-levels",
    "pl": "reanalysis-era5-pressure-levels",
}

PARAM_SFC = ["10u", "10v", "2d", "2t", "msl", "skt", "sp", "tcw", "lsm", "z", "slor", "sdor"]
PARAM_SOIL = ["vsw", "sot"]
PARAM_PL = ["z", "t", "u", "v", "w", "q"]
LEVELS = [1000, 925, 850, 700, 600, 500, 400, 300, 250, 200, 150, 100, 50]
SOIL_LEVELS = [1, 2]

GROUP_PARAMS = {
    "sfc": (PARAM_SFC, None),
    "pl": (PARAM_PL, LEVELS),
    "soil": (PARAM_SOIL, SOIL_LEVELS),
}


def _as_list(x: str | Iterable[str]) -> list[str]:
    """Convert a string or iterable of strings into a list."""
    return [x] if isinstance(x, str) else list(x)


def translate_params_to_cds(
    *, source: str, param: str | Iterable[str], levelist: Iterable[int] | None = None
) -> tuple[str, list[str], list[int]]:
    """Translate Open Data/MARS-style parameters to CDS dataset and variable names.

    Returns (dataset, cds_variables, pressure_levels). Pressure levels are only
    returned for source="pl"; soil layers are expanded into distinct variables.
    """
    params = _as_list(param)
    levels = list(levelist) if levelist is not None else []
    if source not in CDS_DATASETS:
        raise ValueError(f"source must be one of {list(CDS_DATASETS)}, got {source!r}")
    dataset = CDS_DATASETS[source]

    if source == "sfc":
        missing = [p for p in params if p not in PARAM_SFC_CDS]
        if missing:
            raise ValueError(f"Surface parameters without CDS mapping: {missing}")
        if levels:
            raise ValueError("source='sfc' does not accept levelist.")
        return dataset, [PARAM_SFC_CDS[p] for p in params], []

    if source == "pl":
        missing = [p for p in params if p not in PARAM_PL_CDS]
        if missing:
            raise ValueError(f"Pressure-level parameters without CDS mapping: {missing}")
        if not levels:
            raise ValueError("source='pl' requires levelist.")
        return dataset, [PARAM_PL_CDS[p] for p in params], levels

    # soil
    missing = [p for p in params if p not in PARAM_SOIL_CDS]
    if missing:
        raise ValueError(f"Soil parameters without CDS mapping: {missing}")
    if not levels:
        raise ValueError("source='soil' requires levelist, e.g. [1, 2].")
    variables = []
    for p in params:
        for level in levels:
            try:
                variables.append(PARAM_SOIL_CDS[p][level])
            except KeyError as exc:
                raise ValueError(f"No CDS mapping for {p=} soil level {level}.") from exc
    return dataset, variables, []


# Notebook-compatible alias
_translate_params_to_cds = translate_params_to_cds


def build_monthly_cds_request(
    *,
    year: int,
    month: int,
    days: list[str],
    hours: list[str],
    variables: list[str],
    pressure_levels: list[int] | None = None,
    grid: tuple[float, float] = (0.25, 0.25),
) -> dict:
    """CDS request for one month. days x hours is a cross product on the CDS side."""
    request = {
        "product_type": ["reanalysis"],
        "variable": variables,
        "year": [f"{year:04d}"],
        "month": [f"{month:02d}"],
        "day": days,
        "time": hours,
        "grid": list(grid),
        "data_format": "grib",
        "download_format": "unarchived",
    }
    if pressure_levels:
        request["pressure_level"] = [str(level) for level in pressure_levels]
    return request


def normalise_field_name(*, field, source: str) -> str:
    """Map ERA5 GRIB fields to AIFS names.

    sfc  -> shortName (2t, 10u, msl, z, slor, sdor, ...)
    pl   -> {shortName}_{level} (z_850, t_850, ...)
    soil -> ERA5 shortName (swvl1, swvl2, stl1, stl2); verify against checkpoint inputs.
    """
    short_name = field.metadata("shortName", default=field.metadata("param", default="unknown"))
    if source in ("sfc", "soil"):
        return short_name
    if source == "pl":
        return f"{short_name}_{field.metadata('levelist')}"
    raise ValueError(f"Unknown source: {source!r}")


# Notebook-compatible alias
_normalise_field_name = normalise_field_name
