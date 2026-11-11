from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from gemseo_gantry.generator import generate_lib
from gemseo_gantry.parser.toml_parser import parse_toml

from .narration import NarrationStep, build_narration
from .registry import Example

if TYPE_CHECKING:
    from gemseo_gantry.model.data_model import ProblemDefinition


@dataclass
class ExampleArtifact:
    path: Path  # absolute path to the written file
    kind: str  # matches an ArtifactKind string value


@dataclass
class ExampleRun:
    target: Path
    artifacts: list[ExampleArtifact] = field(default_factory=list)
    narration: list[NarrationStep] = field(default_factory=list)


def _copy_tree(src: Path, dst: Path) -> list[ExampleArtifact]:
    artifacts: list[ExampleArtifact] = []
    for item in sorted(src.rglob("*")):
        if item.name == "__pycache__" or "__pycache__" in item.parts:
            continue
        rel = item.relative_to(src)
        out = dst / rel
        if item.is_dir():
            out.mkdir(parents=True, exist_ok=True)
        else:
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, out)
            kind = "package_init" if item.name == "__init__.py" else "discipline"
            artifacts.append(ExampleArtifact(path=out, kind=kind))
    return artifacts


def _write_toml(example: Example, target: Path) -> list[ExampleArtifact]:
    """Copy the example's `{name}.toml` into the target project root."""
    target.mkdir(parents=True, exist_ok=True)
    toml_name = f"{example.name}.toml"
    shutil.copy2(example.root / toml_name, target / toml_name)
    return [ExampleArtifact(path=target / toml_name, kind="problem_definition")]


def _build_lib(problem: ProblemDefinition, target: Path) -> list[ExampleArtifact]:
    """Generate the mechanical lib/ package; generate_lib reports what it wrote."""
    lib_artifacts = generate_lib(problem, target, lib_name="lib")
    return [ExampleArtifact(path=a.path, kind=a.kind.value) for a in lib_artifacts]


def _clean_scaffold_stubs(target: Path) -> None:
    """Remove anything a `gantry scaffold` run leaves that the finished files replace.

    Scaffold writes `disciplines/*_scaffold.py` discipline stubs and a whole
    `scenarios/` directory (executor + loader). The finished example ships
    `disciplines/<Name>.py`, a root `execute_<Name>.py`, and `postprocess.py`,
    so the stubs and the scenarios/ dir must go. A no-op when no stubs exist
    (the plain path never runs scaffold).
    """
    for stub in target.glob("disciplines/*_scaffold.py"):
        stub.unlink()
    scenarios = target / "scenarios"
    if scenarios.is_dir():
        shutil.rmtree(scenarios)


def _fill_finished_files(example: Example, target: Path) -> list[ExampleArtifact]:
    """Clean scaffold stubs, then copy the shipped finished owned files."""
    _clean_scaffold_stubs(target)
    artifacts: list[ExampleArtifact] = []

    artifacts.extend(_copy_tree(example.root / "disciplines", target / "disciplines"))

    executor_name = example.executor
    shutil.copy2(example.root / executor_name, target / executor_name)
    artifacts.append(ExampleArtifact(path=target / executor_name, kind="executor"))

    shutil.copy2(example.root / "postprocess.py", target / "postprocess.py")
    artifacts.append(
        ExampleArtifact(path=target / "postprocess.py", kind="postprocessor")
    )
    return artifacts


def generate_diagrams(
    problem: ProblemDefinition, target: Path
) -> list[ExampleArtifact]:
    """Write N2 + XDSM diagrams into target/diagrams/ (files only; never displayed)."""
    # Local import: gemseo is heavy; only load it when diagrams are actually generated.
    from gemseo_gantry.diagram import generate_n2, generate_xdsm

    diagrams = target / "diagrams"
    generate_n2(problem, diagrams)
    generate_xdsm(problem, diagrams)
    return [
        ExampleArtifact(path=p, kind="diagram")
        for p in sorted(diagrams.rglob("*"))
        if p.is_file()
    ]


def generate_example(
    example: Example,
    target: Path,
    *,
    with_diagrams: bool = True,
) -> ExampleRun:
    """Generate the example project into ``target`` (in-process, no execution).

    Stages: write {name}.toml -> build lib/ -> fill finished owned files ->
    (optionally) generate diagrams. Scaffold is intentionally skipped: it only
    produces throwaway stubs the finished files immediately replace. Nothing is
    executed; the executor and post-processor are --explain-only stages.
    """
    target = Path(target)
    artifacts: list[ExampleArtifact] = []

    toml_arts = _write_toml(example, target)
    artifacts.extend(toml_arts)

    toml_name = f"{example.name}.toml"
    problem = parse_toml(target / toml_name)
    lib_arts = _build_lib(problem, target)
    artifacts.extend(lib_arts)

    fill_arts = _fill_finished_files(example, target)
    artifacts.extend(fill_arts)

    diagram_arts: list[ExampleArtifact] = []
    if with_diagrams:
        diagram_arts = generate_diagrams(problem, target)
        artifacts.extend(diagram_arts)

    lib_rels = [str(a.path.relative_to(target)) for a in lib_arts]
    discipline_rels = [
        str(a.path.relative_to(target)) for a in fill_arts if a.kind == "discipline"
    ]
    diagram_rels = [str(a.path.relative_to(target)) for a in diagram_arts]
    executor_name = f"execute_{example.name.capitalize()}.py"
    artifacts_by_step = {
        1: [toml_name],
        3: lib_rels,
        4: diagram_rels,
        6: discipline_rels,
        7: [executor_name],
        8: ["postprocess.py"],
    }
    narration = build_narration(example, artifacts_by_step=artifacts_by_step)
    return ExampleRun(target=target, artifacts=artifacts, narration=narration)
