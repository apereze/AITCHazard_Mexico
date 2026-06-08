from aitchazard.block2 import (
    AIFS_SINGLE_V2_CHECKPOINT,
    BLOCK2_OUTPUTS,
    CANONICAL_TO_SWAITHER,
    SWAITHER_REFERENCE_REPOSITORY,
)


def test_block2_uses_aifs_single_v2():
    assert AIFS_SINGLE_V2_CHECKPOINT == "ecmwf/aifs-single-2.0"


def test_block2_records_swaither_upstream():
    assert SWAITHER_REFERENCE_REPOSITORY.endswith("danassou/swaither-precip")


def test_precipitation_mapping_keeps_aitchazard_canonical_names():
    assert CANONICAL_TO_SWAITHER["tp_6h"] == "total_precipitation_NoNeg"
    assert CANONICAL_TO_SWAITHER["cp_6h"] == "convective_precipitation_NoNeg"


def test_block2_output_names_match_project_schema():
    assert BLOCK2_OUTPUTS["bias_corrected_coarse"] == "tp_6h_bc_coarse"
    assert BLOCK2_OUTPUTS["high_resolution_precipitation"] == "tp_6h_hr"
