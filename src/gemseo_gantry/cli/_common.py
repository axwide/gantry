from __future__ import annotations

from enum import Enum
from pathlib import Path
from tomllib import TOMLDecodeError

import typer
from rich.console import Console
from rich.status import Status

from ..validation import SemanticValidationError, validate_toml
from ._result import Diagnostic, Invocation, ValidateResult


def _jsonable(value: object) -> object:
    """Coerce a click parameter value into a JSON-serializable primitive."""
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


def invocation_from_ctx(ctx: typer.Context, **overrides: object) -> Invocation:
    """Build an :class:`Invocation` echoing the command line behind ``ctx``.

    ``command`` is the command chain minus the program name, so sub- and
    sub-sub-commands appear in order. ``params`` maps each argument/option to
    its invoked value, keyed by CLI name (``--lib-name`` -> ``lib-name``)
    rather than the internal Python identifier, with values normalized to JSON
    primitives. ``overrides`` replaces values after the fact - used to record a
    resolved path in place of the raw (possibly auto-detected) input.

    Args:
        ctx: The click/typer context of the invoked (sub)command.
        **overrides: CLI-named params to override, e.g. ``toml=resolved.name``.

    Returns:
        The invocation echoing ``ctx``.
    """
    cli_name = {p.name: max(p.opts, key=len).lstrip("-") for p in ctx.command.params}
    params: dict[str, object] = {
        cli_name.get(name, name): _jsonable(value) for name, value in ctx.params.items()
    }
    params.update(overrides)
    return Invocation(command=ctx.command_path.split()[1:], params=params)


class ResolveError(Exception):
    pass


def resolve_toml(path: Path | None) -> Path:
    """Return path if given; otherwise auto-detect a single *.toml in cwd."""
    if path is not None:
        if path.suffix != ".toml":
            raise ResolveError(f"Expected a .toml file, got: {path.name}")
        return path
    candidates = sorted(Path.cwd().glob("*.toml"))
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise ResolveError(
            "No .toml file found in the current directory. Specify one explicitly."
        )
    names = ", ".join(c.name for c in candidates)
    raise ResolveError(f"Multiple .toml files found: {names}. Specify one explicitly.")


def run_validate(path: Path) -> ValidateResult:
    """Run TOML validation and return a structured result. Pure - no I/O."""
    file = path.name
    try:
        result = validate_toml(path)
        warnings = [Diagnostic("validation", w) for w in result.warnings]
        return ValidateResult(
            valid=True, file=file, problem=result.problem, warnings=warnings
        )
    except FileNotFoundError:
        return ValidateResult(
            valid=False,
            file=file,
            errors=[Diagnostic("file_not_found", f"File not found: {path}")],
        )
    except TOMLDecodeError as exc:
        return ValidateResult(
            valid=False,
            file=file,
            errors=[Diagnostic("syntax", str(exc))],
        )
    except SemanticValidationError as exc:
        return ValidateResult(
            valid=False,
            file=file,
            errors=[Diagnostic("semantic", str(exc))],
            warnings=[Diagnostic("validation", w) for w in exc.warnings],
        )
    except ValueError as exc:
        return ValidateResult(
            valid=False,
            file=file,
            errors=[Diagnostic("structural", str(exc))],
        )


class _NoOpSpinner:
    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def update(self, *_: object, **_kwargs: object) -> None:
        pass

    def __enter__(self) -> _NoOpSpinner:
        return self

    def __exit__(self, *_: object) -> None:
        pass


def make_spinner(
    console: Console,
    message: str,
    *,
    quiet: bool = False,
    json_mode: bool = False,
) -> Status | _NoOpSpinner:
    if quiet or json_mode:
        return _NoOpSpinner()
    return console.status(message)
