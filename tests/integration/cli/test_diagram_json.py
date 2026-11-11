from typer.testing import CliRunner

from gemseo_gantry.cli.init import _TEMPLATE
from gemseo_gantry.cli.main import app
from tests.integration.cli._envelope import assert_valid_envelope

runner = CliRunner()


def _setup(tmp_path):
    (tmp_path / "problem.toml").write_text(
        _TEMPLATE.read_text(encoding="utf-8"), encoding="utf-8"
    )


def test_diagram_n2_json(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup(tmp_path)
    result = runner.invoke(app, ["diagram", "n2", "problem.toml", "-j"])
    assert result.exit_code == 0
    data = assert_valid_envelope(result.stdout)
    assert data["invocation"]["command"] == ["diagram", "n2"]
    assert {a["kind"] for a in data["artifacts"]} == {"diagram"}
    assert all(a["status"] == "written" for a in data["artifacts"])


def test_diagram_xdsm_json(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup(tmp_path)
    result = runner.invoke(app, ["diagram", "xdsm", "problem.toml", "-j"])
    assert result.exit_code == 0
    data = assert_valid_envelope(result.stdout)
    assert data["invocation"]["command"] == ["diagram", "xdsm"]
    assert data["artifacts"][0]["kind"] == "diagram"
