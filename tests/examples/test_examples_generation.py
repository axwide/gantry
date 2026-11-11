import pytest
from typer.testing import CliRunner

from gemseo_gantry.examples.registry import available_names, get_example
from gemseo_gantry.generator import generate_lib
from gemseo_gantry.validation.pipeline import validate_toml

_runner = CliRunner()


def _app():
    from gemseo_gantry.cli.main import app

    return app


@pytest.mark.parametrize("name", available_names())
def test_example_validates_and_generates_lib(name, tmp_path):
    ex = get_example(name)
    problem = validate_toml(ex.root / f"{name}.toml").problem
    artifacts = generate_lib(problem, tmp_path, lib_name="lib")
    assert artifacts, "generate_lib produced no artifacts"
    assert (tmp_path / "lib").is_dir()


@pytest.mark.parametrize("name", available_names())
def test_example_explain_narrates_all_steps(name, tmp_path):
    result = _runner.invoke(_app(), ["example", name, str(tmp_path), "--explain"])
    assert result.exit_code == 0, result.output
    out = result.output.lower()
    for marker in [
        "problem definition",
        "build",
        "scaffold",
        "physics",
        "run",
        "post-process",
    ]:
        assert marker in out
