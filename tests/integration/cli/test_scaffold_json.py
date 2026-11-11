from typer.testing import CliRunner

from gemseo_gantry.cli.init import _TEMPLATE
from gemseo_gantry.cli.main import app
from tests.integration.cli._envelope import assert_valid_envelope

runner = CliRunner()


def _setup(tmp_path):
    toml = tmp_path / "problem.toml"
    toml.write_text(_TEMPLATE.read_text(encoding="utf-8"), encoding="utf-8")
    return toml


def test_scaffold_json_success(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    toml_path = _setup(tmp_path)
    runner.invoke(app, ["build", "problem.toml"])  # scaffold needs lib/
    result = runner.invoke(app, ["scaffold", "problem.toml", "-j"])
    assert result.exit_code == 0
    data = assert_valid_envelope(result.stdout)
    assert data["invocation"]["command"] == ["scaffold"]
    kinds = {a["kind"] for a in data["artifacts"]}
    assert "discipline_scaffold" in kinds
    assert "executor" in kinds
    assert "postprocessor" in kinds
    # executor and loader for the same scenario are distinct paths, not duplicates
    paths = [a["path"] for a in data["artifacts"]]
    assert len(paths) == len(set(paths))
    assert all(a["status"] in ("written", "skipped") for a in data["artifacts"])
    assert data["invocation"]["params"]["toml"] == toml_path.name


def test_scaffold_json_skipped_on_second_run(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup(tmp_path)
    runner.invoke(app, ["build", "problem.toml"])
    runner.invoke(app, ["scaffold", "problem.toml"])  # first write
    result = runner.invoke(app, ["scaffold", "problem.toml", "-j"])  # all skipped
    assert result.exit_code == 0
    data = assert_valid_envelope(result.stdout)
    assert any(a["status"] == "skipped" for a in data["artifacts"])


def test_scaffold_json_without_build_is_usage_error(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup(tmp_path)
    result = runner.invoke(app, ["scaffold", "problem.toml", "-j"])
    assert result.exit_code == 1
    data = assert_valid_envelope(result.stdout)
    assert data["success"] is False
    assert [e["type"] for e in data["errors"]] == ["usage"]
    assert "--lib-dir" in data["errors"][0]["message"]
