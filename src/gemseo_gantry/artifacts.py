from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class ArtifactKind(StrEnum):
    DISCIPLINE_BASE = "discipline_base"
    DISCIPLINE_GRAMMAR = "discipline_grammar"
    DISCIPLINE_IO = "discipline_io"
    DISCIPLINE_SCAFFOLD = "discipline_scaffold"
    SCENARIO = "scenario"
    EXECUTOR = "executor"
    VARIABLES = "variables"
    DESIGN_SPACE = "design_space"
    PACKAGE_INIT = "package_init"
    DIAGRAM = "diagram"
    PROBLEM_DEFINITION = "problem_definition"
    SCHEMA = "schema"
    EXAMPLE = "example"
    DISCIPLINE = "discipline"
    POSTPROCESSOR = "postprocessor"


class ArtifactStatus(StrEnum):
    WRITTEN = "written"
    SKIPPED = "skipped"


@dataclass
class GeneratedArtifact:
    path: Path
    kind: ArtifactKind
    status: ArtifactStatus = ArtifactStatus.WRITTEN
