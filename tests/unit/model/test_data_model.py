import pytest


def test_scenario_objective_is_single():
    """Scenario.objective is a single Objective, not a list."""
    from gemseo_gantry.model.data_model import Objective, Scenario

    s = Scenario(
        name="S",
        design_variables=["x"],
        disciplines=["D"],
        formulation_type="MDO",
        objective=Objective(variable="x", maximize=True),
        constraints=[],
    )
    assert s.objective.variable == "x"
    assert s.objective.maximize is True


def test_variable_rejects_leading_digit_name():
    from pydantic import ValidationError

    from gemseo_gantry.model.data_model import Variable

    with pytest.raises(ValidationError, match="valid Python identifier"):
        Variable(name="3dof", unit="m", data_type="float", dimension=1)


def test_variable_rejects_keyword_name():
    from pydantic import ValidationError

    from gemseo_gantry.model.data_model import Variable

    with pytest.raises(ValidationError, match="valid Python identifier"):
        Variable(name="class", unit="m", data_type="float", dimension=1)


def test_variable_rejects_empty_name():
    from pydantic import ValidationError

    from gemseo_gantry.model.data_model import Variable

    with pytest.raises(ValidationError, match="valid Python identifier"):
        Variable(name="", unit="m", data_type="float", dimension=1)


def test_discipline_rejects_leading_digit_name():
    from pydantic import ValidationError

    from gemseo_gantry.model.data_model import Discipline

    with pytest.raises(ValidationError, match="valid Python identifier"):
        Discipline(name="3DofModel")


def test_variable_accepts_sanitized_name():
    from gemseo_gantry.model.data_model import Variable

    v = Variable(name="_3dof", unit="m", data_type="float", dimension=1)
    assert v.name == "_3dof"


def test_problem_definition_without_explicit_relations():
    """ProblemDefinition should derive relations from disciplines automatically."""
    from gemseo_gantry.model.data_model import Discipline, ProblemDefinition, Variable

    variables = [
        Variable(
            name="x", unit="m", data_type="float", dimension=1, is_design_variable=True
        ),
        Variable(name="y", unit="m", data_type="float", dimension=1),
    ]
    disciplines = [Discipline(name="disc1", inputs=["x"], outputs=["y"])]
    problem = ProblemDefinition(variables=variables, disciplines=disciplines)
    assert problem.relations == {
        "x": {"input": ["disc1"], "output": []},
        "y": {"input": [], "output": ["disc1"]},
    }


def test_problem_definition_accepts_any_structure():
    """ProblemDefinition is a pure data structure with no validation logic."""
    from gemseo_gantry.model.data_model import Discipline, ProblemDefinition, Variable

    variables = [
        Variable(
            name="x", unit="m", data_type="float", dimension=1, is_design_variable=True
        ),
        Variable(name="y", unit="m", data_type="float", dimension=1),
        Variable(name="z", unit="m", data_type="float", dimension=1),
    ]
    disciplines = [
        Discipline(name="disc1", inputs=["x", "z"], outputs=["y"]),
        Discipline(name="disc2", inputs=["y"], outputs=["z"]),
    ]
    problem = ProblemDefinition(variables=variables, disciplines=disciplines)
    assert len(problem.variables) == 3
    assert len(problem.disciplines) == 2


def test_variable_is_design_variable_flag():
    """Variable.is_design_variable defaults to False and can be set to True."""
    from gemseo_gantry.model.data_model import Variable

    dv = Variable(
        name="x",
        unit="m",
        data_type="float",
        dimension=1,
        lower_bound=0.0,
        upper_bound=10.0,
        default_value=5.0,
        is_design_variable=True,
    )
    assert dv.is_design_variable is True
    assert dv.lower_bound == 0.0
    assert dv.upper_bound == 10.0
    assert dv.default_value == 5.0

    plain = Variable(name="y", unit="m", data_type="float", dimension=1)
    assert plain.is_design_variable is False


def test_design_space_property():
    """design_space returns dicts for variables with is_design_variable=True."""
    from gemseo_gantry.model.data_model import Discipline, ProblemDefinition, Variable

    variables = [
        Variable(
            name="x",
            unit="m",
            data_type="float",
            dimension=1,
            lower_bound=0.0,
            upper_bound=10.0,
            default_value=5.0,
            is_design_variable=True,
        ),
        Variable(name="y", unit="m", data_type="float", dimension=1),
    ]
    disciplines = [Discipline(name="disc1", inputs=["x"], outputs=["y"])]
    problem = ProblemDefinition(variables=variables, disciplines=disciplines)

    ds = problem.design_space
    assert len(ds) == 1
    assert ds[0]["name"] == "x"
    assert ds[0]["lower_bound"] == 0.0
    assert ds[0]["upper_bound"] == 10.0
    assert ds[0]["value"] == 5.0
    assert ds[0]["type"] == "float"


