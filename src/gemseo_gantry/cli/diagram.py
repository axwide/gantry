from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Annotated, Any, Optional

import lazy_loader as lazy
import typer
from rich.console import Console

_gantry: Any = lazy.load("gemseo_gantry")

from ._artifacts import rel_to_cwd  # noqa: E402
from ._common import (  # noqa: E402
    ResolveError,
    invocation_from_ctx,
    make_spinner,
    resolve_toml,
    run_validate,
)
from ._render import emit_human, emit_json, render_resolve_error  # noqa: E402
from ._result import (  # noqa: E402
    Artifact,
    ArtifactKind,
    ArtifactStatus,
    CliResult,
    Diagnostic,
)

console = Console()

diagram_app = typer.Typer(no_args_is_help=True)


class N2Format(str, Enum):
    pdf = "pdf"
    png = "png"
    svg = "svg"


@diagram_app.command("n2")
def n2_command(
    ctx: typer.Context,
    toml: Annotated[
        Optional[Path],
        typer.Argument(
            help="Path to problem definition TOML file",
            show_default="auto-detect in cwd",
        ),
    ] = None,
    fmt: Annotated[
        N2Format, typer.Option("--format", help="N2 output format")
    ] = N2Format.pdf,
    output_dir: Annotated[
        Optional[Path],
        typer.Option(
            "--output-dir",
            help="Output directory",
            show_default="<toml-dir>/diagrams",
        ),
    ] = None,
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
    """Generate N2 diagram from a problem definition TOML.

    Writes n2.html (interactive) alongside the static file selected by --format.
    Requires at least two disciplines.
    """
    if json_mode and quiet:
        raise typer.BadParameter("--json and --quiet are mutually exclusive")

    try:
        toml_path = resolve_toml(toml)
    except ResolveError as exc:
        diag = Diagnostic("usage", str(exc))
        if json_mode:
            emit_json(
                CliResult(
                    invocation=invocation_from_ctx(ctx), success=False, errors=[diag]
                )
            )
        else:
            render_resolve_error(exc, console)
        raise typer.Exit(code=1)

    val_result = run_validate(toml_path)
    if not val_result.valid:
        envelope = CliResult(
            invocation=invocation_from_ctx(ctx, toml=toml_path.name),
            success=False,
            warnings=val_result.warnings,
            errors=val_result.errors,
        )
        if json_mode:
            emit_json(envelope)
        else:
            emit_human(envelope, console)
        raise typer.Exit(code=1)

    if val_result.problem is None:  # pragma: no cover
        raise RuntimeError("run_validate returned valid=True but problem is None")

    problem = val_result.problem

    out = output_dir if output_dir is not None else toml_path.parent / "diagrams"
    out.mkdir(parents=True, exist_ok=True)

    with make_spinner(console, "Generating N2…", quiet=quiet, json_mode=json_mode):
        _gantry.generate_n2(problem, out, fmt=fmt.value)
    generated_files = [out / f"n2.{fmt.value}", out / "n2.html"]

    if not quiet:
        envelope = CliResult(
            invocation=invocation_from_ctx(ctx, toml=toml_path.name),
            success=True,
            artifacts=[
                Artifact(
                    path=rel_to_cwd(f),
                    kind=ArtifactKind.DIAGRAM,
                    status=ArtifactStatus.WRITTEN,
                )
                for f in generated_files
            ],
            warnings=val_result.warnings,
        )
        if json_mode:
            emit_json(envelope)
        else:
            emit_human(envelope, console)


@diagram_app.command("xdsm")
def xdsm_command(
    ctx: typer.Context,
    toml: Annotated[
        Optional[Path],
        typer.Argument(
            help="Path to problem definition TOML file",
            show_default="auto-detect in cwd",
        ),
    ] = None,
    output_dir: Annotated[
        Optional[Path],
        typer.Option(
            "--output-dir",
            help="Output directory",
            show_default="<toml-dir>/diagrams",
        ),
    ] = None,
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
    """Generate XDSM diagram from a problem definition TOML.

    Writes xdsm.html. Requires at least one scenario.
    """
    if json_mode and quiet:
        raise typer.BadParameter("--json and --quiet are mutually exclusive")

    try:
        toml_path = resolve_toml(toml)
    except ResolveError as exc:
        diag = Diagnostic("usage", str(exc))
        if json_mode:
            emit_json(
                CliResult(
                    invocation=invocation_from_ctx(ctx), success=False, errors=[diag]
                )
            )
        else:
            render_resolve_error(exc, console)
        raise typer.Exit(code=1)

    val_result = run_validate(toml_path)
    if not val_result.valid:
        envelope = CliResult(
            invocation=invocation_from_ctx(ctx, toml=toml_path.name),
            success=False,
            warnings=val_result.warnings,
            errors=val_result.errors,
        )
        if json_mode:
            emit_json(envelope)
        else:
            emit_human(envelope, console)
        raise typer.Exit(code=1)

    if val_result.problem is None:  # pragma: no cover
        raise RuntimeError("run_validate returned valid=True but problem is None")

    problem = val_result.problem

    out = output_dir if output_dir is not None else toml_path.parent / "diagrams"
    out.mkdir(parents=True, exist_ok=True)

    if not problem.scenarios:
        diag = Diagnostic(
            "usage", "XDSM requested but no scenarios are defined in the TOML."
        )
        envelope = CliResult(
            invocation=invocation_from_ctx(ctx, toml=toml_path.name),
            success=False,
            warnings=val_result.warnings,
            errors=[diag],
        )
        if json_mode:
            emit_json(envelope)
        else:
            emit_human(envelope, console)
        raise typer.Exit(code=1)

    with make_spinner(console, "Generating XDSM…", quiet=quiet, json_mode=json_mode):
        _gantry.generate_xdsm(problem, out)
    generated_files = [out / "xdsm.html"]

    if not quiet:
        envelope = CliResult(
            invocation=invocation_from_ctx(ctx, toml=toml_path.name),
            success=True,
            artifacts=[
                Artifact(
                    path=rel_to_cwd(f),
                    kind=ArtifactKind.DIAGRAM,
                    status=ArtifactStatus.WRITTEN,
                )
                for f in generated_files
            ],
            warnings=val_result.warnings,
        )
        if json_mode:
            emit_json(envelope)
        else:
            emit_human(envelope, console)
