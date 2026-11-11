from pathlib import Path

from gemseo_gantry.generator.scaffold_generator import generate_scenario_executor
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


def test_only_root_gets_executor(tmp_path: Path):
    out = generate_scenario_executor(
        _problem(),
        tmp_path,
        lib_dir=tmp_path / "lib",
        disciplines_dir=tmp_path / "lib",
        import_root=tmp_path,
    )
    written = {p.path.name for p in out}
    assert "execute_Root.py" in written
    assert "execute_Sub.py" not in written


def test_executor_wires_subscenarios(tmp_path: Path):
    generate_scenario_executor(
        _problem(),
        tmp_path,
        lib_dir=tmp_path / "lib",
        disciplines_dir=tmp_path / "lib",
        import_root=tmp_path,
    )
    src = (tmp_path / "execute_Root.py").read_text()
    # sub-scenario constructed first, with MDF default + set_algorithm
    assert "construct_Sub(" in src
    assert "MDF_Settings()" in src
    assert ".set_algorithm(" in src
    # root constructed with the sub-scenario instance + BCD settings
    assert "construct_Root(" in src
    assert "BiLevel_BCD_Settings()" in src
    assert "RootSubScenarios(" in src
    # only the root is executed
    assert ".execute(" in src
