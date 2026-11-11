from pathlib import Path

import pytest
from pydantic import ValidationError

FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures"


def test_parse_toml_discipline_sheets():
    """Parse disciplines from a simple TOML file."""
    from gemseo_gantry.model.data_model import ProblemDefinition
    from gemseo_gantry.parser.toml_parser import parse_toml

    result = parse_toml(FIXTURES_DIR / "gemseo_format_simple.toml")
    assert isinstance(result, ProblemDefinition)

    disc_names = {d.name for d in result.disciplines}
    assert disc_names == {"Discipline1", "Discipline2"}

    disc1 = next(d for d in result.disciplines if d.name == "Discipline1")
    assert set(disc1.inputs) == {"a", "b"}
    assert set(disc1.outputs) == {"c", "d"}

    disc2 = next(d for d in result.disciplines if d.name == "Discipline2")
    assert set(disc2.inputs) == {"c", "d"}
    assert set(disc2.outputs) == {"a", "e"}

    var_names = {v.name for v in result.variables}
    assert var_names == {"a", "b", "c", "d", "e"}


def test_parse_toml_with_variables():
    """Parse TOML with explicit variables section containing metadata."""
    from gemseo_gantry.parser.toml_parser import parse_toml

    result = parse_toml(FIXTURES_DIR / "gemseo_format_with_variables.toml")

    var_map = {v.name: v for v in result.variables}
    assert var_map["x"].is_design_variable is True
    assert var_map["x"].lower_bound == 0.0
    assert var_map["x"].upper_bound == 10.0
    assert var_map["x"].default_value == 5.0

    assert var_map["y"].is_design_variable is False
    assert var_map["z"].is_design_variable is False
    assert var_map["w"].is_design_variable is False

    disc_names = {d.name for d in result.disciplines}
    assert disc_names == {"Discipline1", "Discipline2"}


def test_parse_toml_scenario():
    """Parse TOML with a scenario containing design variables and objectives."""
    from gemseo_gantry.parser.toml_parser import parse_toml

    result = parse_toml(FIXTURES_DIR / "gemseo_format_with_variables.toml")

    assert len(result.scenarios) == 1
    scenario = result.scenarios[0]
    assert set(scenario.design_variables) == {"x"}
    assert scenario.formulation_type == "MDO"
    assert set(scenario.disciplines) == {"Discipline1", "Discipline2"}
    assert scenario.objective.variable == "y"


def test_parse_toml_extended_scenario():
    """Parse TOML scenario with maximize objective and explicit constraint details."""
    from gemseo_gantry.parser.toml_parser import parse_toml

    result = parse_toml(FIXTURES_DIR / "discipline_self_coupled_modified.toml")

    assert len(result.scenarios) == 1
    scenario = result.scenarios[0]
    assert scenario.objective.variable == "f"
    assert scenario.objective.maximize is True

    assert len(scenario.constraints) == 1
    assert scenario.constraints[0].variable == "g"
    assert scenario.constraints[0].operator == "<"
    assert scenario.constraints[0].value == 0.0


def test_parse_toml_bilevel():
    """Parse TOML with four disciplines (bilevel pattern)."""
    from gemseo_gantry.parser.toml_parser import parse_toml

    result = parse_toml(FIXTURES_DIR / "bilevel_d.toml")

    disc_names = {d.name for d in result.disciplines}
    assert disc_names == {"Sa", "Apa", "Ap", "O"}

    sa = next(d for d in result.disciplines if d.name == "Sa")
    assert set(sa.inputs) == {"pp", "prof", "mt"}
    assert set(sa.outputs) == {"m", "sc"}

    ap = next(d for d in result.disciplines if d.name == "Ap")
    assert set(ap.inputs) == {"l", "d", "m"}
    assert set(ap.outputs) == {"obj"}


def test_parse_toml_bilevel_all_scenarios():
    """TOML bilevel fixture has 3 scenarios including sub-scenario references."""
    from gemseo_gantry.parser.toml_parser import parse_toml

    result = parse_toml(FIXTURES_DIR / "bilevel_d.toml")

    assert len(result.scenarios) == 3
    scenario_names = {s.name for s in result.scenarios}
    assert scenario_names == {"Scenarios", "Scenarioa", "Scenariosystem"}

    system = next(s for s in result.scenarios if s.name == "Scenariosystem")
    assert "Scenarioa" in system.disciplines
    assert "Scenarios" in system.disciplines


def test_parse_toml_multiple_scenarios():
    """Two scenarios sharing a common discipline."""
    from gemseo_gantry.parser.toml_parser import parse_toml

    result = parse_toml(FIXTURES_DIR / "bilevel_multi_scenario.toml")

    assert len(result.scenarios) == 2
    scenario_names = {s.name for s in result.scenarios}
    assert scenario_names == {"Scenarioa", "Scenariob"}

    sa = next(s for s in result.scenarios if s.name == "Scenarioa")
    sb = next(s for s in result.scenarios if s.name == "Scenariob")
    assert "D2" in sa.disciplines
    assert "D2" in sb.disciplines


