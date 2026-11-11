from __future__ import annotations

import tomllib
from os import PathLike

from slugify import slugify

from ..model.data_model import (
    Constraint,
    Discipline,
    Objective,
    ProblemDefinition,
    Scenario,
    Variable,
)
from .toml_data_model import TomlProblemDefinition
from .utils import pascalify, sanitize_identifier


def build_problem_definition(validated: TomlProblemDefinition) -> ProblemDefinition:
    """Transform a validated TomlProblemDefinition into the internal ProblemDefinition."""
    disciplines = [
        Discipline(
            name=sanitize_identifier(pascalify(key)),
            inputs=[
                sanitize_identifier(slugify(var, separator="_"))
                for var in toml_disc.inputs
            ],
            outputs=[
                sanitize_identifier(slugify(var, separator="_"))
                for var in toml_disc.outputs
            ],
        )
        for key, toml_disc in validated.disciplines.items()
    ]

    variables: list[Variable] = [
        Variable(
            name=sanitize_identifier(slugify(var.name, separator="_")),
            unit=var.unit,
            data_type=var.data_type,
            dimension=var.dimension,
            description=var.description,
            lower_bound=var.lower_bound,
            upper_bound=var.upper_bound,
            default_value=var.default_value,
        )
        for var in validated.variables
    ]

    scenarios: list[Scenario] = [
        Scenario(
            name=sanitize_identifier(pascalify(key)),
            design_variables=[
                sanitize_identifier(slugify(var, separator="_"))
                for var in ts.design_variables
            ],
            disciplines=[
                sanitize_identifier(pascalify(disc)) for disc in ts.disciplines
            ],
            formulation_type=ts.scenario_type,
            formulation=ts.formulation,
            objective=Objective(
                variable=sanitize_identifier(
                    slugify(ts.objective.variable, separator="_")
                ),
                maximize=ts.objective.maximize,
            ),
            constraints=[
                Constraint(
                    variable=sanitize_identifier(slugify(con.variable, separator="_")),
                    operator=con.operator,
                    value=con.value,
                )
                for con in ts.constraints
            ],
            observables=[
                sanitize_identifier(slugify(obs, separator="_"))
                for obs in ts.observables
            ],
        )
        for key, ts in validated.scenarios.items()
    ]

    problem = ProblemDefinition(
        variables=variables, disciplines=disciplines, scenarios=scenarios
    )

    design_var_names = {dv for s in scenarios for dv in s.design_variables}
    for var in problem.variables:
        if var.name in design_var_names:
            var.is_design_variable = True

    return problem


def parse_toml(file: str | PathLike[str]) -> ProblemDefinition:
    """Parse a TOML problem definition file into a ProblemDefinition."""
    with open(file, "rb") as f:
        raw = tomllib.load(f)
    validated = TomlProblemDefinition.model_validate(raw)
    return build_problem_definition(validated)
