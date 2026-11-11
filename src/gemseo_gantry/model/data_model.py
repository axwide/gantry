import keyword
import math
from enum import StrEnum
from typing import Any, List, Literal

from pydantic import BaseModel, Field, computed_field, field_validator


def _validate_identifier(v: str) -> str:
    if not v or not v.isidentifier() or keyword.iskeyword(v):
        raise ValueError(f"Name {v!r} is not a valid Python identifier")
    return v


class DataType(StrEnum):
    FLOAT = "float"
    INTEGER = "integer"


class FormulationType(StrEnum):
    MDF = "MDF"
    IDF = "IDF"
    BILEVEL = "BiLevel"
    BILEVEL_BCD = "BiLevelBCD"


BILEVEL_FORMULATIONS = frozenset({FormulationType.BILEVEL, FormulationType.BILEVEL_BCD})


def _expand(value: float | list[float] | None, dimension: int) -> list[float] | None:
    """Broadcast a scalar to a length-`dimension` list; pass lists through; keep None."""
    if value is None:
        return None
    if isinstance(value, list):
        return value
    return [value for _ in range(dimension)]


class Variable(BaseModel):
    name: str
    unit: str | None = None
    data_type: DataType
    dimension: int
    description: str | None = None
    lower_bound: float | list[float] | None = None
    upper_bound: float | list[float] | None = None
    default_value: float | list[float] | None = None
    is_design_variable: bool = False

    @field_validator("name")
    @classmethod
    def validate_name_is_identifier(cls, v: str) -> str:
        return _validate_identifier(v)

    def lower_bounds(self) -> list[float] | None:
        return _expand(self.lower_bound, self.dimension)

    def upper_bounds(self) -> list[float] | None:
        return _expand(self.upper_bound, self.dimension)

    def default_values(self) -> list[float] | None:
        return _expand(self.default_value, self.dimension)


class Discipline(BaseModel):
    name: str
    inputs: List[str] = []
    outputs: List[str] = []

    @field_validator("name")
    @classmethod
    def validate_name_is_identifier(cls, v: str) -> str:
        return _validate_identifier(v)


class Constraint(BaseModel):
    variable: str
    operator: Literal["<", ">", "="]
    value: float

    @computed_field  # type: ignore[prop-decorator]
    @property
    def constraint_type(self) -> str:
        if self.operator == "=":
            return "eq"
        return "ineq"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def positive(self) -> bool:
        return self.operator == ">"


class Objective(BaseModel):
    variable: str
    maximize: bool = False


class Scenario(BaseModel):
    name: str
    design_variables: List[str]
    disciplines: List[str]
    formulation_type: Literal["DOE", "MDO"]
    formulation: FormulationType | None = None
    objective: Objective
    constraints: List[Constraint]
    observables: List[str] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def validate_name_is_identifier(cls, v: str) -> str:
        return _validate_identifier(v)


class ProblemDefinition(BaseModel):
    variables: List[Variable]
    disciplines: List[Discipline]
    scenarios: List[Scenario] = Field(default_factory=list)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def relations(self) -> dict[str, dict[str, list[str]]]:
        """Derive variable-to-discipline relations from discipline I/O lists."""
        rels: dict[str, dict[str, list[str]]] = {}
        for disc in self.disciplines:
            for var_name in disc.inputs:
                rels.setdefault(var_name, {"input": [], "output": []})
                rels[var_name]["input"].append(disc.name)
            for var_name in disc.outputs:
                rels.setdefault(var_name, {"input": [], "output": []})
                rels[var_name]["output"].append(disc.name)
        return rels

    @property
    def design_space(self) -> list[dict[str, Any]]:
        # An absent bound maps to -inf/+inf, matching GEMSEO's DesignSpace
        # convention. These render as "inf"/"-inf" in design_space.csv, which
        # DesignSpace.from_csv parses back to numpy infinities. An absent default
        # renders as the literal "None", which from_csv reads as "no current
        # value" (an empty cell would be parsed as NaN and rejected). Validation
        # still requires a default for design variables.
        rows: list[dict[str, Any]] = []
        for var in self.variables:
            if not var.is_design_variable:
                continue
            n = var.dimension
            _lowers = var.lower_bounds()
            lowers: list[float] = _lowers if _lowers is not None else [-math.inf] * n
            _values = var.default_values()
            values: list[Any] = _values if _values is not None else ["None"] * n
            _uppers = var.upper_bounds()
            uppers: list[float] = _uppers if _uppers is not None else [math.inf] * n
            for lower, value, upper in zip(lowers, values, uppers):
                rows.append(
                    {
                        "name": var.name,
                        "lower_bound": lower,
                        "value": value,
                        "upper_bound": upper,
                        "type": var.data_type,
                    }
                )
        return rows

    @property
    def _scenario_names(self) -> set[str]:
        return {s.name for s in self.scenarios}

    def sub_scenario_names_of(self, scenario: Scenario) -> list[str]:
        """Names in this scenario's disciplines that are themselves scenarios."""
        names = self._scenario_names
        return [d for d in scenario.disciplines if d in names]

    def plain_discipline_names_of(self, scenario: Scenario) -> list[str]:
        """Names in this scenario's disciplines that are real disciplines."""
        names = self._scenario_names
        return [d for d in scenario.disciplines if d not in names]

    @property
    def sub_scenario_names(self) -> set[str]:
        """Every scenario name that is nested under some other scenario."""
        return {
            name
            for scenario in self.scenarios
            for name in self.sub_scenario_names_of(scenario)
        }

    @property
    def root_scenarios(self) -> list[Scenario]:
        """Scenarios not nested under any other scenario."""
        subs = self.sub_scenario_names
        return [s for s in self.scenarios if s.name not in subs]

    def construction_order(self, root: Scenario) -> list[Scenario]:
        """Return scenarios in post-order DFS: sub-scenarios before parents.

        Walks the nesting graph from ``root`` so that every sub-scenario
        precedes the scenario that nests it, with ``root`` last. This is the
        order in which scenarios must be constructed, since a parent scenario
        consumes its already-built sub-scenarios.

        Args:
            root: The root scenario to traverse from.

        Returns:
            Scenarios ordered sub-scenarios first, ``root`` last.
        """
        by_name = {s.name: s for s in self.scenarios}
        ordered: list[Scenario] = []
        seen: set[str] = set()

        def visit(scenario: Scenario) -> None:
            for sub_name in self.sub_scenario_names_of(scenario):
                sub = by_name[sub_name]
                if sub.name not in seen:
                    visit(sub)
            if scenario.name not in seen:
                seen.add(scenario.name)
                ordered.append(scenario)

        visit(root)
        return ordered

    def resolve_formulation(self, scenario: Scenario) -> FormulationType:
        """Return the scenario's effective formulation.

        Uses the scenario's declared ``formulation`` when set; otherwise applies
        a nesting-based default: ``BiLevelBCD`` when the scenario has
        sub-scenarios, and ``MDF`` when it does not.

        Args:
            scenario: The scenario whose formulation to resolve.

        Returns:
            The declared formulation, or the nesting-based default when none is
            declared.
        """
        if scenario.formulation is not None:
            return scenario.formulation
        if self.sub_scenario_names_of(scenario):
            return FormulationType.BILEVEL_BCD
        return FormulationType.MDF
