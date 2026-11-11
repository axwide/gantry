import pytest

from gemseo_gantry.parser.utils import pascalify, sanitize_identifier


def test_valid_name_unchanged():
    assert sanitize_identifier("power_budget") == "power_budget"


def test_leading_digit_gets_underscore_prefix():
    assert sanitize_identifier("3dof_model") == "_3dof_model"


def test_python_keyword_gets_underscore_suffix():
    assert sanitize_identifier("class") == "class_"


def test_empty_string_raises():
    with pytest.raises(ValueError, match="empty"):
        sanitize_identifier("")


def test_pascal_case_valid_unchanged():
    assert sanitize_identifier("PowerBudget") == "PowerBudget"


def test_pascal_case_leading_digit_gets_prefix():
    assert sanitize_identifier("3DofModel") == "_3DofModel"


def test_pipeline_slugify_then_ensure_identifier():
    from slugify import slugify

    name = slugify("3D Printer", separator="_")
    result = sanitize_identifier(name)
    assert result == "_3d_printer"


def test_pipeline_pascalify_then_ensure_identifier():
    result = sanitize_identifier(pascalify("3d printer"))
    assert result == "_3DPrinter"
