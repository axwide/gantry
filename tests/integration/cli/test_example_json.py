from typer.testing import CliRunner

from gemseo_gantry.cli.main import app
from tests.integration.cli._envelope import assert_valid_envelope

runner = CliRunner()


def test_example_json_success(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["example", "sellar", "-j"])
    assert result.exit_code == 0
    data = assert_valid_envelope(result.stdout)
    assert data["invocation"]["command"] == ["example"]
    assert data["success"] is True
    kinds = {a["kind"] for a in data["artifacts"]}
    assert "problem_definition" in kinds
    assert any("sellar.toml" in a["path"] for a in data["artifacts"])
    assert all(a["status"] == "written" for a in data["artifacts"])


def test_example_json_exists_without_force(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    existing = tmp_path / "sellar"
    existing.mkdir()
    (existing / "keep.txt").write_text("x", encoding="utf-8")
    result = runner.invoke(app, ["example", "sellar", "-j"])
    assert result.exit_code == 1
    data = assert_valid_envelope(result.stdout)
    assert data["success"] is False
    assert data["errors"][0]["type"] == "usage"


def test_example_json_unknown_name(tmp_path, monkeypatch):
    # Typer validates the StrEnum argument before our function runs, so the
    # error is a plain-text Typer panel (exit 2), not a JSON envelope.
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["example", "nope", "-j"])
    assert result.exit_code == 2
    assert "sellar" in result.output
