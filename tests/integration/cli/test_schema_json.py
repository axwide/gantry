from typer.testing import CliRunner

from gemseo_gantry.cli.main import app
from tests.integration.cli._envelope import assert_valid_envelope

runner = CliRunner()


def test_schema_json_success(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["schema", "-j"])
    assert result.exit_code == 0
    data = assert_valid_envelope(result.stdout)
    assert data["invocation"]["command"] == ["schema"]
    assert data["success"] is True
    assert data["artifacts"] == [
        {
            "path": "schema/problem.schema.json",
            "kind": "schema",
            "status": "written",
        }
    ]


def test_schema_json_exists_without_force(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["schema"])  # first write
    result = runner.invoke(app, ["schema", "-j"])  # second, no --force
    assert result.exit_code == 1
    data = assert_valid_envelope(result.stdout)
    assert data["success"] is False
    assert data["errors"][0]["type"] == "usage"


def test_schema_stdout_option_removed():
    result = runner.invoke(app, ["schema", "--stdout"])
    assert result.exit_code != 0  # unknown option
