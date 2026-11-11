from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError
from pydantic_core import ErrorDetails

from ..model.data_model import ProblemDefinition
from ..parser.toml_data_model import TomlProblemDefinition
from ..parser.toml_parser import build_problem_definition
from . import semantic


@dataclass
class ValidationResult:
    problem: ProblemDefinition
    warnings: list[str]


class SemanticValidationError(ValueError):
    """Raised when semantic checks fail.

    Carries the warnings gathered in the same pass so callers can still surface
    them alongside the errors instead of discarding them.
    """

    def __init__(self, errors: list[str], warnings: list[str]) -> None:
        super().__init__("\n".join(errors))
        self.warnings = warnings


def _fmt_pydantic_error(error: ErrorDetails) -> str:
    loc = error.get("loc", ())
    msg = error["msg"].removeprefix("Value error, ")
    if loc:
        loc_str = " -> ".join(str(p) for p in loc)
        return f"{loc_str}: {msg}"
    return msg


def validate_toml(path: Path) -> ValidationResult:
    with open(path, "rb") as f:
        raw = tomllib.load(f)

    try:
        parsed = TomlProblemDefinition.model_validate(raw)
    except ValidationError as exc:
        messages = [_fmt_pydantic_error(e) for e in exc.errors(include_url=False)]
        raise ValueError("\n".join(messages)) from exc

    errors, warnings = semantic.run_all(parsed)
    if errors:
        raise SemanticValidationError(errors, warnings)

    return ValidationResult(
        problem=build_problem_definition(parsed),
        warnings=warnings,
    )