def test_parse_toml_sub_scenario_references():
    """ScenarioSystem references sub-scenario names as disciplines (BiLevel pattern)."""
    from gemseo_gantry.parser.toml_parser import parse_toml

    result = parse_toml(FIXTURES_DIR / "bilevel_sub_scenarios.toml")

    assert len(result.scenarios) == 3

    system = next(s for s in result.scenarios if s.name == "Scenariosystem")
    assert set(system.disciplines) == {"Scenarioa", "Scenariob"}


def test_parse_toml_self_coupled():
    """Parse a TOML discipline where a variable appears in both inputs and outputs."""
    from gemseo_gantry.parser.toml_parser import parse_toml

    result = parse_toml(FIXTURES_DIR / "discipline_self_coupled.toml")

    disc_names = {d.name for d in result.disciplines}
    assert disc_names == {"Discipline1", "Discipline2"}

    disc1 = next(d for d in result.disciplines if d.name == "Discipline1")
    assert set(disc1.inputs) == {"a", "x"}
    assert set(disc1.outputs) == {"a", "b"}  # self-coupled

    disc2 = next(d for d in result.disciplines if d.name == "Discipline2")
    assert set(disc2.inputs) == {"b"}
    assert set(disc2.outputs) == {"f", "g"}


def test_parse_toml_raises_for_invalid_scenario_type(tmp_path):
    """parse_toml raises when scenario_type is not DOE or MDO."""
    toml_content = """
[disciplines.disc_1]
inputs = ["x"]
outputs = ["y"]

[scenarios.scenario_1]
design_variables = ["x"]
disciplines = ["disc_1"]
scenario_type = "INVALID"

[scenarios.scenario_1.objective]
variable = "y"
"""
    toml_file = tmp_path / "invalid_scenario_type.toml"
    toml_file.write_text(toml_content)

    from gemseo_gantry.parser.toml_parser import parse_toml

    with pytest.raises(ValidationError):
        parse_toml(toml_file)


def test_parse_toml_self_coupled_one_disc():
    """Single self-coupled discipline: 'a' appears in both inputs and outputs."""
    from gemseo_gantry.parser.toml_parser import parse_toml

    result = parse_toml(FIXTURES_DIR / "discipline_self_coupled_one_disc.toml")

    assert len(result.disciplines) == 1
    disc = result.disciplines[0]
    assert disc.name == "Discipline1"
    assert set(disc.inputs) == {"a", "x"}
    assert set(disc.outputs) == {"a", "b", "f", "g"}

    assert len(result.scenarios) == 1
    scenario = result.scenarios[0]
    assert set(scenario.design_variables) == {"x"}
    assert scenario.disciplines == ["Discipline1"]
    assert scenario.objective.variable == "f"
    assert len(scenario.constraints) == 1
    assert scenario.constraints[0].variable == "g"


def test_parse_toml_disciplines_spec():
    """Two disciplines with multiple design variables and a constraint."""
    from gemseo_gantry.parser.toml_parser import parse_toml

    result = parse_toml(FIXTURES_DIR / "disciplines_spec.toml")

    disc_names = {d.name for d in result.disciplines}
    assert disc_names == {"Discipline1", "Discipline2"}

    disc1 = next(d for d in result.disciplines if d.name == "Discipline1")
    assert set(disc1.inputs) == {"a", "b", "c"}
    assert set(disc1.outputs) == {"d", "e", "g"}

    disc2 = next(d for d in result.disciplines if d.name == "Discipline2")
    assert set(disc2.inputs) == {"z", "x", "d", "e"}
    assert set(disc2.outputs) == {"a", "b", "f"}

    assert len(result.scenarios) == 1
    scenario = result.scenarios[0]
    assert set(scenario.design_variables) == {"b", "x"}
    assert set(scenario.disciplines) == {"Discipline1", "Discipline2"}
    assert scenario.objective.variable == "f"
    assert len(scenario.constraints) == 1
    assert scenario.constraints[0].variable == "g"


def test_parse_toml_special_characters_in_names():
    """Discipline keys with special characters are slugified to valid identifiers."""
    from gemseo_gantry.parser.toml_parser import parse_toml

    result = parse_toml(FIXTURES_DIR / "disciplines_spec_special_characters.toml")

    disc_names = {d.name for d in result.disciplines}
    assert disc_names == {"Discipline1", "Discipline2Cie"}

    assert len(result.scenarios) == 1
    scenario = result.scenarios[0]
    assert set(scenario.disciplines) == {"Discipline1", "Discipline2Cie"}


