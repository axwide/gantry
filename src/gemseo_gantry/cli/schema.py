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


def schema(
    ctx: typer.Context,
    path: Annotated[
        Optional[Path],
        typer.Argument(
            help="Directory to write schema/problem.schema.json into",
            show_default="cwd",
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
    """Generate the JSON Schema for problem-definition TOML files.

    Called automatically by `gantry init` and `gantry build`, so run this
    directly only if you want to regenerate just the schema.
    """
    from ..schema import SCHEMA_DIRNAME, SCHEMA_FILENAME, write_schema

    if json_mode and quiet:
        raise typer.BadParameter("--json and --quiet are mutually exclusive")

    project_dir = path or Path.cwd()
    target = project_dir / SCHEMA_DIRNAME / SCHEMA_FILENAME
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

    written = write_schema(project_dir)
    if not quiet:
        envelope = CliResult(
            invocation=invocation_from_ctx(ctx),
            success=True,
            artifacts=[
                Artifact(
                    path=rel_to_cwd(written),
                    kind=ArtifactKind.SCHEMA,
                    status=ArtifactStatus.WRITTEN,
                )
            ],
        )
        if json_mode:
            emit_json(envelope)
        else:
            emit_human(envelope, console)
