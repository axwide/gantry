"""Tests that CLI modules do not eagerly import heavy dependencies at startup."""

import subprocess
import sys


def _modules_after_import(module: str) -> set[str]:
    """Return sys.modules keys present after importing `module` in a clean subprocess."""
    code = f"import {module}; import sys; print('\\n'.join(sys.modules.keys()))"
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=True,
    )
    return set(result.stdout.splitlines())


def test_importing_scaffold_module_does_not_load_generator():
    modules = _modules_after_import("gemseo_gantry.cli.scaffold")
    assert "gemseo_gantry.generator" not in modules


def test_importing_build_module_does_not_load_generator():
    modules = _modules_after_import("gemseo_gantry.cli.build")
    assert "gemseo_gantry.generator" not in modules
