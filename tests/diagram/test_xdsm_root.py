from pathlib import Path

from gemseo_gantry.diagram.diagram import _build_dummy_scenario, generate_xdsm
from gemseo_gantry.model.data_model import (
    Discipline,
    FormulationType,
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
        formulation=FormulationType.BILEVEL_BCD,
        objective=Objective(variable="obj"),
        constraints=[],
    )
    return ProblemDefinition(
        variables=[
            Variable(name="x", data_type="float", dimension=1),
            Variable(name="sub_obj", data_type="float", dimension=1),
            Variable(name="obj", data_type="float", dimension=1),
        ],
        disciplines=[
            Discipline(name="DiscA", inputs=["x"], outputs=["sub_obj"]),
            Discipline(name="DiscB", inputs=["x"], outputs=["obj"]),
        ],
        scenarios=[sub, root],
    )


def test_xdsm_renders_without_error(tmp_path: Path):
    # Must not KeyError on the "Sub" name in root.disciplines.
    generate_xdsm(_problem(), tmp_path)
    assert (tmp_path / "xdsm.html").is_file()


def test_xdsm_includes_subscenarios():
    # The root is bilevel, so its sub-scenarios must appear in the structure
    # rather than collapsing to the root's plain disciplines.
    problem = _problem()
    disc_map = {d.name: d for d in problem.disciplines}
    scen_map = {s.name: s for s in problem.scenarios}
    scenario = _build_dummy_scenario(
        problem, problem.root_scenarios[0], disc_map, scen_map
    )
    disciplines = scenario.formulation.disciplines
    names = {d.name for d in disciplines}
    # The plain discipline plus the nested sub-scenario are both present.
    assert "DiscB" in names
    assert any(d.name == "Sub" for d in disciplines)
