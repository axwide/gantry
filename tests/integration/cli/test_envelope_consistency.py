import pytest
from typer.testing import CliRunner

from gemseo_gantry.cli.init import _TEMPLATE
from gemseo_gantry.cli.main import app
from tests.integration.cli._envelope import assert_valid_envelope

runner = CliRunner()


def _project(tmp_path):
    (tmp_path / "problem.toml").write_text(
        _TEMPLATE.read_text(encoding="utf-8"), encoding="utf-8"
    )


SUCCESS_INVOCATIONS = [
    ["init", "--force"],
    ["validate", "problem.toml"],
    ["build", "problem.toml"],
    ["scaffold", "problem.toml"],
    ["diagram", "n2", "problem.toml"],
    ["diagram", "xdsm", "problem.toml"],
    ["schema", "--force"],
    ["example", "sellar"],
]


@pytest.mark.parametrize("argv", SUCCESS_INVOCATIONS, ids=lambda a: " ".join(a))
def test_every_command_emits_valid_envelope(argv, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _project(tmp_path)
    if argv[0] in {"scaffold"}:
        runner.invoke(app, ["build", "problem.toml"])
    result = runner.invoke(app, [*argv, "-j"])
    assert result.exit_code == 0, result.stdout
    data = assert_valid_envelope(result.stdout)
    assert set(data) == {"invocation", "success", "artifacts", "warnings", "errors"}
    assert data["invocation"]["command"][0] == argv[0]
    assert data["success"] is True


def test_resolve_error_envelope_matches_normal_shape(tmp_path, monkeypatch):
    # empty dir -> every file-taking command resolve-errors with the same shape
    monkeypatch.chdir(tmp_path)
    for cmd in (["validate"], ["build"], ["scaffold"], ["diagram", "n2"]):
        result = runner.invoke(app, [*cmd, "-j"])
        data = assert_valid_envelope(result.stdout)
        assert set(data) == {"invocation", "success", "artifacts", "warnings", "errors"}
        assert data["invocation"]["command"] == cmd
        assert data["success"] is False
