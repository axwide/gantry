from __future__ import annotations

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
from ._render import (  # noqa: E402
    emit_human,
    emit_json,
    render_resolve_error,
    render_warnings,
)
from ._result import (  # noqa: E402
    Artifact,
    ArtifactKind,
    ArtifactStatus,
    CliResult,
    Diagnostic,
)

console = Console()


def build(
    ctx: typer.Context,
    toml: Annotated[
        Optional[Path],
        typer.Argument(
            help="Path to problem definition TOML file",
            show_default="auto-detect in cwd",
        ),
    ] = None,
    out: Annotated[
        Optional[Path],
        typer.Option(
            "--out", "-o", help="Output directory", show_default="TOML parent dir"
        ),
    ] = None,
    lib_name: Annotated[
        str,
        typer.Option("--lib-name", help="Name of the generated lib package directory"),
    ] = "lib",
    flat: Annotated[
        bool,
        typer.Option(
            "--flat",
            help="Use when generating directly into your source root (e.g. src/ or the project root). Prevents a spurious __init__.py that breaks type-checker import resolution.",
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
    """Generate the GEMSEO lib package from a problem definition TOML."""
    if json_mode and quiet:
        raise typer.BadParameter("--json and --quiet are mutually exclusive")

    import keyword

    from slugify import slugify

    if not lib_name.isidentifier() or keyword.iskeyword(lib_name):
        suggestion = slugify(lib_name, separator="_")
        diag = Diagnostic(
            "usage",
            f"--lib-name {lib_name!r} is not a valid Python package name. "
            f"Use only letters, digits, and underscores (e.g. {suggestion!r}).",
        )
        envelope = CliResult(
            invocation=invocation_from_ctx(ctx), success=False, errors=[diag]
        )
        if json_mode:
            emit_json(envelope)
        else:
            emit_human(envelope, console)
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

    out_dir = out or toml_path.parent

    try:
        with make_spinner(console, "Building…", quiet=quiet, json_mode=json_mode):
            lib_artifacts = _gantry.generate_lib(
                val_result.problem, out_dir, lib_name=lib_name, is_import_root=flat
            )
    except Exception as exc:
        diag = Diagnostic("internal", str(exc))
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

    lib_arts_sorted = sorted(lib_artifacts, key=lambda a: a.path.name)
    from ..schema import write_schema

    schema_path = write_schema(
        toml_path.parent
    )  # intentionally beside the TOML, not lib/ (--out doesn't affect this)
    if not quiet:
        artifacts = [
            Artifact(path=rel_to_cwd(a.path), kind=a.kind, status=a.status)
            for a in lib_arts_sorted
        ] + [
            Artifact(
                path=rel_to_cwd(schema_path),
                kind=ArtifactKind.SCHEMA,
                status=ArtifactStatus.WRITTEN,
            )
        ]
        envelope = CliResult(
            invocation=invocation_from_ctx(ctx, toml=toml_path.name),
            success=True,
            artifacts=artifacts,
            warnings=val_result.warnings,
        )
        if json_mode:
            emit_json(envelope)
        else:
            emit_human(envelope, console)
