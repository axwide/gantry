import pytest

from gemseo_gantry.parser.toml_data_model import TomlProblemDefinition
from gemseo_gantry.validation import semantic


def _parsed(toml_dict):
    return TomlProblemDefinition.model_validate(toml_dict)


def _base():
    return {
        "disciplines": {"disc_a": {"inputs": ["x"], "outputs": ["obj"]}},
        "variables": [
            {
                "name": "x",
                "data_type": "float",
                "dimension": 1,
                "lower_bound": 0.0,
                "upper_bound": 1.0,
                "default_value": 0.5,
            },
            {"name": "obj", "data_type": "float", "dimension": 1},
        ],
        "scenarios": {
            "main": {
                "design_variables": ["x"],
                "disciplines": ["disc_a"],
                "objective": {"variable": "obj"},
            }
        },
    }


def test_disjoint_names_flags_clash():
    data = _base()
    # a discipline and a scenario both normalize to "DiscA"
    data["disciplines"]["disc_a"] = {"inputs": ["x"], "outputs": ["obj"]}
    data["scenarios"]["disc_a"] = {
        "design_variables": ["x"],
        "disciplines": ["disc_a"],
        "objective": {"variable": "obj"},
    }
    violations = semantic.check_disjoint_discipline_scenario_names(_parsed(data))
    assert any("DiscA" in v for v in violations)


def test_disjoint_names_ok_when_distinct():
    violations = semantic.check_disjoint_discipline_scenario_names(_parsed(_base()))
    assert violations == []


def test_nesting_without_bilevel_is_flagged():
    data = _base()
    data["disciplines"]["disc_b"] = {"inputs": ["x"], "outputs": ["obj2"]}
    data["variables"].append({"name": "obj2", "data_type": "float", "dimension": 1})
    data["scenarios"]["sub"] = {
        "design_variables": ["x"],
        "disciplines": ["disc_a"],
        "objective": {"variable": "obj"},
    }
    data["scenarios"]["main"] = {
        "design_variables": ["x"],
        "disciplines": ["disc_b", "Sub"],
        "formulation": "MDF",
        "objective": {"variable": "obj2"},
    }
    violations = semantic.check_nesting_formulation(_parsed(data))
    assert any("require 'BiLevel'" in v for v in violations)


def test_bilevel_without_subscenarios_is_flagged():
    data = _base()
    data["scenarios"]["main"]["formulation"] = "BiLevel"
    violations = semantic.check_nesting_formulation(_parsed(data))
    assert any("no sub-scenarios" in v for v in violations)


def test_nesting_with_default_bilevel_bcd_ok():
    data = _base()
    data["disciplines"]["disc_b"] = {"inputs": ["x"], "outputs": ["obj2"]}
    data["variables"].append({"name": "obj2", "data_type": "float", "dimension": 1})
    data["scenarios"]["sub"] = {
        "design_variables": ["x"],
        "disciplines": ["disc_a"],
        "objective": {"variable": "obj"},
    }
    data["scenarios"]["main"] = {
        "design_variables": ["x"],
        "disciplines": ["disc_b", "Sub"],
        "objective": {"variable": "obj2"},
    }
    assert semantic.check_nesting_formulation(_parsed(data)) == []


def test_idf_raises_not_implemented():
    data = _base()
    data["scenarios"]["main"]["formulation"] = "IDF"
    with pytest.raises(NotImplementedError, match="IDF"):
        semantic.run_all(_parsed(data))


def test_multiple_roots_raises_not_implemented():
    data = _base()
    data["disciplines"]["disc_b"] = {"inputs": ["x"], "outputs": ["obj2"]}
    data["variables"].append({"name": "obj2", "data_type": "float", "dimension": 1})
    data["scenarios"]["second"] = {
        "design_variables": ["x"],
        "disciplines": ["disc_b"],
        "objective": {"variable": "obj2"},
    }
    with pytest.raises(NotImplementedError, match="Multiple root"):
        semantic.run_all(_parsed(data))


def test_discipline_reused_across_scenarios_raises_not_implemented():
    data = _base()
    data["variables"].append({"name": "obj2", "data_type": "float", "dimension": 1})
    data["disciplines"]["disc_a"] = {"inputs": ["x"], "outputs": ["obj", "obj2"]}
    # disc_a is used by both the sub-scenario and the root.
    data["scenarios"]["sub"] = {
        "design_variables": ["x"],
        "disciplines": ["disc_a"],
        "objective": {"variable": "obj"},
    }
    data["scenarios"]["main"] = {
        "design_variables": ["x"],
        "disciplines": ["disc_a", "Sub"],
        "objective": {"variable": "obj2"},
    }
    with pytest.raises(NotImplementedError, match="instantiated multiple times"):
        semantic.run_all(_parsed(data))


def test_discipline_listed_twice_in_one_scenario_raises_not_implemented():
    data = _base()
    data["scenarios"]["main"]["disciplines"] = ["disc_a", "disc_a"]
    with pytest.raises(NotImplementedError, match="instantiated multiple times"):
        semantic.run_all(_parsed(data))


def test_cycle_has_no_root():
    data = _base()
    # two scenarios each nested under the other -> no root
    data["disciplines"]["disc_b"] = {"inputs": ["x"], "outputs": ["obj2"]}
    data["variables"].append({"name": "obj2", "data_type": "float", "dimension": 1})
    data["scenarios"]["main"] = {
        "design_variables": ["x"],
        "disciplines": ["disc_a", "Second"],
        "formulation": "BiLevel",
        "objective": {"variable": "obj"},
    }
    data["scenarios"]["second"] = {
        "design_variables": ["x"],
        "disciplines": ["disc_b", "Main"],
        "formulation": "BiLevel",
        "objective": {"variable": "obj2"},
    }
    violations = semantic.check_root_exists(_parsed(data))
    assert any("root" in v.lower() for v in violations)
