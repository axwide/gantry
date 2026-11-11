from __future__ import annotations

import shutil
from enum import Enum
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.panel import Panel

from ..examples.registry import available_names, get_example
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

ExampleName = Enum("ExampleName", {n: n for n in available_names()}, type=str)  # type: ignore[misc]


def example(
    ctx: typer.Context,
    name: Annotated[
        ExampleName,  # type: ignore[valid-type]
        typer.Argument(help="Example to generate"),
    ],
    path: Annotated[
        Optional[Path],
        typer.Argument(help="Parent directory", show_default="current directory"),
    ] = None,
    explain: Annotated[
        bool,
        typer.Option(
            "--explain",
            help="Narrate the generation workflow stage by stage (conflicts with --quiet, --json, --dump-toml)",
        ),
    ] = False,
    dump_toml: Annotated[
        bool,
        typer.Option(
            "--dump-toml",
            help="Write only the problem definition TOML to the output directory (conflicts with --explain)",
        ),
    ] = False,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Overwrite existing files"),
    ] = False,
    quiet: Annotated[
        bool,
        typer.Option(
            "--quiet",
            "-q",
            help="Suppress output (conflicts with --json, --explain)",
        ),
    ] = False,
    json_mode: Annotated[
        bool,
        typer.Option(
            "--json",
            "-j",
            help="Emit machine-readable JSON to stdout (conflicts with --quiet, --explain)",
        ),
    ] = False,
) -> None:
    """Generate a complete, runnable example project."""
    if json_mode and quiet:
        raise typer.BadParameter("--json and --quiet are mutually exclusive")
    if explain and quiet:
        raise typer.BadParameter("--explain and --quiet are mutually exclusive")
    if explain and json_mode:
        raise typer.BadParameter("--explain and --json are mutually exclusive")
    if dump_toml and explain:
        raise typer.BadParameter("--dump-toml and --explain are mutually exclusive")

    ex = get_example(name.value)

    if dump_toml:
        output_dir = path or Path.cwd()
        toml_name = f"{name.value}.toml"
        dest = output_dir / toml_name
        shutil.copy2(ex.root / toml_name, dest)
        artifact = Artifact(
            path=rel_to_cwd(dest),
            kind=ArtifactKind.PROBLEM_DEFINITION,
            status=ArtifactStatus.WRITTEN,
        )
        envelope = CliResult(
            invocation=invocation_from_ctx(ctx), success=True, artifacts=[artifact]
        )
        if json_mode:
            emit_json(envelope)
        elif not quiet:
            console.print(
                Panel(
                    f"[green]Files created:[/green]\n  • {rel_to_cwd(dest)}",
                    title="gantry example --dump-toml",
                    style="green",
                )
            )
        return

    target = (path or Path.cwd()) / name.value

    if (
        not force
        and target.exists()
        and any(p for p in target.iterdir() if not p.name.startswith("."))
    ):
        diag = Diagnostic(
            "usage", f"{target} already exists. Use --force to overwrite."
        )
        envelope = CliResult(
            invocation=invocation_from_ctx(ctx), success=False, errors=[diag]
        )
        if json_mode:
            emit_json(envelope)
        elif not quiet:
            emit_human(envelope, console)
        raise typer.Exit(code=1)

    if explain and not quiet:
        # Local import: lazy.load/lazy.attach don't help for `from pkg import submodule`.
        from ._walkthrough import run_walkthrough

        arts = run_walkthrough(ex, target, console)
        cli_artifacts = [
            Artifact(
                path=rel_to_cwd(a.path),
                kind=ArtifactKind.EXAMPLE,
                status=ArtifactStatus.WRITTEN,
            )
            for a in arts
        ]
        if cli_artifacts:
            emit_human(
                CliResult(
                    invocation=invocation_from_ctx(ctx),
                    success=True,
                    artifacts=cli_artifacts,
                ),
                console,
            )
        return

    try:
        from ..examples.runner import generate_example

        run = generate_example(ex, target)
    except Exception as exc:  # pragma: no cover - defensive
        diag = Diagnostic("internal", str(exc))
        envelope = CliResult(
            invocation=invocation_from_ctx(ctx), success=False, errors=[diag]
        )
        if json_mode:
            emit_json(envelope)
        elif not quiet:
            emit_human(envelope, console)
        raise typer.Exit(code=1)

    cli_artifacts = [
        Artifact(
            path=rel_to_cwd(a.path),
            kind=ArtifactKind(a.kind),
            status=ArtifactStatus.WRITTEN,
        )
        for a in run.artifacts
    ]
    envelope = CliResult(
        invocation=invocation_from_ctx(ctx), success=True, artifacts=cli_artifacts
    )
    if json_mode:
        emit_json(envelope)
    elif not quiet:
        emit_human(envelope, console)
