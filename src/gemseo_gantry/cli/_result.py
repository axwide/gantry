from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING

import pydantic
from pydantic import BaseModel, ConfigDict

from gemseo_gantry.artifacts import ArtifactKind, ArtifactStatus

if TYPE_CHECKING:  # pragma: no cover
    from ..model.data_model import ProblemDefinition


@pydantic.dataclasses.dataclass(config=ConfigDict(extra="forbid"))
class Diagnostic:
    type: str  # "file_not_found" | "syntax" | "structural" | "semantic" | "usage" | "internal"
    message: str
    loc: str | None = None

    def to_dict(self) -> dict[str, object]:
        d: dict[str, object] = {"type": self.type, "message": self.message}
        if self.loc is not None:
            d["loc"] = self.loc
        return d


class Command(StrEnum):
    INIT = "init"
    VALIDATE = "validate"
    BUILD = "build"
    SCAFFOLD = "scaffold"
    DIAGRAM = "diagram"
    SCHEMA = "schema"
    EXAMPLE = "example"


class Artifact(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path: str
    kind: ArtifactKind
    status: ArtifactStatus


class Invocation(BaseModel):
    """The command line that produced a :class:`CliResult`.

    Attributes:
        command: The command chain minus the program name, in order, so that
            sub- and sub-sub-commands are preserved (e.g. ``["diagram", "n2"]``).
        params: Each argument and option keyed by its CLI name (``format`` for
            ``--format``), mapped to the value it was invoked with. Includes
            meta flags such as ``quiet`` and ``json``.
    """

    model_config = ConfigDict(extra="forbid")
    command: list[str]
    params: dict[str, object] = {}


class CliResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    invocation: Invocation
    success: bool
    artifacts: list[Artifact] = []
    warnings: list[Diagnostic] = []
    errors: list[Diagnostic] = []


@dataclass
class ValidateResult:
    valid: bool
    file: str
    warnings: list[Diagnostic] = field(default_factory=list)
    errors: list[Diagnostic] = field(default_factory=list)
    problem: ProblemDefinition | None = field(default=None, repr=False)
