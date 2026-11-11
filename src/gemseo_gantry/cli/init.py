from __future__ import annotations

from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console

from ._artifacts import rel_to_cwd
from ._common import invocation_from_ctx
from ._render import emit_human, emit_json
from ._result import (
    Artifact,
    ArtifactKind,
    ArtifactStatus,
    CliResult,
    Diagnostic,
)

console = Console()

_TEMPLATE = Path(__file__).parent / "templates" / "problem.toml"


def init(
    ctx: typer.Context,
    path: Annotated[
        Optional[Path],
        typer.Argument(
            help="Where to write the template", show_default="./problem.toml"
        ),
    ] = None,
    force: Annotated[
        bool, typer.Option("--force", "-f", help="Overwrite existing files")
    ] = False,
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Suppress output (conflicts with --json)"),
    ] = False,
    json_mode: Annotated[
        bool,
        typer.Option(
            "--json",
            "-j",
            help="Emit machine-readable JSON to stdout (conflicts with --quiet)",
        ),
    ] = False,
) -> None:
    """Create a problem definition template TOML file."""
    if json_mode and quiet:
        raise typer.BadParameter("--json and --quiet are mutually exclusive")

    target = path or Path("problem.toml")

    if target.suffix.lower() != ".toml":
        diag = Diagnostic("usage", f"{target} does not have a .toml extension.")
        envelope = CliResult(
            invocation=invocation_from_ctx(ctx), success=False, errors=[diag]
        )
        if json_mode:
            emit_json(envelope)
        else:
            emit_human(envelope, console)
        raise typer.Exit(code=1)

    if target.exists() and not force:
        diag = Diagnostic(
            "usage", f"{target} already exists. Use --force to overwrite."
        )
        envelope = CliResult(
            invocation=invocation_from_ctx(ctx), success=False, errors=[diag]
        )
        if json_mode:
            emit_json(envelope)
        else:
            emit_human(envelope, console)
        raise typer.Exit(code=1)

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(_TEMPLATE.read_text(encoding="utf-8"), encoding="utf-8")

    from ..schema import write_schema

    schema_path = write_schema(target.parent)

    if not quiet:
        envelope = CliResult(
            invocation=invocation_from_ctx(ctx),
            success=True,
            artifacts=[
                Artifact(
                    path=rel_to_cwd(target),
                    kind=ArtifactKind.PROBLEM_DEFINITION,
                    status=ArtifactStatus.WRITTEN,
                ),
                Artifact(
                    path=rel_to_cwd(schema_path),
                    kind=ArtifactKind.SCHEMA,
                    status=ArtifactStatus.WRITTEN,
                ),
            ],
        )
        if json_mode:
            emit_json(envelope)
        else:
            emit_human(envelope, console)
