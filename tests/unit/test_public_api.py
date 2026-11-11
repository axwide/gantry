EXPECTED_ALL = {
    "ALL_ARTIFACTS",
    "ProblemDefinition",
    "validate_toml",
    "generate_lib",
    "generate_scaffold",
    "generate_n2",
    "generate_xdsm",
}


def test_all_symbols_are_declared():
    import gemseo_gantry

    assert set(gemseo_gantry.__all__) == EXPECTED_ALL


def test_all_symbols_are_importable():
    import gemseo_gantry

    for name in gemseo_gantry.__all__:
        assert hasattr(gemseo_gantry, name), (
            f"{name!r} is in __all__ but not importable"
        )


def test_unknown_attribute_raises_attribute_error():
    import pytest

    import gemseo_gantry

    with pytest.raises(AttributeError):
        _ = gemseo_gantry.nonexistent_symbol_xyz
