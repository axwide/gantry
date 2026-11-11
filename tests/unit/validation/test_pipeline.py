from __future__ import annotations

from pathlib import Path
from tomllib import TOMLDecodeError

import pytest

from gemseo_gantry.model.data_model import ProblemDefinition
from gemseo_gantry.validation import ValidationResult, validate_toml


def _write(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "problem.toml"
    p.write_text(content)
    return p


# -- stage 1: syntax -----------------------------------------------------------


def test_toml_syntax_error_raises_decode_error(tmp_path):
    p = _write(tmp_path, "[disciplines\n")  # unclosed bracket
    with pytest.raises(TOMLDecodeError):
        validate_toml(p)


# -- stage 2: structural -------------------------------------------------------


def test_missing_required_variable_field_raises_value_error(tmp_path):
    p = _write(
        tmp_path,
        """
[disciplines.drag]
inputs = ["h"]
outputs = ["duty_cycle"]

[[variables]]
name = "h"
# unit, data_type, dimension missing
""",
    )
    with pytest.raises(ValueError) as exc_info:
        validate_toml(p)
    msg = str(exc_info.value)
    assert "unit" in msg or "data_type" in msg or "dimension" in msg


def test_invalid_scenario_type_raises_value_error(tmp_path):
    p = _write(
        tmp_path,
        """
[disciplines.drag]
inputs = ["x"]
outputs = ["y"]

[scenarios.s1]
design_variables = ["x"]
disciplines = ["drag"]
scenario_type = "INVALID"

[scenarios.s1.objective]
variable = "y"
""",
    )
    with pytest.raises(ValueError) as exc_info:
        validate_toml(p)
    msg = str(exc_info.value)
    assert "scenario_type" in msg or "DOE" in msg or "MDO" in msg


def test_extra_field_in_discipline_raises(tmp_path):
    p = _write(
        tmp_path,
        """
[disciplines.drag]
inputs = ["h"]
outputs = ["duty_cycle"]
unknown_key = "oops"
""",
    )
    with pytest.raises(ValueError) as exc_info:
        validate_toml(p)
    assert "unknown_key" in str(exc_info.value)


def test_extra_field_at_top_level_raises(tmp_path):
    p = _write(
        tmp_path,
        """
[disciplines.drag]
inputs = ["h"]
outputs = ["duty_cycle"]

[custom_section]
key = "value"
""",
    )
    with pytest.raises(ValueError) as exc_info:
        validate_toml(p)
    assert "custom_section" in str(exc_info.value)


def test_fmt_pydantic_error_without_location() -> None:
    """_fmt_pydantic_error returns just the message when loc is empty (line 44)."""
    from gemseo_gantry.validation.pipeline import _fmt_pydantic_error

    error = {"loc": (), "msg": "Value error, something bad", "type": "value_error"}
    result = _fmt_pydantic_error(error)  # type: ignore[arg-type]
    assert result == "something bad"
    assert " -> " not in result


def test_structural_error_uses_arrow_location_separator(tmp_path):
    """Pydantic errors are formatted with ' -> ' joining the loc path (ASCII only)."""
    p = _write(
        tmp_path,
        """
[disciplines.drag]
inputs = ["h"]
outputs = ["duty_cycle"]
unknown_key = "oops"
""",
    )
    with pytest.raises(ValueError) as exc_info:
        validate_toml(p)
    msg = str(exc_info.value)
    # loc is ('disciplines', 'drag', 'unknown_key') -> "disciplines -> drag -> unknown_key"
    assert " -> " in msg
    assert "disciplines -> drag -> unknown_key" in msg
    assert msg.isascii()


def test_extra_field_in_variable_raises(tmp_path):
    p = _write(
        tmp_path,
        """
[disciplines.drag]
inputs = ["h"]
outputs = ["duty_cycle"]

[[variables]]
name = "h"
unit = "m"
data_type = "float"
dimension = 1
unknown_key = "oops"
""",
    )
    with pytest.raises(ValueError) as exc_info:
        validate_toml(p)
    assert "unknown_key" in str(exc_info.value)


def test_extra_field_in_objective_raises(tmp_path):
    p = _write(
        tmp_path,
        """
[disciplines.drag]
inputs = ["x"]
outputs = ["y"]

[scenarios.s1]
design_variables = ["x"]
disciplines = ["drag"]

[scenarios.s1.objective]
variable = "y"
unknown_key = "oops"
""",
    )
    with pytest.raises(ValueError) as exc_info:
        validate_toml(p)
    assert "unknown_key" in str(exc_info.value)


def test_extra_field_in_constraint_raises(tmp_path):
    p = _write(
        tmp_path,
        """
[disciplines.drag]
inputs = ["x"]
outputs = ["y"]

[scenarios.s1]
design_variables = ["x"]
disciplines = ["drag"]

[scenarios.s1.objective]
variable = "y"

[[scenarios.s1.constraints]]
variable = "y"
unknown_key = "oops"
""",
    )
    with pytest.raises(ValueError) as exc_info:
        validate_toml(p)
    assert "unknown_key" in str(exc_info.value)


def test_extra_field_in_scenario_raises(tmp_path):
    p = _write(
        tmp_path,
        """
[disciplines.drag]
inputs = ["x"]
outputs = ["y"]

[scenarios.s1]
design_variables = ["x"]
disciplines = ["drag"]
unknown_key = "oops"

[scenarios.s1.objective]
variable = "y"
""",
    )
    with pytest.raises(ValueError) as exc_info:
        validate_toml(p)
    assert "unknown_key" in str(exc_info.value)


def test_structural_error_stops_pipeline_before_semantic(tmp_path):
    """Stage 2 failure must not allow Stage 3 to run."""
    p = _write(
        tmp_path,
        """
[disciplines.drag]
inputs = ["x"]
outputs = ["y"]

[[variables]]
name = "x"
unit = "m"
data_type = "float"
dimension = 1

[scenarios.s1]
design_variables = ["x"]
disciplines = ["drag"]
scenario_type = "INVALID"

[scenarios.s1.objective]
variable = "y"
""",
    )
    with pytest.raises(ValueError) as exc_info:
        validate_toml(p)
    # Must be a structural error message, not a semantic one about 'y' missing from variables
    assert "semantic" not in str(exc_info.value).lower()


# -- stage 3: semantic ---------------------------------------------------------


def test_semantic_error_raises_value_error(tmp_path):
    p = _write(
        tmp_path,
        """
[disciplines.drag]
inputs = ["h"]
outputs = ["duty_cycle"]

[disciplines.power]
inputs = ["h"]
outputs = ["duty_cycle"]
""",
    )
    with pytest.raises(ValueError) as exc_info:
        validate_toml(p)
    assert "duty_cycle" in str(exc_info.value)


def test_all_semantic_violations_reported_together(tmp_path):
    p = _write(
        tmp_path,
        """
[disciplines.drag]
inputs = ["h"]
outputs = ["duty_cycle"]

[disciplines.power]
inputs = ["h"]
outputs = ["duty_cycle"]

[scenarios.vleo]
design_variables = ["h"]
disciplines = ["drag", "power", "ghost"]

[scenarios.vleo.objective]
variable = "duty_cycle"
""",
    )
    with pytest.raises(ValueError) as exc_info:
        validate_toml(p)
    msg = str(exc_info.value)
    assert "duty_cycle" in msg  # double-output
    assert "ghost" in msg  # missing discipline


def test_no_disciplines_raises_value_error(tmp_path):
    p = _write(tmp_path, "[disciplines]\n")  # present but empty
    with pytest.raises(ValueError, match="No disciplines"):
        validate_toml(p)


# -- happy path ----------------------------------------------------------------


def test_valid_toml_returns_validation_result(tmp_path):
    p = _write(
        tmp_path,
        """
[disciplines.drag]
inputs = ["h"]
outputs = ["duty_cycle"]

[[variables]]
name = "h"
unit = "m"
data_type = "float"
dimension = 1

[[variables]]
name = "duty_cycle"
unit = "-"
data_type = "float"
dimension = 1
""",
    )
    result = validate_toml(p)
    assert isinstance(result, ValidationResult)
    assert isinstance(result.problem, ProblemDefinition)
    assert result.warnings == []
    assert len(result.problem.disciplines) == 1
    assert result.problem.disciplines[0].name == "Drag"


def test_valid_toml_no_warnings_on_clean_input(tmp_path):
    """A clean TOML with no issues returns an empty warnings list."""
    p = _write(
        tmp_path,
        """
[disciplines.drag]
inputs = ["h"]
outputs = ["duty_cycle"]

[[variables]]
name = "h"
unit = "m"
data_type = "float"
dimension = 1

[[variables]]
name = "duty_cycle"
unit = "-"
data_type = "float"
dimension = 1
""",
    )
    result = validate_toml(p)
    assert isinstance(result, ValidationResult)
    assert result.warnings == []


def test_file_not_found_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        validate_toml(tmp_path / "ghost.toml")