def test_parse_toml_without_scenario():
    """TOML with only disciplines and no scenarios section."""
    from gemseo_gantry.parser.toml_parser import parse_toml

    result = parse_toml(FIXTURES_DIR / "disciplines_spec_without_scenario.toml")

    disc_names = {d.name for d in result.disciplines}
    assert disc_names == {"Discipline1", "Discipline2"}

    disc1 = next(d for d in result.disciplines if d.name == "Discipline1")
    assert set(disc1.inputs) == {"a"}
    assert set(disc1.outputs) == {"b", "c"}

    disc2 = next(d for d in result.disciplines if d.name == "Discipline2")
    assert set(disc2.inputs) == {"a", "b"}
    assert set(disc2.outputs) == {"d"}

    assert result.scenarios == []


def test_parse_toml_bilevel_sobieski():
    """Sobieski problem: four disciplines and four scenarios including a bilevel system."""
    from gemseo_gantry.parser.toml_parser import parse_toml

    result = parse_toml(FIXTURES_DIR / "study_bilevel_sobieski.toml")

    disc_names = {d.name for d in result.disciplines}
    assert disc_names == {
        "SobieskiAerodynamics",
        "SobieskiStructure",
        "SobieskiPropulsion",
        "SobieskiMission",
    }

    aero = next(d for d in result.disciplines if d.name == "SobieskiAerodynamics")
    assert set(aero.inputs) == {"x_2", "x_shared", "y_12", "y_32"}
    assert set(aero.outputs) == {"y_2", "y_21", "y_23", "y_24", "g_2"}

    mission = next(d for d in result.disciplines if d.name == "SobieskiMission")
    assert set(mission.inputs) == {"x_shared", "y_14", "y_24", "y_34"}
    assert set(mission.outputs) == {"y_4"}

    assert len(result.scenarios) == 4
    scenario_names = {s.name for s in result.scenarios}
    assert scenario_names == {
        "ScenarioStructure",
        "ScenarioPropulsion",
        "ScenarioAero",
        "ScenarioSystem",
    }

    system = next(s for s in result.scenarios if s.name == "ScenarioSystem")
    assert set(system.design_variables) == {"x_shared"}
    assert system.objective.variable == "y_4"
    assert {c.variable for c in system.constraints} == {"g_1", "g_2", "g_3"}
    assert set(system.disciplines) == {
        "ScenarioAero",
        "ScenarioStructure",
        "ScenarioPropulsion",
        "SobieskiMission",
    }

    aero_scenario = next(s for s in result.scenarios if s.name == "ScenarioAero")
    assert set(aero_scenario.design_variables) == {"x_2"}
    assert set(aero_scenario.disciplines) == {"SobieskiAerodynamics", "SobieskiMission"}


def test_parse_toml_with_integer_variable(tmp_path):
    """A variable with data_type = "integer" round-trips to DataType.INTEGER."""
    toml_content = """
[disciplines.disc_1]
inputs = ["n"]
outputs = ["y"]

[[variables]]
name = "n"
unit = ""
data_type = "integer"
dimension = 1
"""
    toml_file = tmp_path / "integer_variable.toml"
    toml_file.write_text(toml_content)

    from gemseo_gantry.model.data_model import DataType
    from gemseo_gantry.parser.toml_parser import parse_toml

    result = parse_toml(toml_file)
    var_map = {v.name: v for v in result.variables}
    assert var_map["n"].data_type == DataType.INTEGER


def test_parse_toml_raises_for_unknown_data_type(tmp_path):
    """parse_toml raises when data_type is not one of the supported DataType values."""
    toml_content = """
[disciplines.disc_1]
inputs = ["x"]
outputs = ["y"]

[[variables]]
name = "x"
unit = ""
data_type = "bogus"
dimension = 1
"""
    toml_file = tmp_path / "unknown_data_type.toml"
    toml_file.write_text(toml_content)

    from gemseo_gantry.parser.toml_parser import parse_toml

    with pytest.raises(ValidationError):
        parse_toml(toml_file)


def test_parse_toml_raises_for_invalid_variables(tmp_path):
    """parse_toml raises when a variable is missing required fields."""
    toml_content = """
[disciplines.disc_1]
inputs = ["x"]
outputs = ["y"]

[[variables]]
name = "x"
# missing unit, data_type, dimension
"""
    toml_file = tmp_path / "invalid_variables.toml"
    toml_file.write_text(toml_content)

    from gemseo_gantry.parser.toml_parser import parse_toml

    with pytest.raises(ValidationError):
        parse_toml(toml_file)


def test_parse_toml_rejects_is_design_variable_key(tmp_path):
    """TOML carrying the removed is_design_variable key must raise a ValidationError."""
    toml_content = """
[disciplines.disc_1]
inputs = ["x"]
outputs = ["y"]

[[variables]]
name = "x"
unit = "m"
data_type = "float"
dimension = 1
is_design_variable = true

[scenarios.s1]
design_variables = ["x"]
disciplines = ["disc_1"]

[scenarios.s1.objective]
variable = "y"
"""
    toml_file = tmp_path / "has_is_design_variable.toml"
    toml_file.write_text(toml_content)

    from gemseo_gantry.parser.toml_parser import parse_toml

    with pytest.raises(ValidationError):
        parse_toml(toml_file)
