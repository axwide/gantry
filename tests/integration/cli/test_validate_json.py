from typer.testing import CliRunner

from gemseo_gantry.cli.main import app
from tests.integration.cli._envelope import assert_valid_envelope

runner = CliRunner()


def test_validate_json_success(tmp_path):
    toml = tmp_path / "problem.toml"
    from gemseo_gantry.cli.init import _TEMPLATE

    toml.write_text(_TEMPLATE.read_text(encoding="utf-8"), encoding="utf-8")
    result = runner.invoke(app, ["validate", str(toml), "-j"])
    assert result.exit_code == 0
    data = assert_valid_envelope(result.stdout)
    assert data["invocation"]["params"]["toml"] == "problem.toml"
    assert data == {
        "invocation": {
            "command": ["validate"],
            "params": {
                "toml": "problem.toml",
                "watch": False,
                "quiet": False,
                "json": True,
            },
        },
        "success": True,
        "artifacts": [],
        "warnings": [],
        "errors": [],
    }


def test_validate_json_missing_file(tmp_path):
    result = runner.invoke(app, ["validate", str(tmp_path / "nope.toml"), "-j"])
    assert result.exit_code == 1
    data = assert_valid_envelope(result.stdout)
    assert data["success"] is False
    assert data["errors"][0]["type"] == "file_not_found"


def test_validate_json_resolve_error(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # empty dir -> resolve error
    result = runner.invoke(app, ["validate", "-j"])
    assert result.exit_code == 1
    data = assert_valid_envelope(result.stdout)
    assert data["invocation"]["command"] == ["validate"]
    assert data["success"] is False
    assert data["errors"][0]["type"] == "usage"
