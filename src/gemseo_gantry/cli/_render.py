from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING

from rich.console import Console
from rich.markup import escape
from rich.panel import Panel

from ._common import ResolveError
from ._result import (
    ArtifactKind,
    ArtifactStatus,
    CliResult,
    Command,
    Diagnostic,
)

if TYPE_CHECKING:
    from ..examples.narration import NarrationStep


def emit_json(result: CliResult) -> None:
    """Print the unified CLI envelope as single-line JSON to stdout."""
    print(result.model_dump_json(exclude_none=True))


def emit_human(result: CliResult, console: Console) -> None:
    """Render the unified CLI envelope as Rich output to the console.

    Mirrors emit_json: a single entry point that branches on the top-level
    command (``invocation.command[0]``), so subcommands of a group share a renderer.
    """
    command = result.invocation.command[0]
    if command == Command.VALIDATE:
        _human_validate(result, console)
    elif command == Command.BUILD:
        _human_build(result, console)
    elif command == Command.SCAFFOLD:
        _human_scaffold(result, console)
    elif command == Command.DIAGRAM:
        _human_diagram(result, console)
    elif command == Command.INIT:
        _human_init(result, console)
    elif command == Command.SCHEMA:
        _human_schema(result, console)
    elif command == Command.EXAMPLE:
        _human_example(result, console)
    else:  # pragma: no cover - unknown commands never reach here
        raise ValueError(f"emit_human does not handle {command}")


def _render_error_panels(errors: list[Diagnostic], console: Console) -> None:
    """Render each diagnostic as a red error panel (shared failure rendering)."""
    for error in errors:
        console.print(Panel(f"[red]Error:[/red] {escape(error.message)}", style="red"))


def _file_lines(paths: Iterable[object]) -> str:
    """Vertical bulleted file listing shared by every success panel."""
    return "\n".join(f"  • {p}" for p in paths)


def _human_validate(result: CliResult, console: Console) -> None:
    render_warnings(result.warnings, console)
    panel_titles = {
        "syntax": "Syntax error",
        "structural": "Structural error",
        "semantic": "Semantic error",
    }
    file = str(result.invocation.params.get("toml") or "")
    if result.success:
        console.print(f"[green]✓[/green] {file} is valid")
        return
    for error in result.errors:
        if error.type == "file_not_found":
            console.print(f"[red]✗[/red] File not found: {escape(file)}")
        else:
            error_text = "\n".join(
                f"• {escape(line)}" for line in error.message.splitlines()
            )
            console.print(
                Panel(
                    error_text,
                    title=panel_titles.get(error.type, "Validation error"),
                    border_style="red",
                )
            )
    if result.errors and result.errors[0].type not in ("file_not_found", "usage"):
        console.print(f"[red]✗[/red] {file} is invalid")


def _human_build(result: CliResult, console: Console) -> None:
    if not result.success:
        _render_error_panels(result.errors, console)
        return
    lib_artifacts = [a for a in result.artifacts if a.kind is not ArtifactKind.SCHEMA]
    lib_path = Path(lib_artifacts[0].path).parent if lib_artifacts else Path("")
    file_list = _file_lines(Path(a.path).name for a in lib_artifacts)
    source = result.invocation.params.get("toml")
    source_line = f"\n[green]From:[/green] {source}" if source else ""
    console.print(
        Panel(
            f"[green]Created {lib_path.name}/ in[/green] {lib_path.parent}"
            f"{source_line}\n\n"
            f"[green]Files created:[/green]\n{file_list}",
            title="gantry build",
            style="green",
        )
    )


def _human_scaffold(result: CliResult, console: Console) -> None:
    if result.errors:
        _render_error_panels(result.errors, console)
        return
    written = [a.path for a in result.artifacts if a.status is ArtifactStatus.WRITTEN]
    skipped = [a.path for a in result.artifacts if a.status is ArtifactStatus.SKIPPED]
    lines: list[str] = []
    if written:
        lines.append(f"[green]Files written:[/green]\n{_file_lines(written)}")
    if skipped:
        lines.append(
            f"[yellow]Files skipped:[/yellow]\n[yellow]{_file_lines(skipped)}[/yellow]"
        )
    console.print(
        Panel(
            "\n".join(lines) if lines else "Nothing to do.",
            title="gantry scaffold",
            style="green",
        )
    )


