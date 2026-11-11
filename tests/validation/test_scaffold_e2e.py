import re
import subprocess
import sys

from typer.testing import CliRunner

_cli_runner = CliRunner()


def _get_app():
    from gemseo_gantry.cli.main import app

    return app


def _clean_env() -> dict[str, str]:
    import os

    return {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}


def test_scaffold_e2e_workflow(tmp_path):
    """Full pipeline: init -> build -> scaffold --runnable -> execute -> load.

    Verifies that the template TOML produced by `init` can be built, scaffolded
    with runnable stubs, executed as an optimization, and the resulting HDF5 file
    loaded - all without manual edits to generated code. Also verifies that the
    template's observable (the coupling variable ``z``, which is neither an
    objective, constraint, nor design variable) is recorded during the run and
    surfaces in the loaded post-processing dataset.
    """
    app = _get_app()
    toml_path = tmp_path / "problem.toml"

    result = _cli_runner.invoke(app, ["init", str(toml_path)])
    assert result.exit_code == 0, f"init failed:\n{result.output}"
    assert toml_path.exists()

    result = _cli_runner.invoke(app, ["build", str(toml_path)])
    assert result.exit_code == 0, f"build failed:\n{result.output}"
    assert (tmp_path / "lib").is_dir()

    result = _cli_runner.invoke(
        app,
        ["scaffold", str(toml_path), "--runnable", "--import-root", str(tmp_path)],
    )
    assert result.exit_code == 0, f"scaffold failed:\n{result.output}"
    assert (tmp_path / "disciplines").is_dir()

    execute_script = next(tmp_path.glob("execute_*.py"), None)
    load_script = next(tmp_path.glob("load_*.py"), None)
    assert execute_script is not None, "No execute_*.py was generated"
    assert load_script is not None, "No load_*.py was generated"

    env = {**_clean_env(), "PYTHONPATH": str(tmp_path)}

    proc = subprocess.run(
        [sys.executable, str(execute_script)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env=env,
    )
    assert proc.returncode == 0, (
        f"execute script failed (exit {proc.returncode}):\n"
        f"stdout: {proc.stdout}\nstderr: {proc.stderr}"
    )
    assert list(tmp_path.glob("*.h5")), "execute script did not produce an HDF5 file"

    proc = subprocess.run(
        [sys.executable, str(load_script)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env=env,
    )
    assert proc.returncode == 0, (
        f"load script failed (exit {proc.returncode}):\n"
        f"stdout: {proc.stdout}\nstderr: {proc.stderr}"
    )
    assert proc.stdout.strip(), "load script produced no output"

    # The observable ``z`` must appear in the post-processing dataset. Matched as
    # a whole word so the "z" inside log noise (e.g. "optimization") can't pass it.
    assert re.search(r"\bz\b", proc.stdout), (
        f"observable 'z' not found in post-processing output:\n{proc.stdout}"
    )
