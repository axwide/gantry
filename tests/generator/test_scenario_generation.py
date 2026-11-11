from pathlib import Path

from gemseo_gantry.generator.lib_generator import generate_scenario
from gemseo_gantry.model.data_model import (
    Discipline,
    Objective,
    ProblemDefinition,
    Scenario,
    Variable,
)


def _problem():
    sub = Scenario(
        name="Sub",
        design_variables=["x"],
        disciplines=["DiscA"],
        formulation_type="MDO",
        objective=Objective(variable="sub_obj"),
        constraints=[],
    )
    root = Scenario(
        name="Root",
        design_variables=["x"],
        disciplines=["DiscB", "Sub"],
        formulation_type="MDO",
        objective=Objective(variable="obj"),
        constraints=[],
    )
    return ProblemDefinition(
        variables=[
            Variable(
                name="x",
                data_type="float",
                dimension=1,
                lower_bound=0.0,
                upper_bound=1.0,
                default_value=0.5,
            ),
            Variable(name="sub_obj", data_type="float", dimension=1),
            Variable(name="obj", data_type="float", dimension=1),
        ],
        disciplines=[
            Discipline(name="DiscA", inputs=["x"], outputs=["sub_obj"]),
            Discipline(name="DiscB", inputs=["x"], outputs=["obj"]),
        ],
        scenarios=[sub, root],
    )


def test_root_scenario_emits_subscenarios_dataclass(tmp_path: Path):
    generate_scenario(_problem(), tmp_path)
    root_src = (tmp_path / "Root.py").read_text()
    assert "class RootSubScenarios:" in root_src
    assert "Sub: BaseScenario" in root_src
    assert "sub_scenarios: RootSubScenarios" in root_src
    # plain disciplines are instances, not classes
    assert "DiscB: Discipline" in root_src
    assert "disciplines.DiscB," in root_src  # no parentheses -> instance
    assert "sub_scenarios.Sub," in root_src
    assert "filter(design_variables, copy=True)" in root_src


def test_leaf_scenario_has_no_subscenarios(tmp_path: Path):
    generate_scenario(_problem(), tmp_path)
    sub_src = (tmp_path / "Sub.py").read_text()
    assert "SubScenarios" not in sub_src.replace("BaseScenario", "")
    assert "DiscA: Discipline" in sub_src
    assert "disciplines.DiscA," in sub_src
