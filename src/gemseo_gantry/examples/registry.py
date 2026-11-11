"""Registry of shipped, runnable example projects.

Each example is a package under ``examples/<name>/`` with a TOML, owned
``disciplines/`` (subclasses of the generated ``*Base``), a shipped executor,
``postprocess.py``, and a ``meta.py`` registering an :class:`Example`.

An example's disciplines come in one of two kinds, both tested identically by
the parametrized two-tier example test suite:

* **Hand-written** - the discipline ``_run`` implements the physics directly
  (e.g. ``sellar``).
* **Library-delegated** - the discipline ``_run`` forwards to a reference
  implementation shipped by a library such as GEMSEO (e.g. ``sobieski``).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Example:
    """Metadata for a shipped, runnable example project."""

    name: str
    summary: str
    root: (
        Path  # package dir holding problem.toml, disciplines/, executor, postprocess.py
    )
    intro: str
    outro: str
    expected_objective: float
    executor: str  # shipped executor filename, e.g. "execute_Sellar.py"
    objective_tolerance: float  # abs tolerance for the end-to-end objective check
    physics_note: str  # narration step 4 (fill-in-the-physics) example-specific note
    run_note: str  # narration step 5 (run) example-specific note


class UnknownExampleError(Exception):
    def __init__(self, name: str, available: list[str]) -> None:
        self.name = name
        self.available = available
        super().__init__(
            f"Unknown example {name!r}. Available: {', '.join(available)}."
        )


# Name -> Example lookup, populated lazily on first access. Each example's
# `meta.py` defines an `Example` (name, summary, expected objective, executor
# filename, narration text); `_load` imports those modules once and indexes
# them by name so the CLI can list and fetch examples by name.
_REGISTRY: dict[str, Example] = {}


def _load() -> dict[str, Example]:
    if not _REGISTRY:
        from .sellar.meta import EXAMPLE as SELLAR
        from .sobieski.meta import EXAMPLE as SOBIESKI

        for ex in (SELLAR, SOBIESKI):
            _REGISTRY[ex.name] = ex
    return _REGISTRY


def available_names() -> list[str]:
    return sorted(_load())


def get_example(name: str) -> Example:
    registry = _load()
    if name not in registry:
        raise UnknownExampleError(name, sorted(registry))
    return registry[name]