def test_design_space_property_maps_missing_bounds_to_infinity():
    """Missing bounds become -inf/+inf so the design_space CSV is valid for GEMSEO."""
    import math

    from gemseo_gantry.model.data_model import Discipline, ProblemDefinition, Variable

    variables = [
        Variable(
            name="x",
            unit="m",
            data_type="float",
            dimension=1,
            default_value=5.0,
            is_design_variable=True,
        ),  # no bounds
        Variable(name="y", unit="m", data_type="float", dimension=1),
    ]
    disciplines = [Discipline(name="disc1", inputs=["x"], outputs=["y"])]
    problem = ProblemDefinition(variables=variables, disciplines=disciplines)

    ds = problem.design_space
    assert len(ds) == 1
    assert ds[0]["lower_bound"] == -math.inf
    assert ds[0]["upper_bound"] == math.inf
    assert ds[0]["value"] == 5.0


def test_design_space_empty_when_no_design_variables():
    """design_space is empty when no variables are flagged as design variables."""
    from gemseo_gantry.model.data_model import Discipline, ProblemDefinition, Variable

    variables = [Variable(name="y", unit="m", data_type="float", dimension=1)]
    disciplines = [Discipline(name="disc1", inputs=["y"], outputs=["y"])]
    problem = ProblemDefinition(variables=variables, disciplines=disciplines)
    assert problem.design_space == []


def test_scenario_has_formulation_field():
    """Scenario model should have a formulation field to specify explicit formulations."""
    from gemseo_gantry.model.data_model import Scenario

    assert "formulation" in Scenario.model_fields


def test_multiple_scenarios_valid():
    """ProblemDefinition accepts a list of scenarios."""
    from gemseo_gantry.model.data_model import (
        Discipline,
        Objective,
        ProblemDefinition,
        Scenario,
        Variable,
    )

    variables = [Variable(name="x", unit="m", data_type="float", dimension=1)]
    disciplines = [
        Discipline(name="D1", inputs=["x"], outputs=["x"]),
        Discipline(name="D2", inputs=["x"], outputs=["x"]),
    ]
    s1 = Scenario(
        name="ScenarioA",
        design_variables=["x"],
        disciplines=["D1"],
        formulation_type="MDO",
        objective=Objective(variable="x", maximize=False),
        constraints=[],
    )
    s2 = Scenario(
        name="ScenarioB",
        design_variables=["x"],
        disciplines=["D2"],
        formulation_type="MDO",
        objective=Objective(variable="x", maximize=False),
        constraints=[],
    )
    problem = ProblemDefinition(
        variables=variables, disciplines=disciplines, scenarios=[s1, s2]
    )
    assert len(problem.scenarios) == 2
    assert problem.scenarios[0].name == "ScenarioA"
    assert problem.scenarios[1].name == "ScenarioB"


def test_variable_accepts_integer_data_type():
    from gemseo_gantry.model.data_model import DataType, Variable

    v = Variable(name="n", unit="", data_type="integer", dimension=1)
    assert v.data_type == DataType.INTEGER


def test_variable_rejects_unknown_data_type():
    from pydantic import ValidationError

    from gemseo_gantry.model.data_model import Variable

    with pytest.raises(ValidationError):
        Variable(name="x", unit="m", data_type="bogus", dimension=1)


def test_design_space_type_serializes_integer_as_string():
    """design_space 'type' column must serialize the enum to its string value."""
    from gemseo_gantry.model.data_model import Discipline, ProblemDefinition, Variable

    variables = [
        Variable(
            name="n",
            unit="",
            data_type="integer",
            dimension=1,
            lower_bound=0,
            upper_bound=10,
            default_value=5,
            is_design_variable=True,
        ),
    ]
    disciplines = [Discipline(name="disc1", inputs=["n"], outputs=["n"])]
    problem = ProblemDefinition(variables=variables, disciplines=disciplines)
    assert problem.design_space[0]["type"] == "integer"
    assert isinstance(problem.design_space[0]["type"], str)


def test_constraint_type_eq() -> None:
    """Constraint.constraint_type returns 'eq' when operator is '=' (line 50)."""
    from gemseo_gantry.model.data_model import Constraint

    c = Constraint(variable="x", operator="=", value=0.0)
    assert c.constraint_type == "eq"


def test_constraint_type_ineq() -> None:
    from gemseo_gantry.model.data_model import Constraint

    c = Constraint(variable="x", operator="<", value=0.0)
    assert c.constraint_type == "ineq"


