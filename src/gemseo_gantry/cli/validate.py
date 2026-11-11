from __future__ import annotations

import io
import sys
import threading
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console

from ._common import (
    ResolveError,
    invocation_from_ctx,
    make_spinner,
    resolve_toml,
    run_validate,
)
from ._render import emit_human, emit_json
from ._result import CliResult, Diagnostic, Invocation, ValidateResult

console = Console()


def _validate_envelope(result: ValidateResult, invocation: Invocation) -> CliResult:
    return CliResult(
        invocation=invocation,
        success=result.valid,
        warnings=result.warnings,
        errors=result.errors,
    )


def _is_quit_key(key: str) -> bool:
    """Whether a keypress is q, Q, or Esc."""
    import readchar

    return key in ("q", "Q", readchar.key.ESC)


def _start_quit_key_listener(stop_event: threading.Event) -> threading.Thread | None:
    """Start a background thread that sets `stop_event` on q/Q/Esc.

    Reads raw keypresses from the controlling terminal, which works over a
    plain SSH session (unlike X11-based listeners). Returns None if stdin
    isn't a terminal (e.g. input is redirected) - Ctrl+C remains the fallback
    in that case.

    Terminal raw-mode setup uses the stdlib's `tty.setcbreak`, not
    `readchar`'s read functions: readchar's POSIX backend clears
    `ICANON|ECHO|IGNBRK|BRKINT` against `c_lflag`, but `IGNBRK`/`BRKINT` are
    `c_iflag` constants that happen to numerically collide with `ISIG`/
    `ICANON` in `c_lflag` - so every readchar call also disables `ISIG`,
    silently breaking Ctrl+C. Calling it in a tight loop (as a listener must)
    means the terminal spends virtually all its time with Ctrl+C disabled.
    `tty.setcbreak` applies the same flags to the correct fields and is only
    invoked once per thread lifetime, so Ctrl+C keeps working throughout.
    """
    if not sys.stdin.isatty():
        return None

    def _watch_for_quit_key() -> None:
        if sys.platform == "win32":  # pragma: no cover
            import msvcrt
            import time

            try:
                while not stop_event.is_set():
                    if msvcrt.kbhit() and _is_quit_key(msvcrt.getwch()):
                        stop_event.set()
                        return
                    time.sleep(0.05)
            except Exception:
                return
        else:
            import os
            import termios
            import tty

            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setcbreak(fd)
                while not stop_event.is_set():
                    if _is_quit_key(os.read(fd, 1).decode(errors="ignore")):
                        stop_event.set()
                        return
            except Exception:
                return
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    thread = threading.Thread(target=_watch_for_quit_key, daemon=True)
    thread.start()
    return thread


def _run(
    path: Path,
    watch: bool,
    console: Console,
    invocation: Invocation,
    *,
    json_mode: bool = False,
) -> int:
    result = run_validate(path)
    envelope = _validate_envelope(result, invocation)
    if json_mode:
        emit_json(envelope)
    else:
        emit_human(envelope, console)

    if not watch:
        return 0 if result.valid else 1

    import watchfiles

    def _only_this_file(_: watchfiles.Change, changed_path: str) -> bool:
        return changed_path == str(path)

    stop_event = threading.Event()
    _start_quit_key_listener(stop_event)

    spinner = make_spinner(console, f"Watching '{path.name}'", json_mode=json_mode)
    spinner.start()
    try:
        for _ in watchfiles.watch(
            path.parent, watch_filter=_only_this_file, stop_event=stop_event
        ):
            spinner.stop()
            if not json_mode:
                console.rule()
            result = run_validate(path)
            envelope = _validate_envelope(result, invocation)
            if json_mode:
                emit_json(envelope)
            else:
                emit_human(envelope, console)
            spinner.start()
    except KeyboardInterrupt:
        pass
    finally:
        stop_event.set()
        spinner.stop()

    return 0


def validate(
    ctx: typer.Context,
    toml: Annotated[
        Optional[Path],
        typer.Argument(
            help="Path to problem definition TOML file",
            show_default="auto-detect in cwd",
        ),
    ] = None,
    watch: Annotated[
        bool,
        typer.Option(
            "--watch", "-w", help="Re-validate on every file save (q/Esc to stop)"
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
    """Validate a problem definition TOML against the gemseo-gantry schema."""
    if json_mode and quiet:
        raise typer.BadParameter("--json and --quiet are mutually exclusive")

    try:
        path = resolve_toml(toml)
    except ResolveError as exc:
        diag = Diagnostic("usage", str(exc))
        envelope = CliResult(
            invocation=invocation_from_ctx(ctx),
            success=False,
            errors=[diag],
        )
        if json_mode:
            emit_json(envelope)
        else:
            emit_human(envelope, console)
        raise typer.Exit(code=1)

    invocation = invocation_from_ctx(ctx, toml=path.name)
    out_console = Console(file=io.StringIO()) if quiet else console
    rc = _run(
        path,
        watch=watch,
        console=out_console,
        invocation=invocation,
        json_mode=json_mode,
    )
    raise typer.Exit(code=rc)
