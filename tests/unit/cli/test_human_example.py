from __future__ import annotations

import io

from rich.console import Console

from gemseo_gantry.artifacts import ArtifactKind, ArtifactStatus
from gemseo_gantry.cli._render import emit_human
from gemseo_gantry.cli._result import Artifact, CliResult, Diagnostic, Invocation


def _console() -> Console:
    return Console(file=io.StringIO(), width=100)


def _art(path: str, kind: ArtifactKind = ArtifactKind.EXAMPLE) -> Artifact:
    return Artifact(path=path, kind=kind, status=ArtifactStatus.WRITTEN)


def test_human_example_success_renders_name_dir_and_next():
    console = _console()
    result = CliResult(
        invocation=Invocation(command=["example"]),
        success=True,
        artifacts=[
            _art("sellar/sellar.toml", ArtifactKind.PROBLEM_DEFINITION),
            _art("sellar/lib/Sellar1_io.py"),
            _art("sellar/execute_Sellar.py", ArtifactKind.EXECUTOR),
        ],
    )
    emit_human(result, console)
    out = console.file.getvalue()
    assert "gantry example" in out
    assert "'sellar'" in out
    assert "sellar" in out  # the project dir
    # files listed relative to the project dir
    assert "lib/Sellar1_io.py" in out
    assert "execute_Sellar.py" in out
    # next-step line uses `uv run` without python
    assert "uv run sellar/execute_Sellar.py" in out
    assert "uv run python" not in out


def test_human_example_failure_renders_error():
    console = _console()
    result = CliResult(
        invocation=Invocation(command=["example"]),
        success=False,
        errors=[
            Diagnostic("usage", "sellar already exists. Use --force to overwrite.")
        ],
    )
    emit_human(result, console)
    out = console.file.getvalue()
    assert "Error:" in out
    assert "already exists" in out