def _human_diagram(result: CliResult, console: Console) -> None:
    render_warnings(result.warnings, console)
    if not result.success:
        _render_error_panels(result.errors, console)
        return
    file_list = _file_lines(a.path for a in result.artifacts)
    console.print(
        Panel(
            f"[green]Files created:[/green]\n{file_list}",
            title="gantry diagram",
            style="green",
        )
    )


def _human_init(result: CliResult, console: Console) -> None:
    if not result.success:
        _render_error_panels(result.errors, console)
        return
    defn = next(
        a for a in result.artifacts if a.kind is ArtifactKind.PROBLEM_DEFINITION
    )
    created = _file_lines(a.path for a in result.artifacts)
    console.print(
        Panel(
            f"[green]Files created:[/green]\n{created}\n\n"
            f"Next step: [bold]gantry build {defn.path}[/bold]",
            title="gantry init",
            style="green",
        )
    )


def _human_schema(result: CliResult, console: Console) -> None:
    if not result.success:
        _render_error_panels(result.errors, console)
        return
    artifact = next(a for a in result.artifacts if a.kind is ArtifactKind.SCHEMA)
    console.print(
        Panel(
            f"[green]Files created:[/green]\n{_file_lines([artifact.path])}",
            title="gantry schema",
            style="green",
        )
    )


def render_resolve_error(exc: ResolveError, console: Console) -> None:
    """Render a resolve_toml failure for human output."""
    console.print(Panel(f"[red]Error:[/red] {escape(str(exc))}", style="red"))


def _human_example(result: CliResult, console: Console) -> None:
    if not result.success:
        _render_error_panels(result.errors, console)
        return
    toml_art = next(a for a in result.artifacts if a.path.endswith(".toml"))
    project_dir = Path(toml_art.path).parent
    name = Path(toml_art.path).stem
    executor_art = next(
        (a for a in result.artifacts if a.kind is ArtifactKind.EXECUTOR), None
    )
    executor = (
        Path(executor_art.path).name
        if executor_art
        else f"execute_{name.capitalize()}.py"
    )
    files = _file_lines(
        str(Path(a.path).relative_to(project_dir)) for a in result.artifacts
    )
    console.print(
        Panel(
            f"[green]Created[/green] '{name}' example in "
            f"[bold]{project_dir}[/bold]\n\n{files}\n\n"
            f"[dim]Next:[/dim] uv run {project_dir.as_posix()}/{executor}",
            title="gantry example",
            style="green",
        )
    )


def render_warnings(warnings: list[Diagnostic], console: Console) -> None:
    if not warnings:
        return
    warning_text = "\n".join(f"• {escape(w.message)}" for w in warnings)
    console.print(Panel(warning_text, title="Warnings", border_style="yellow"))


def _narration_panel(step: NarrationStep) -> Panel:
    body = step.body
    if step.command:
        body += f"\n\n[cyan]$ {step.command}[/cyan]"
    if step.artifacts:
        body += f"\n\nFiles:\n{_file_lines(step.artifacts)}"
    return Panel(body, title=f"[bold cyan]{step.title}[/bold cyan]")


def live_header(command: str, console: Console) -> None:
    """Print a header rule introducing live subprocess output."""
    console.rule(f"[cyan]$ {command}[/cyan]")


def render_file_snippet(
    path: Path,
    lexer: str,
    console: Console,
    lines: int = 15,
    *,
    title: str | None = None,
) -> None:
    """Show the first ``lines`` lines of a file, syntax-highlighted.

    When *title* is supplied a pair of rules bracket the output so the reader
    can clearly see where the snippet starts and ends.
    """
    from rich.syntax import Syntax

    text = path.read_text(encoding="utf-8")
    head = "\n".join(text.splitlines()[:lines])
    syntax = Syntax(head, lexer, theme="ansi_dark", line_numbers=False)
    if title is not None:
        console.print(Panel(syntax, title=f"[dim]{title}[/dim]"))
    else:
        console.print(syntax)
