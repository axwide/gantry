from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ..model.data_model import DataType, FormulationType


class TomlDiscipline(BaseModel):
    model_config = ConfigDict(extra="forbid")

    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)


class TomlVariable(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    unit: str | None = None
    data_type: DataType
    dimension: int
    description: str | None = None
    lower_bound: float | list[float] | None = None
    upper_bound: float | list[float] | None = None
    default_value: float | list[float] | None = None


class TomlObjective(BaseModel):
    model_config = ConfigDict(extra="forbid")

    variable: str
    maximize: bool = False


class TomlConstraint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    variable: str
    operator: Literal["<", ">", "="] = "<"
    value: float = 0.0


class TomlScenario(BaseModel):
    model_config = ConfigDict(extra="forbid")

    design_variables: list[str]
    disciplines: list[str]
    scenario_type: Literal["DOE", "MDO"] = "MDO"
    formulation: FormulationType | None = None
    objective: TomlObjective
    constraints: list[TomlConstraint] = Field(default_factory=list)
    observables: list[str] = Field(default_factory=list)


class TomlProblemDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    disciplines: dict[str, TomlDiscipline]
    variables: list[TomlVariable] = Field(default_factory=list)
    scenarios: dict[str, TomlScenario] = Field(default_factory=dict)