def test_scenario_references_other_scenario_as_discipline():
    """BiLevel: a scenario may list other scenario names as disciplines."""
    from gemseo_gantry.model.data_model import (
        Discipline,
        Objective,
        ProblemDefinition,
        Scenario,
        Variable,
    )

    variables = [Variable(name="x", unit="m", data_type="float", dimension=1)]
    disciplines = [Discipline(name="D1", inputs=["x"], outputs=["x"])]
    sub = Scenario(
        name="ScenarioA",
        design_variables=["x"],
        disciplines=["D1"],
        formulation_type="MDO",
        objective=Objective(variable="x", maximize=False),
        constraints=[],
    )
    system = Scenario(
        name="ScenarioSystem",
        design_variables=["x"],
        disciplines=["ScenarioA"],  # references sub-scenario by name
        formulation_type="MDO",
        objective=Objective(variable="x", maximize=False),
        constraints=[],
    )
    # Should not raise - model is a pure data structure with no discipline reference checks
    problem = ProblemDefinition(
        variables=variables, disciplines=disciplines, scenarios=[sub, system]
    )
    assert len(problem.scenarios) == 2
    assert problem.scenarios[1].disciplines == ["ScenarioA"]


def test_variable_accepts_list_bounds_and_default():
    from gemseo_gantry.model.data_model import Variable

    v = Variable(
        name="x",
        data_type="float",
        dimension=3,
        lower_bound=[0.0, 1.0, 2.0],
        upper_bound=[10.0, 11.0, 12.0],
        default_value=[1.0, 2.0, 3.0],
    )
    assert v.lower_bound == [0.0, 1.0, 2.0]
    assert v.upper_bound == [10.0, 11.0, 12.0]
    assert v.default_value == [1.0, 2.0, 3.0]


def test_lower_bounds_broadcasts_scalar():
    from gemseo_gantry.model.data_model import Variable

    v = Variable(name="x", data_type="float", dimension=3, lower_bound=2.0)
    assert v.lower_bounds() == [2.0, 2.0, 2.0]


def test_lower_bounds_passes_through_list():
    from gemseo_gantry.model.data_model import Variable

    v = Variable(name="x", data_type="float", dimension=3, lower_bound=[1.0, 2.0, 3.0])
    assert v.lower_bounds() == [1.0, 2.0, 3.0]


def test_lower_bounds_none_stays_none():
    from gemseo_gantry.model.data_model import Variable

    v = Variable(name="x", data_type="float", dimension=3)
    assert v.lower_bounds() is None


def test_upper_bounds_broadcasts_scalar():
    from gemseo_gantry.model.data_model import Variable

    v = Variable(name="x", data_type="float", dimension=2, upper_bound=5.0)
    assert v.upper_bounds() == [5.0, 5.0]


def test_default_values_broadcasts_scalar():
    from gemseo_gantry.model.data_model import Variable

    v = Variable(name="x", data_type="float", dimension=2, default_value=1.5)
    assert v.default_values() == [1.5, 1.5]


def test_default_values_none_stays_none():
    from gemseo_gantry.model.data_model import Variable

    v = Variable(name="x", data_type="float", dimension=2)
    assert v.default_values() is None


def test_design_space_emits_one_row_per_element_for_vector_variable():
    from gemseo_gantry.model.data_model import Discipline, ProblemDefinition, Variable

    problem = ProblemDefinition(
        variables=[
            Variable(
                name="x",
                data_type="float",
                dimension=3,
                lower_bound=[0.0, 1.0, 2.0],
                upper_bound=[10.0, 11.0, 12.0],
                default_value=[1.0, 2.0, 3.0],
                is_design_variable=True,
            ),
        ],
        disciplines=[Discipline(name="d", inputs=["x"])],
    )
    rows = problem.design_space
    assert len(rows) == 3
    assert [r["name"] for r in rows] == ["x", "x", "x"]
    assert [r["lower_bound"] for r in rows] == [0.0, 1.0, 2.0]
    assert [r["value"] for r in rows] == [1.0, 2.0, 3.0]
    assert [r["upper_bound"] for r in rows] == [10.0, 11.0, 12.0]
    assert all(r["type"] == "float" for r in rows)


def test_design_space_scalar_variable_emits_one_row():
    from gemseo_gantry.model.data_model import Discipline, ProblemDefinition, Variable

    problem = ProblemDefinition(
        variables=[
            Variable(
                name="x",
                data_type="float",
                dimension=1,
                lower_bound=0.0,
                upper_bound=10.0,
                default_value=5.0,
                is_design_variable=True,
            ),
        ],
        disciplines=[Discipline(name="d", inputs=["x"])],
    )
    assert problem.design_space == [
        {
            "name": "x",
            "lower_bound": 0.0,
            "value": 5.0,
            "upper_bound": 10.0,
            "type": "float",
        }
    ]


def test_design_space_broadcasts_scalar_bound_on_vector_variable():
    from gemseo_gantry.model.data_model import Discipline, ProblemDefinition, Variable

    problem = ProblemDefinition(
        variables=[
            Variable(
                name="x",
                data_type="float",
                dimension=2,
                lower_bound=0.0,  # scalar, broadcasts
                upper_bound=[5.0, 6.0],  # list
                is_design_variable=True,
            ),
        ],
        disciplines=[Discipline(name="d", inputs=["x"])],
    )
    rows = problem.design_space
    assert [r["lower_bound"] for r in rows] == [0.0, 0.0]
    assert [r["upper_bound"] for r in rows] == [5.0, 6.0]
