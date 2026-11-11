from typer.testing import CliRunner

from gemseo_gantry.cli.main import app
from tests.integration.cli._envelope import assert_valid_envelope

runner = CliRunner()


def test_init_json_success(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["init", "-j"])
    assert result.exit_code == 0
    data = assert_valid_envelope(result.stdout)
    assert data["invocation"]["command"] == ["init"]
    assert data["success"] is True
    kinds = {a["kind"] for a in data["artifacts"]}
    assert kinds == {"problem_definition", "schema"}
    assert all(a["status"] == "written" for a in data["artifacts"])
    assert any(a["path"] == "problem.toml" for a in data["artifacts"])
    assert any("problem.schema.json" in a["path"] for a in data["artifacts"])


def test_init_json_exists_without_force(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "problem.toml").write_text("x", encoding="utf-8")
    result = runner.invoke(app, ["init", "-j"])
    assert result.exit_code == 1
    data = assert_valid_envelope(result.stdout)
    assert data["success"] is False
    assert data["errors"][0]["type"] == "usage"
