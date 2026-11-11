import os
import re
import subprocess
import sys

import pytest
from typer.testing import CliRunner

from gemseo_gantry.examples.registry import available_names, get_example

_runner = CliRunner()


def _get_app():
    from gemseo_gantry.cli.main import app

    return app


def _clean_env(target) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    env["PYTHONPATH"] = str(target)
    return env


@pytest.mark.slow
@pytest.mark.parametrize("name", available_names())
def test_example_end_to_end(name, tmp_path):
    """generate -> execute -> post-process; assert the optimum objective.

    Uniform across every registered example. Primary drift guard: catches
    broken imports and non-convergence.
    """
    ex = get_example(name)

    result = _runner.invoke(_get_app(), ["example", name, str(tmp_path)])
    assert result.exit_code == 0, result.output

    target = tmp_path / name
    env = _clean_env(target)

    execute = subprocess.run(
        [sys.executable, ex.executor],
        cwd=target,
        capture_output=True,
        text=True,
        env=env,
    )
    assert execute.returncode == 0, (
        f"execute failed (exit {execute.returncode}):\n"
        f"stdout: {execute.stdout}\nstderr: {execute.stderr}"
    )

    post = subprocess.run(
        [sys.executable, "postprocess.py"],
        cwd=target,
        capture_output=True,
        text=True,
        env=env,
    )
    assert post.returncode == 0, (
        f"postprocess failed (exit {post.returncode}):\n"
        f"stdout: {post.stdout}\nstderr: {post.stderr}"
    )

    match = re.search(r"OPTIMUM_OBJECTIVE:\s*(-?[0-9]+\.[0-9]+)", post.stdout)
    assert match, f"no OPTIMUM_OBJECTIVE in post-processing output:\n{post.stdout}"
    objective = float(match.group(1))
    assert objective == pytest.approx(
        ex.expected_objective, abs=ex.objective_tolerance
    ), f"{name}: objective {objective} not near expected {ex.expected_objective}"


@pytest.mark.slow
def test_example_sellar_explain_runs_full_pipeline(tmp_path):
    """--explain in a non-TTY auto-advances and runs the whole pipeline."""
    result = _runner.invoke(
        _get_app(), ["example", "sellar", str(tmp_path), "--explain"]
    )
    assert result.exit_code == 0, result.output
    target = tmp_path / "sellar"
    assert (target / "Sellar.h5").is_file()
    assert (target / "diagrams").is_dir()
    assert re.search(r"OPTIMUM_OBJECTIVE:\s*([0-9]+\.[0-9]+)", result.output)
    # finished files, no scaffold stubs left behind
    assert not list(target.rglob("*_scaffold.py"))
    assert (target / "disciplines" / "Sellar1.py").is_file()
