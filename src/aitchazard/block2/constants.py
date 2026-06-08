"""Shared Block 2 conventions for the SwAIther-Precip adaptation."""

SWAITHER_REFERENCE_REPOSITORY = "https://github.com/danassou/swaither-precip"
SWAITHER_REFERENCE_COMMIT = "f225b40"
AIFS_SINGLE_V2_CHECKPOINT = "ecmwf/aifs-single-2.0"

CANONICAL_TO_SWAITHER = {
    "tp_6h": "total_precipitation_NoNeg",
    "cp_6h": "convective_precipitation_NoNeg",
    "10u": "wind_10m_u",
    "10v": "wind_10m_v",
    "q_500": "specific_humidity_500hPa",
    "q_850": "specific_humidity_850hPa",
    "t_500": "temperature_500hPa",
    "t_850": "temperature_850hPa",
    "z_500": "geopotential_500hPa",
    "z_850": "geopotential_850hPa",
}

SWAITHER_STEP1_INPUT_VARIABLES = tuple(CANONICAL_TO_SWAITHER.values())

SWAITHER_TARGET_VARIABLE = "precip6h_cumulative_capped"
SWAITHER_INVARIANT_VARIABLES = ("altitude",)

BLOCK2_OUTPUTS = {
    "bias_corrected_coarse": "tp_6h_bc_coarse",
    "high_resolution_precipitation": "tp_6h_hr",
}
