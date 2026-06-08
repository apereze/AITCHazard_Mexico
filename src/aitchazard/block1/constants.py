"""Shared Block 1 scientific conventions."""

MEXICO_DOMAIN = {
    "latitude_min": 5.0,
    "latitude_max": 35.0,
    "longitude_west": -130.0,
    "longitude_east": -60.0,
    "longitude_360_min": 230.0,
    "longitude_360_max": 300.0,
}

DEFAULT_INITIALIZATION_FREQUENCY_HOURS = 6
DEFAULT_OUTPUT_FREQUENCY_HOURS = 6
DEFAULT_FORECAST_HORIZON_HOURS = 72

PRESSURE_LEVELS_HPA = (
    1000,
    925,
    850,
    700,
    600,
    500,
    400,
    300,
    250,
    200,
    150,
    100,
    50,
)

SURFACE_VARIABLES = (
    "tp_raw",
    "cp_raw",
    "10u",
    "10v",
    "msl",
    "sp",
    "2t",
    "2d",
    "skt",
    "sst",
    "tcw",
)

DERIVED_VARIABLES = ("tp_6h", "cp_6h", "ws10")
