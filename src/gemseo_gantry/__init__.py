from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gemseo_gantry.diagram import generate_n2, generate_xdsm
    from gemseo_gantry.generator import (
        ALL_ARTIFACTS,
        generate_lib,
        generate_scaffold,
    )
    from gemseo_gantry.model.data_model import ProblemDefinition
    from gemseo_gantry.validation import validate_toml

__all__ = [
    "ALL_ARTIFACTS",
    "ProblemDefinition",
    "validate_toml",
    "generate_lib",
    "generate_scaffold",
    "generate_n2",
    "generate_xdsm",
]

_lazy: dict[str, str] = {
    "ALL_ARTIFACTS": "gemseo_gantry.generator",
    "generate_n2": "gemseo_gantry.diagram",
    "generate_xdsm": "gemseo_gantry.diagram",
    "generate_lib": "gemseo_gantry.generator",
    "generate_scaffold": "gemseo_gantry.generator",
    "ProblemDefinition": "gemseo_gantry.model.data_model",
    "validate_toml": "gemseo_gantry.validation",
}


def __getattr__(name: str) -> object:
    if name not in _lazy:
        raise AttributeError(f"module 'gemseo_gantry' has no attribute {name!r}")
    import importlib

    mod = importlib.import_module(_lazy[name])
    obj = getattr(mod, name)
    globals()[name] = obj
    return obj
