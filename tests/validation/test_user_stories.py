import json
import shutil
import subprocess
import sys
from pathlib import Path

from typer.testing import CliRunner

from tests.conftest import PYRIGHT_SUPPRESS_RULES

_cli_runner = CliRunner()
VLEO_TOML = Path(__file__).parent.parent / "fixtures" / "vleo.toml"


def _get_app():
    from gemseo_gantry.cli.main import app

    return app


def _clean_env() -> dict[str, str]:
    import os

    return {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}


def _write_pyrightconfig(directory: Path) -> None:
    (directory / "pyrightconfig.json").write_text(
        json.dumps({"extraPaths": ["."], **PYRIGHT_SUPPRESS_RULES}),
        encoding="utf-8",
    )


def test_greenfield_workflow(tmp_path):
    """Story 1: TOML -> validate -> build -> scaffold -> runnable execute -> load."""
    app = _get_app()

    # Copy VLEO fixture into tmp_path so all generated artifacts land there
    toml_path = tmp_path / "problem.toml"
    shutil.copy(VLEO_TOML, toml_path)

    # 1. validate
    result = _cli_runner.invoke(app, ["validate", str(toml_path)])
    assert result.exit_code == 0, f"validate failed:\n{result.output}"
    assert "valid" in result.output

    # 2. build -> lib/ in tmp_path
    result = _cli_runner.invoke(app, ["build", str(toml_path)])
    assert result.exit_code == 0, f"build failed:\n{result.output}"
    lib_dir = tmp_path / "lib"
    assert lib_dir.is_dir()
    assert (lib_dir / "variables.py").exists()
    assert (lib_dir / "design_space.csv").exists()

    # 3. scaffold --runnable -> disciplines/ + execute/load scripts in tmp_path
    result = _cli_runner.invoke(
        app,
        [
            "scaffold",
            str(toml_path),
            "--runnable",
            "--import-root",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0, f"scaffold failed:\n{result.output}"
    assert (tmp_path / "disciplines").is_dir()

    execute_script = next(tmp_path.glob("execute_*.py"), None)
    load_script = next(tmp_path.glob("load_*.py"), None)
    assert execute_script is not None, "No execute_*.py was generated"
    assert load_script is not None, "No load_*.py was generated"

    env = {**_clean_env(), "PYTHONPATH": str(tmp_path)}

    # 4. run execute script -> exit 0 + HDF5 produced
    proc = subprocess.run(
        [sys.executable, str(execute_script)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env=env,
    )
    assert proc.returncode == 0, (
        f"execute script failed:\nstdout: {proc.stdout}\nstderr: {proc.stderr}"
    )
    assert list(tmp_path.glob("*.h5")), "execute script did not produce an HDF5 file"

    # 5. run load script -> exit 0 + non-empty stdout
    proc = subprocess.run(
        [sys.executable, str(load_script)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env=env,
    )
    assert proc.returncode == 0, (
        f"load script failed:\nstdout: {proc.stdout}\nstderr: {proc.stderr}"
    )
    assert proc.stdout.strip(), "load script produced no output"


_SPLIT_V1_TOML = """\
[disciplines.aero]
inputs  = ["ballistic_coefficient"]
outputs = ["drag"]

[[variables]]
name             = "ballistic_coefficient"
unit             = "kg/m2"
data_type        = "float"
dimension        = 1
lower_bound      = 0.01
upper_bound      = 1.0
default_value    = 0.1

[[variables]]
name      = "drag"
unit      = "N"
data_type = "float"
dimension = 1
"""

_SPLIT_V2_TOML = """\
[disciplines.aero]
inputs  = ["mass", "Cd", "area"]
outputs = ["drag"]

[[variables]]
name             = "mass"
unit             = "kg"
data_type        = "float"
dimension        = 1
lower_bound      = 1.0
upper_bound      = 100.0
default_value    = 10.0

[[variables]]
name      = "Cd"
unit      = "-"
data_type = "float"
dimension = 1
default_value = 2.2

[[variables]]
name      = "area"
unit      = "m2"
data_type = "float"
dimension = 1
default_value = 0.1

[[variables]]
name      = "drag"
unit      = "N"
data_type = "float"
dimension = 1
"""


def test_type_checker_catches_split_variable(tmp_path):
    """Story 2: splitting a variable in TOML + regenerating lib surfaces a localized
    type error in the unchanged user file - only the removed attribute breaks."""
    app = _get_app()
    # Nested layout: tmp_path is the import root, project/ is the output dir.
    # This mirrors real usage where pyproject.toml sits above the generated package.
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    toml_path = project_dir / "problem.toml"

    # 1. Build lib from v1
    toml_path.write_text(_SPLIT_V1_TOML, encoding="utf-8")
    result = _cli_runner.invoke(app, ["build", str(toml_path)])
    assert result.exit_code == 0, f"build (v1) failed:\n{result.output}"

    # 2. Write user file that accesses ballistic_coefficient
    user_file = project_dir / "user_aero.py"
    user_file.write_text(
        "from project.lib.Aero_io import AeroInputs\n\n"
        "def compute(inputs: AeroInputs) -> None:\n"
        "    _ = inputs.ballistic_coefficient\n",
        encoding="utf-8",
    )
    # pyrightconfig lives at the import root; "." resolves there, no __init__.py clash
    _write_pyrightconfig(tmp_path)

    # 3. basedpyright on v1 lib -> clean (0 errors, no cascade noise)
    proc = subprocess.run(
        ["uv", "run", "basedpyright", "project/user_aero.py"],
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
    )
    assert proc.returncode == 0, (
        f"basedpyright unexpectedly failed on v1 lib:\n{proc.stdout}\n{proc.stderr}"
    )
    assert "0 errors" in proc.stdout, f"Expected 0 errors on v1 lib:\n{proc.stdout}"

    # 4. Capture user file fingerprint, then rebuild lib from v2 (split variable)
    user_content_before = user_file.read_bytes()
    toml_path.write_text(_SPLIT_V2_TOML, encoding="utf-8")
    result = _cli_runner.invoke(app, ["build", str(toml_path)])
    assert result.exit_code == 0, f"build (v2) failed:\n{result.output}"

    # Scaffold must not have been touched by build
    assert user_file.read_bytes() == user_content_before, (
        "build must not modify user files"
    )

    # 5. basedpyright on v2 lib -> exactly 1 error naming the removed variable
    proc = subprocess.run(
        ["uv", "run", "basedpyright", "project/user_aero.py"],
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
    )
    assert proc.returncode != 0, (
        "basedpyright should have flagged stale ballistic_coefficient reference"
    )
    assert "1 error" in proc.stdout, (
        f"Expected exactly 1 error on v2 lib:\n{proc.stdout}"
    )
    assert "ballistic_coefficient" in proc.stdout, (
        f"Expected 'ballistic_coefficient' in basedpyright output:\n{proc.stdout}"
    )


_RENAME_V2_TOML = """\
[disciplines.aero]
inputs  = ["BC"]
outputs = ["drag"]

[[variables]]
name             = "BC"
unit             = "kg/m2"
data_type        = "float"
dimension        = 1
lower_bound      = 0.01
upper_bound      = 1.0
default_value    = 0.1

[[variables]]
name      = "drag"
unit      = "N"
data_type = "float"
dimension = 1
"""


def test_type_checker_catches_renamed_variable(tmp_path):
    """Story 3: renaming a variable in TOML + regenerating lib surfaces a clear
    type error for the old Var enum member name in unchanged user code."""
    app = _get_app()
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    toml_path = project_dir / "problem.toml"

    # 1. Build lib from v1 (ballistic_coefficient exists in Var enum)
    toml_path.write_text(_SPLIT_V1_TOML, encoding="utf-8")
    result = _cli_runner.invoke(app, ["build", str(toml_path)])
    assert result.exit_code == 0, f"build (v1) failed:\n{result.output}"

    # 2. Write user file that uses Var.BALLISTIC_COEFFICIENT
    user_file = project_dir / "user_vars.py"
    user_file.write_text(
        "from project.lib.variables import Var\n\n"
        "def tag() -> str:\n"
        "    return Var.BALLISTIC_COEFFICIENT.value\n",
        encoding="utf-8",
    )
    _write_pyrightconfig(tmp_path)

    # 3. basedpyright on v1 lib -> clean (0 errors, no cascade noise)
    proc = subprocess.run(
        ["uv", "run", "basedpyright", "project/user_vars.py"],
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
    )
    assert proc.returncode == 0, (
        f"basedpyright unexpectedly failed on v1 lib:\n{proc.stdout}\n{proc.stderr}"
    )
    assert "0 errors" in proc.stdout, f"Expected 0 errors on v1 lib:\n{proc.stdout}"

    # 4. Rebuild lib from v2 (variable renamed to BC)
    user_content_before = user_file.read_bytes()
    toml_path.write_text(_RENAME_V2_TOML, encoding="utf-8")
    result = _cli_runner.invoke(app, ["build", str(toml_path)])
    assert result.exit_code == 0, f"build (v2) failed:\n{result.output}"

    assert user_file.read_bytes() == user_content_before, (
        "build must not modify user files"
    )

    # Positive check: Var.BC now exists in the regenerated variables.py
    variables_py = (project_dir / "lib" / "variables.py").read_text(encoding="utf-8")
    assert "BC" in variables_py, "Expected Var.BC to exist in regenerated variables.py"

    # 5. basedpyright on v2 lib -> exactly 1 error naming the old enum member
    proc = subprocess.run(
        ["uv", "run", "basedpyright", "project/user_vars.py"],
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
    )
    assert proc.returncode != 0, (
        "basedpyright should have flagged stale Var.BALLISTIC_COEFFICIENT reference"
    )
    assert "1 error" in proc.stdout, (
        f"Expected exactly 1 error on v2 lib:\n{proc.stdout}"
    )
    assert "BALLISTIC_COEFFICIENT" in proc.stdout, (
        f"Expected 'BALLISTIC_COEFFICIENT' in basedpyright output:\n{proc.stdout}"
    )


_BROKEN_TOML = """\
[disciplines.drag]
inputs  = ["altitude"]
outputs = ["force"]

[[variables]]
name      = "force"
unit      = "N"
data_type = "float"
dimension = 1
"""
# "altitude" is referenced as a discipline input but not defined in [[variables]].
# check_variable_refs catches this and names the variable in the error message.


def test_validate_clean_toml(tmp_path):
    """Story 4: validate exits 0 and reports the file as valid on a well-formed TOML."""
    app = _get_app()
    toml_path = tmp_path / "problem.toml"
    shutil.copy(VLEO_TOML, toml_path)

    result = _cli_runner.invoke(app, ["validate", str(toml_path)])

    assert result.exit_code == 0, f"validate unexpectedly failed:\n{result.output}"
    assert "valid" in result.output


def test_validate_broken_toml(tmp_path):
    """Story 4: validate exits non-zero and names the offending variable."""
    app = _get_app()
    toml_path = tmp_path / "problem.toml"
    toml_path.write_text(_BROKEN_TOML, encoding="utf-8")

    result = _cli_runner.invoke(app, ["validate", str(toml_path)])

    assert result.exit_code != 0, (
        f"validate should have failed for broken TOML:\n{result.output}"
    )
    assert "altitude" in result.output, (
        f"Expected 'altitude' in validate output:\n{result.output}"
    )
