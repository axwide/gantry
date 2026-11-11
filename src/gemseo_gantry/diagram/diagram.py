from __future__ import annotations

from pathlib import Path

from gemseo import create_design_space, create_scenario, generate_n2_plot
from gemseo.core.coupling_structure import CouplingStructure
from gemseo.scenarios.base_scenario import BaseScenario
from gemseo.utils.discipline import DummyDiscipline

from gemseo_gantry.model.data_model import Discipline, ProblemDefinition, Scenario


def generate_n2(problem: ProblemDefinition, output_dir: Path, fmt: str = "pdf") -> None:
    import matplotlib

    matplotlib.use("Agg")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    disciplines = [
        DummyDiscipline(d.name, input_names=d.inputs, output_names=d.outputs)
        for d in problem.disciplines
    ]
    file_path = output_dir / f"n2.{fmt}"
    generate_n2_plot(disciplines, file_path=file_path, save=True, show=False)


def _build_dummy_scenario(
    problem: ProblemDefinition,
    scenario_def: Scenario,
    disc_map: dict[str, Discipline],
    scen_map: dict[str, Scenario],
) -> BaseScenario:
    """Build a GEMSEO scenario of dummy disciplines mirroring the nesting.

    Real disciplines become ``DummyDiscipline`` instances and each sub-scenario
    is built recursively and added as a discipline, so a bilevel root scenario
    renders its sub-scenarios.

    Args:
        problem: The parsed problem definition.
        scenario_def: The scenario to build.
        disc_map: Discipline name to model lookup.
        scen_map: Scenario name to model lookup.

    Returns:
        A GEMSEO scenario suitable for ``xdsmize``.
    """
    real_disciplines = [
        DummyDiscipline(
            disc_map[name].name,
            input_names=disc_map[name].inputs,
            output_names=disc_map[name].outputs,
        )
        for name in problem.plain_discipline_names_of(scenario_def)
    ]
    sub_scenarios = [
        _build_dummy_scenario(problem, scen_map[name], disc_map, scen_map)
        for name in problem.sub_scenario_names_of(scenario_def)
    ]
    disciplines = [*real_disciplines, *sub_scenarios]

    # Couplings are derived from the real disciplines only; CouplingStructure
    # cannot introspect nested scenarios, whose internal couplings the chosen
    # formulation resolves on its own.
    coupling_vars = set(CouplingStructure(real_disciplines).all_couplings)
    design_vars = set(scenario_def.design_variables)

    ds = create_design_space()
    for name in sorted(coupling_vars | design_vars):
        ds.add_variable(name)

    formulation = problem.resolve_formulation(scenario_def)
    scenario = create_scenario(
        disciplines,
        scenario_def.objective.variable,
        ds,
        name=scenario_def.name,
        formulation_name=formulation.value,
    )
    for constraint in scenario_def.constraints:
        scenario.add_constraint(constraint.variable)
    return scenario


def generate_xdsm(problem: ProblemDefinition, output_dir: Path) -> None:
    if not problem.scenarios:
        raise ValueError(
            "Cannot generate XDSM: no scenarios defined in the problem definition."
        )

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    disc_map = {d.name: d for d in problem.disciplines}
    scen_map = {s.name: s for s in problem.scenarios}

    # TODO: support multiple root scenarios (one XDSM per root). Multi-root is
    # currently blocked upstream in `validate`, so taking the first root keeps
    # this graceful for the single-root case until that restriction is lifted.
    if len(problem.root_scenarios) > 1:
        raise NotImplementedError(
            "Multiple root scenarios defined in the problem definition, not yet supported."
        )
    root_scenario = problem.root_scenarios[0]
    scenario = _build_dummy_scenario(problem, root_scenario, disc_map, scen_map)
    scenario.xdsmize(directory_path=output_dir, save_html=True, show_html=False)
