from __future__ import annotations

from io import StringIO

from rich.console import Console

from gemseo_gantry.cli._common import ResolveError
from gemseo_gantry.cli._render import emit_human, render_resolve_error


def _console() -> tuple[Console, StringIO]:
    buf = StringIO()
    return Console(file=buf, force_terminal=False), buf


def test_render_resolve_error_rich_mode() -> None:
    """Human path writes a Rich panel to console."""
    console, buf = _console()
    exc = ResolveError("no .toml file found")

    render_resolve_error(exc, console)

    output = buf.getvalue()
    assert "no .toml file found" in output


def test_emit_human_diagram_rich_failure() -> None:
    from gemseo_gantry.cli._result import CliResult, Diagnostic, Invocation

    console, buf = _console()
    emit_human(
        CliResult(
            invocation=Invocation(command=["diagram", "n2"]),
            success=False,
            errors=[Diagnostic("usage", "something went wrong")],
        ),
        console,
    )
    assert "something went wrong" in buf.getvalue()


def test_emit_human_diagram_success_lists_files() -> None:
    from gemseo_gantry.cli._result import (
        Artifact,
        ArtifactKind,
        ArtifactStatus,
        CliResult,
        Invocation,
    )

    console, buf = _console()
    emit_human(
        CliResult(
            invocation=Invocation(
                command=["diagram", "n2"], params={"toml": "problem.toml"}
            ),
            success=True,
            artifacts=[
                Artifact(
                    path="diagrams/n2.pdf",
                    kind=ArtifactKind.DIAGRAM,
                    status=ArtifactStatus.WRITTEN,
                )
            ],
        ),
        console,
    )
    out = buf.getvalue()
    assert "Files created" in out
    assert "n2.pdf" in out


def test_emit_human_validate_valid_reads_source() -> None:
    from gemseo_gantry.cli._render import emit_human
    from gemseo_gantry.cli._result import CliResult, Invocation

    console, buf = _console()
    emit_human(
        CliResult(
            invocation=Invocation(
                command=["validate"], params={"toml": "problem.toml"}
            ),
            success=True,
        ),
        console,
    )
    out = buf.getvalue()
    assert "problem.toml is valid" in out


def test_emit_human_validate_file_not_found() -> None:
    from gemseo_gantry.cli._render import emit_human
    from gemseo_gantry.cli._result import CliResult, Diagnostic, Invocation

    console, buf = _console()
    emit_human(
        CliResult(
            invocation=Invocation(command=["validate"], params={"toml": "ghost.toml"}),
            success=False,
            errors=[Diagnostic("file_not_found", "File not found: ghost.toml")],
        ),
        console,
    )
    out = buf.getvalue()
    assert "File not found: ghost.toml" in out


def test_emit_human_build_success_derives_dir_and_source() -> None:
    from gemseo_gantry.cli._render import emit_human
    from gemseo_gantry.cli._result import (
        Artifact,
        ArtifactKind,
        ArtifactStatus,
        CliResult,
        Invocation,
    )

    console, buf = _console()
    emit_human(
        CliResult(
            invocation=Invocation(command=["build"], params={"toml": "problem.toml"}),
            success=True,
            artifacts=[
                Artifact(
                    path="out/lib/variables.py",
                    kind=ArtifactKind.VARIABLES,
                    status=ArtifactStatus.WRITTEN,
                ),
                Artifact(
                    path="schema/problem.schema.json",
                    kind=ArtifactKind.SCHEMA,
                    status=ArtifactStatus.WRITTEN,
                ),
            ],
        ),
        console,
    )
    out = buf.getvalue()
    assert "lib/ in" in out
    assert "out" in out
    assert "From:" in out
    assert "problem.toml" in out
    assert "variables.py" in out
    assert "problem.schema.json" not in out  # schema excluded from the build panel


def test_emit_human_scaffold_groups_by_status() -> None:
    from gemseo_gantry.cli._render import emit_human
    from gemseo_gantry.cli._result import (
        Artifact,
        ArtifactKind,
        ArtifactStatus,
        CliResult,
        Invocation,
    )

    console, buf = _console()
    emit_human(
        CliResult(
            invocation=Invocation(
                command=["scaffold"], params={"toml": "problem.toml"}
            ),
            success=True,
            artifacts=[
                Artifact(
                    path="disciplines/Drag_scaffold.py",
                    kind=ArtifactKind.DISCIPLINE_SCAFFOLD,
                    status=ArtifactStatus.WRITTEN,
                ),
                Artifact(
                    path="disciplines/Lift_scaffold.py",
                    kind=ArtifactKind.DISCIPLINE_SCAFFOLD,
                    status=ArtifactStatus.SKIPPED,
                ),
            ],
        ),
        console,
    )
    out = buf.getvalue()
    assert "Drag_scaffold.py" in out
    assert "written" in out.lower()
    assert "Lift_scaffold.py" in out
    assert "skipped" in out.lower()


def test_emit_human_init_success_uses_problem_definition_artifact() -> None:
    from gemseo_gantry.cli._render import emit_human
    from gemseo_gantry.cli._result import (
        Artifact,
        ArtifactKind,
        ArtifactStatus,
        CliResult,
        Invocation,
    )

    console, buf = _console()
    emit_human(
        CliResult(
            invocation=Invocation(command=["init"]),
            success=True,
            artifacts=[
                Artifact(
                    path="problem.toml",
                    kind=ArtifactKind.PROBLEM_DEFINITION,
                    status=ArtifactStatus.WRITTEN,
                ),
                Artifact(
                    path="schema/problem.schema.json",
                    kind=ArtifactKind.SCHEMA,
                    status=ArtifactStatus.WRITTEN,
                ),
            ],
        ),
        console,
    )
    out = buf.getvalue()
    assert "Files created" in out
    assert "problem.toml" in out
    assert "gantry build problem.toml" in out


def test_emit_human_schema_success_uses_schema_artifact() -> None:
    from gemseo_gantry.cli._render import emit_human
    from gemseo_gantry.cli._result import (
        Artifact,
        ArtifactKind,
        ArtifactStatus,
        CliResult,
        Invocation,
    )

    console, buf = _console()
    emit_human(
        CliResult(
            invocation=Invocation(command=["schema"]),
            success=True,
            artifacts=[
                Artifact(
                    path="schema/problem.schema.json",
                    kind=ArtifactKind.SCHEMA,
                    status=ArtifactStatus.WRITTEN,
                )
            ],
        ),
        console,
    )
    out = buf.getvalue()
    assert "Files created" in out
    assert "problem.schema.json" in out
