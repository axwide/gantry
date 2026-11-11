import json
import shutil
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

runner = CliRunner()

FIXTURES_TOML = Path(__file__).parent.parent.parent / "fixtures" / "vleo.toml"


def get_app():
    from gemseo_gantry.cli.main import app

    return app


def test_build_generates_lib_next_to_toml(tmp_path):
    toml_path = tmp_path / "vleo.toml"
    shutil.copy(FIXTURES_TOML, toml_path)

    result = runner.invoke(get_app(), ["build", str(toml_path)])

    assert result.exit_code == 0
    assert (tmp_path / "lib").is_dir()
    assert (tmp_path / "lib" / "variables.py").exists()
    assert (tmp_path / "lib" / "design_space.csv").exists()


def test_build_custom_out(tmp_path):
    toml_path = tmp_path / "vleo.toml"
    shutil.copy(FIXTURES_TOML, toml_path)
    out_dir = tmp_path / "custom_out"

    result = runner.invoke(get_app(), ["build", str(toml_path), "--out", str(out_dir)])

    assert result.exit_code == 0
    assert (out_dir / "lib").is_dir()


def test_build_is_idempotent(tmp_path):
    toml_path = tmp_path / "vleo.toml"
    shutil.copy(FIXTURES_TOML, toml_path)

    runner.invoke(get_app(), ["build", str(toml_path)])
    result = runner.invoke(get_app(), ["build", str(toml_path)])

    assert result.exit_code == 0
    assert (tmp_path / "lib").is_dir()


def test_build_output_message(tmp_path):
    toml_path = tmp_path / "vleo.toml"
    shutil.copy(FIXTURES_TOML, toml_path)

    result = runner.invoke(get_app(), ["build", str(toml_path)])

    assert result.exit_code == 0
    # Should show the parent dir, not the created dir itself
    assert str(tmp_path) in result.output
    assert "lib/ in" in result.output
    assert str(tmp_path / "lib") not in result.output
    # Should show the TOML filename
    assert "vleo.toml" in result.output


def test_build_rejects_non_identifier_lib_name(tmp_path):
    toml_path = tmp_path / "vleo.toml"
    shutil.copy(FIXTURES_TOML, toml_path)

    result = runner.invoke(
        get_app(),
        ["build", str(toml_path), "--lib-name", "my-lib"],
    )

    assert result.exit_code != 0
    assert "my_lib" in result.output  # suggestion shown


def test_build_fails_on_invalid_toml(tmp_path):
    bad_toml = tmp_path / "bad.toml"
    bad_toml.write_text("not valid toml [[[", encoding="utf-8")

    result = runner.invoke(get_app(), ["build", str(bad_toml)])

    assert result.exit_code != 0


def test_build_fails_on_missing_disciplines(tmp_path):
    empty_toml = tmp_path / "empty.toml"
    empty_toml.write_text("[metadata]\nname = 'empty'\n", encoding="utf-8")

    result = runner.invoke(get_app(), ["build", str(empty_toml)])

    assert result.exit_code != 0


def test_build_custom_lib_name(tmp_path):
    toml_path = tmp_path / "vleo.toml"
    shutil.copy(FIXTURES_TOML, toml_path)

    result = runner.invoke(get_app(), ["build", str(toml_path), "--lib-name", "my_lib"])

    assert result.exit_code == 0
    assert (tmp_path / "my_lib").is_dir()
    assert (tmp_path / "my_lib" / "variables.py").exists()


def test_build_quiet_suppresses_output(tmp_path):
    toml_path = tmp_path / "vleo.toml"
    shutil.copy(FIXTURES_TOML, toml_path)

    result = runner.invoke(get_app(), ["build", str(toml_path), "--quiet"])

    assert result.exit_code == 0
    assert result.output.strip() == ""


