from typer.testing import CliRunner

from gemseo_gantry.cli.init import _TEMPLATE
from gemseo_gantry.cli.main import app
from tests.integration.cli._envelope import assert_valid_envelope

runner = CliRunner()


def _write_template(tmp_path):
    toml = tmp_path / "problem.toml"
    toml.write_text(_TEMPLATE.read_text(encoding="utf-8"), encoding="utf-8")
    return toml


def test_build_json_success(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_template(tmp_path)
    result = runner.invoke(app, ["build", "problem.toml", "-j"])
    assert result.exit_code == 0
    data = assert_valid_envelope(result.stdout)
    assert data["invocation"]["command"] == ["build"]
    assert data["success"] is True
    assert data["invocation"]["params"]["toml"] == "problem.toml"
    kinds = {a["kind"] for a in data["artifacts"]}
    assert {
        "discipline_base",
        "discipline_grammar",
        "discipline_io",
        "variables",
        "design_space",
        "package_init",
        "scenario",
        "schema",
    } <= kinds
    assert all(a["status"] == "written" for a in data["artifacts"])
    lib_arts = [a for a in data["artifacts"] if a["kind"] != "schema"]
    assert all(a["path"].startswith("lib/") for a in lib_arts)
    schema_arts = [a for a in data["artifacts"] if a["kind"] == "schema"]
    assert len(schema_arts) == 1
    assert "problem.schema.json" in schema_arts[0]["path"]


def test_build_json_bad_lib_name(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_template(tmp_path)
    result = runner.invoke(app, ["build", "problem.toml", "--lib-name", "1bad", "-j"])
    assert result.exit_code == 1
    data = assert_valid_envelope(result.stdout)
    assert data["success"] is False
    assert data["errors"][0]["type"] == "usage"
