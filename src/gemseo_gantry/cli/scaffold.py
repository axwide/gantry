from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any, Optional

import lazy_loader as lazy
import typer
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel

_gantry: Any = lazy.load("gemseo_gantry")

from ._artifacts import rel_to_cwd  # noqa: E402
from ._common import (  # noqa: E402
    ResolveError,
    invocation_from_ctx,
    make_spinner,
    resolve_toml,
    run_validate,
)
from ._render import (  # noqa: E402
    emit_human,
    emit_json,
    render_resolve_error,
    render_warnings,
)
from ._result import (  # noqa: E402
    Artifact,
    CliResult,
    Diagnostic,
)

console = Console()

_ARTIFACT_ALIASES: dict[str, str] = {
    "d": "disciplines",
    "disciplines": "disciplines",
    "e": "executor",
    "executor": "executor",
    "l": "loader",
    "loader": "loader",
}


def _resolve_only(values: list[str]) -> frozenset[str]:
    resolved: set[str] = set()
    for val in values:
        for part in val.split(","):
            part = part.strip().lower()
            if part not in _ARTIFACT_ALIASES:
                raise ValueError(
                    f"Unknown artifact '{part}'. "
                    "Valid values: d/disciplines, e/executor, l/loader."
                )
            resolved.add(_ARTIFACT_ALIASES[part])
    return frozenset(resolved)


def _scaffold_failure_diagnostic(exc: Exception) -> Diagnostic:
    """Map a scaffold-generation failure to its CLI diagnostic.

    A missing or stale lib (``FileNotFoundError``) is a usage error with a fix hint;
    anything else is internal.
    """
    if isinstance(exc, FileNotFoundError):
        return Diagnostic(
            "usage",
            f"{exc} Run `gantry build` to (re)build it, or pass --lib-dir to point at "
            "where it wrote the package (e.g. --lib-dir src/lib after "
            "`gantry build --out src`).",
        )
    return Diagnostic("internal", str(exc))


def scaffold(
    ctx: typer.Context,
    toml: Annotated[
        Optional[Path],
        typer.Argument(
            help="Path to problem definition TOML file",
            show_default="auto-detect in cwd",
        ),
    ] = None,
    disciplines_into: Annotated[
        Optional[Path],
        typer.Option(
            "--disciplines-into",
            help="Directory for discipline stubs",
            show_default="<toml-dir>/disciplines",
        ),
    ] = None,
    executor_into: Annotated[
        Optional[Path],
        typer.Option(
            "--executor-into",
            help="Directory for scenario executor file",
            show_default="<toml-dir>",
        ),
    ] = None,
    lib_dir: Annotated[
        Optional[Path],
        typer.Option(
            "--lib-dir",
            help="Path to the lib directory produced by 'gantry build'",
            show_default="<toml-dir>/lib",
        ),
    ] = None,
    import_root: Annotated[
        Optional[Path],
        typer.Option(
            "--import-root",
            help="sys.path root for import path computation",
            show_default="cwd",
        ),
    ] = None,
    force: Annotated[
        bool, typer.Option("--force", "-f", help="Overwrite existing files")
    ] = False,
    only: Annotated[
        Optional[list[str]],
        typer.Option(
            "--only",
            help=(
                "Generate only the specified artifacts. "
                "Accepts d/disciplines, e/executor, l/loader. "
                "Repeat or comma-separate: --only d,e or --only d --only e."
            ),
            show_default="all",
        ),
    ] = None,
    runnable: Annotated[
        bool,
        typer.Option(
            "--runnable", help="Generate discipline stubs with placeholder outputs"
        ),
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
    """Generate discipline stubs and scenario executor from a problem definition TOML."""
    if json_mode and quiet:
        raise typer.BadParameter("--json and --quiet are mutually exclusive")

    if runnable and only is not None:
        try:
            resolved_only = _resolve_only(only)
        except ValueError as exc:
            diag = Diagnostic("usage", str(exc))
            if json_mode:
                emit_json(
                    CliResult(
                        invocation=invocation_from_ctx(ctx),
                        success=False,
                        errors=[diag],
                    )
                )
            else:
                console.print(
                    Panel(f"[red]Error:[/red] {escape(str(exc))}", style="red")
                )
            raise typer.Exit(code=1)
        if "disciplines" not in resolved_only:
            diag = Diagnostic(
                "usage", "--runnable requires disciplines to be generated."
            )
            if json_mode:
                emit_json(
                    CliResult(
                        invocation=invocation_from_ctx(ctx),
                        success=False,
                        errors=[diag],
                    )
                )
            else:
                console.print(
                    Panel(
                        "[red]Error:[/red] --runnable requires disciplines to be generated.",
                        style="red",
                    )
                )
            raise typer.Exit(code=1)

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
    elif not quiet and not json_mode:
        render_warnings(val_result.warnings, console)
        console.print(f"[green]✓[/green] {toml_path.name} is valid")

    if val_result.problem is None:  # pragma: no cover
        raise RuntimeError("run_validate returned valid=True but problem is None")

    toml_dir = toml_path.parent
    resolved_disciplines_into = disciplines_into or (toml_dir / "disciplines")
    resolved_executor_into = executor_into or toml_dir
    # CWD-relative (same location) so error messages show the path as other output does.
    resolved_lib_dir = Path(rel_to_cwd(lib_dir or (toml_dir / "lib")))
    resolved_import_root = import_root or Path.cwd()

    try:
        artifacts = _resolve_only(only) if only else _gantry.ALL_ARTIFACTS
    except ValueError as exc:
        diag = Diagnostic("usage", str(exc))
        if json_mode:
            emit_json(
                CliResult(
                    invocation=invocation_from_ctx(ctx, toml=toml_path.name),
                    success=False,
                    errors=[diag],
                )
            )
        else:
            console.print(Panel(f"[red]Error:[/red] {escape(str(exc))}", style="red"))
        raise typer.Exit(code=1)

    try:
        with make_spinner(console, "Scaffolding…", quiet=quiet, json_mode=json_mode):
            output = _gantry.generate_scaffold(
                val_result.problem,
                disciplines_into=resolved_disciplines_into,
                lib_dir=resolved_lib_dir,
                executor_into=resolved_executor_into,
                import_root=resolved_import_root,
                artifacts=artifacts,
                force=force,
                runnable=runnable,
            )
    except Exception as exc:
        diag = _scaffold_failure_diagnostic(exc)
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

    json_artifacts: list[Artifact] = [
        Artifact(path=rel_to_cwd(a.path), kind=a.kind, status=a.status) for a in output
    ]
    if not quiet:
        envelope = CliResult(
            invocation=invocation_from_ctx(ctx, toml=toml_path.name),
            success=True,
            artifacts=json_artifacts,
            warnings=val_result.warnings,
        )
        if json_mode:
            emit_json(envelope)
        else:
            emit_human(envelope, console)