def test_build_json_success(tmp_path):
    toml_path = tmp_path / "vleo.toml"
    shutil.copy(FIXTURES_TOML, toml_path)
    result = runner.invoke(get_app(), ["build", str(toml_path), "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["invocation"]["command"] == ["build"]
    assert data["success"] is True
    assert len(data["artifacts"]) > 0
    assert data.get("errors", []) == []


def test_build_json_invalid_toml(tmp_path):
    bad = tmp_path / "bad.toml"
    bad.write_text("not valid toml [[[", encoding="utf-8")
    result = runner.invoke(get_app(), ["build", str(bad), "--json"])
    assert result.exit_code != 0
    data = json.loads(result.output)
    assert data["success"] is False
    assert len(data["errors"]) > 0


def test_build_json_resolve_error(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(get_app(), ["build", "--json"])
    assert result.exit_code != 0
    data = json.loads(result.output)
    assert data["success"] is False
    assert data["errors"][0]["type"] == "usage"


def test_build_json_and_quiet_mutually_exclusive(tmp_path):
    toml_path = tmp_path / "vleo.toml"
    shutil.copy(FIXTURES_TOML, toml_path)
    result = runner.invoke(get_app(), ["build", str(toml_path), "--json", "--quiet"])
    assert result.exit_code != 0


def test_build_output_message_is_rich_specific(tmp_path):
    """Rich output contains 'lib/ in' - definitively not JSON."""
    toml_path = tmp_path / "vleo.toml"
    shutil.copy(FIXTURES_TOML, toml_path)
    result = runner.invoke(get_app(), ["build", str(toml_path)])
    assert result.exit_code == 0
    assert "lib/ in" in result.output
    assert "vleo.toml" in result.output


_WARNING_TOML = (
    '[disciplines.drag]\ninputs = ["h"]\noutputs = ["f"]\n\n'
    '[disciplines.sink]\ninputs = ["f"]\noutputs = []\n\n'
    '[[variables]]\nname = "h"\nunit = "m"\ndata_type = "float"\ndimension = 1\n\n'
    '[[variables]]\nname = "f"\nunit = "-"\ndata_type = "float"\ndimension = 1\n'
)


def test_warnings_displayed_before_build_success(tmp_path: Path) -> None:
    """Warnings from validation are shown before the build success panel."""
    toml = tmp_path / "problem.toml"
    toml.write_text(_WARNING_TOML)
    result = runner.invoke(get_app(), ["build", str(toml), "--out", str(tmp_path)])
    assert result.exit_code == 0
    assert "sink" in result.output
    # Warning must appear before the success checkmark
    assert result.output.index("sink") < result.output.index("✓")


def test_build_lib_exception_renders_rich_error(tmp_path):
    toml_path = tmp_path / "vleo.toml"
    shutil.copy(FIXTURES_TOML, toml_path)

    with patch("gemseo_gantry.generate_lib", side_effect=RuntimeError("disk full")):
        result = runner.invoke(get_app(), ["build", str(toml_path)])

    assert result.exit_code != 0
    assert "disk full" in result.output


def test_build_lib_exception_renders_json_error(tmp_path):
    toml_path = tmp_path / "vleo.toml"
    shutil.copy(FIXTURES_TOML, toml_path)

    with patch("gemseo_gantry.generate_lib", side_effect=RuntimeError("boom")):
        result = runner.invoke(get_app(), ["build", str(toml_path), "--json"])

    assert result.exit_code != 0
    data = json.loads(result.output)
    assert data["success"] is False
    assert any("boom" in e["message"] for e in data["errors"])


def test_build_refreshes_schema_next_to_toml(tmp_path):
    src = Path(__file__).parents[2] / "fixtures" / "vleo.toml"
    toml = tmp_path / "problem.toml"
    shutil.copyfile(src, toml)

    result = runner.invoke(get_app(), ["build", str(toml), "--flat"])
    assert result.exit_code == 0

    schema_file = tmp_path / "schema" / "problem.schema.json"
    assert schema_file.exists()
    json.loads(schema_file.read_text(encoding="utf-8"))
