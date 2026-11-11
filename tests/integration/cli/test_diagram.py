import json as _json
import shutil
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

runner = CliRunner()

FIXTURES_TOML = Path(__file__).parent.parent.parent / "fixtures" / "vleo.toml"


def get_app():
    from gemseo_gantry.cli.main import app

    return app


def test_diagram_n2_only(tmp_path):
    toml_path = tmp_path / "vleo.toml"
    shutil.copy(FIXTURES_TOML, toml_path)

    result = runner.invoke(
        get_app(), ["diagram", "n2", str(toml_path), "--output-dir", str(tmp_path)]
    )

    assert result.exit_code == 0
    assert (tmp_path / "n2.pdf").exists()
    assert not (tmp_path / "xdsm.html").exists()


def test_diagram_xdsm_only(tmp_path):
    toml_path = tmp_path / "vleo.toml"
    shutil.copy(FIXTURES_TOML, toml_path)

    result = runner.invoke(
        get_app(), ["diagram", "xdsm", str(toml_path), "--output-dir", str(tmp_path)]
    )

    assert result.exit_code == 0
    assert (tmp_path / "xdsm.html").exists()
    assert not (tmp_path / "n2.pdf").exists()


def test_diagram_default_output_dir(tmp_path):
    toml_path = tmp_path / "vleo.toml"
    shutil.copy(FIXTURES_TOML, toml_path)

    result = runner.invoke(get_app(), ["diagram", "n2", str(toml_path)])

    assert result.exit_code == 0
    assert (tmp_path / "diagrams" / "n2.pdf").exists()


_WARNING_TOML = (
    '[disciplines.drag]\ninputs = ["h"]\noutputs = ["f"]\n\n'
    '[disciplines.sink]\ninputs = ["f"]\noutputs = []\n\n'
    '[[variables]]\nname = "h"\nunit = "m"\ndata_type = "float"\ndimension = 1\n\n'
    '[[variables]]\nname = "f"\nunit = "-"\ndata_type = "float"\ndimension = 1\n'
)


def test_diagram_n2_surfaces_warnings(tmp_path):
    """gantry diagram must not silently drop validation warnings."""
    toml_path = tmp_path / "problem.toml"
    toml_path.write_text(_WARNING_TOML)

    result = runner.invoke(
        get_app(), ["diagram", "n2", str(toml_path), "--output-dir", str(tmp_path)]
    )

    assert result.exit_code == 0
    assert "Warning" in result.output


def test_diagram_n2_json_includes_warnings(tmp_path):
    toml_path = tmp_path / "problem.toml"
    toml_path.write_text(_WARNING_TOML)

    result = runner.invoke(
        get_app(),
        ["diagram", "n2", str(toml_path), "--output-dir", str(tmp_path), "--json"],
    )

    assert result.exit_code == 0
    data = _json.loads(result.output)
    assert len(data["warnings"]) == 1
    assert "sink" in data["warnings"][0]["message"]
    assert data["invocation"]["params"]["toml"] == toml_path.name


def test_diagram_xdsm_fails_without_scenario(tmp_path, monkeypatch):
    toml_path = tmp_path / "vleo.toml"
    shutil.copy(FIXTURES_TOML, toml_path)

    from gemseo_gantry.model.data_model import Discipline, ProblemDefinition

    no_scenario = ProblemDefinition(
        disciplines=[Discipline(name="D", inputs=["x"], outputs=["y"])],
        variables=[],
    )
    monkeypatch.setattr(
        "gemseo_gantry.cli._common.validate_toml", lambda _: no_scenario
    )

    result = runner.invoke(
        get_app(), ["diagram", "xdsm", str(toml_path), "--output-dir", str(tmp_path)]
    )

    assert result.exit_code != 0


def test_diagram_help_lists_subcommands():
    result = runner.invoke(get_app(), ["diagram", "--help"])

    assert result.exit_code == 0
    assert "n2" in result.output
    assert "xdsm" in result.output


def test_diagram_n2_png_format(tmp_path):
    toml_path = tmp_path / "vleo.toml"
    shutil.copy(FIXTURES_TOML, toml_path)

    result = runner.invoke(
        get_app(),
        [
            "diagram",
            "n2",
            str(toml_path),
            "--format",
            "png",
            "--output-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert (tmp_path / "n2.png").exists()
    assert not (tmp_path / "n2.pdf").exists()


def test_diagram_quiet_suppresses_output(tmp_path):
    toml_path = tmp_path / "vleo.toml"
    shutil.copy(FIXTURES_TOML, toml_path)

    result = runner.invoke(
        get_app(),
        ["diagram", "n2", str(toml_path), "--output-dir", str(tmp_path), "--quiet"],
    )

    assert result.exit_code == 0
    assert result.output.strip() == ""


def test_diagram_json_resolve_error(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(get_app(), ["diagram", "n2", "--json"])
    assert result.exit_code != 0
    data = _json.loads(result.output)
    assert data["success"] is False
    assert data["errors"][0]["type"] == "usage"


def test_diagram_json_and_quiet_mutually_exclusive(tmp_path):
    toml_path = tmp_path / "vleo.toml"
    shutil.copy(FIXTURES_TOML, toml_path)
    result = runner.invoke(
        get_app(), ["diagram", "n2", str(toml_path), "--json", "--quiet"]
    )
    assert result.exit_code != 0


def test_diagram_rich_output_is_rich_specific(tmp_path):
    """Rich output contains file paths - definitively not JSON."""
    toml_path = tmp_path / "vleo.toml"
    shutil.copy(FIXTURES_TOML, toml_path)
    result = runner.invoke(get_app(), ["diagram", "n2", str(toml_path)])
    assert result.exit_code == 0
    assert "Files created" in result.output


# -- n2 validation failure (lines 65-67) --------------------------------------


def test_diagram_n2_fails_on_invalid_toml(tmp_path):
    bad = tmp_path / "bad.toml"
    bad.write_text("not valid toml [[[", encoding="utf-8")

    result = runner.invoke(get_app(), ["diagram", "n2", str(bad)])

    assert result.exit_code != 0


# -- xdsm paths ----------------------------------------------------------------


def test_diagram_xdsm_json_and_quiet_mutually_exclusive(tmp_path):
    """--json and --quiet are mutually exclusive for xdsm too (line 114)."""
    toml_path = tmp_path / "vleo.toml"
    shutil.copy(FIXTURES_TOML, toml_path)

    result = runner.invoke(
        get_app(), ["diagram", "xdsm", str(toml_path), "--json", "--quiet"]
    )

    assert result.exit_code != 0


def test_diagram_xdsm_resolve_error(tmp_path, monkeypatch):
    """xdsm command emits an error when no TOML can be resolved (lines 118-120)."""
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(get_app(), ["diagram", "xdsm"])

    assert result.exit_code != 0


def test_diagram_xdsm_fails_on_invalid_toml(tmp_path):
    """xdsm validation failure path (lines 124-126)."""
    bad = tmp_path / "bad.toml"
    bad.write_text("not valid toml [[[", encoding="utf-8")

    result = runner.invoke(get_app(), ["diagram", "xdsm", str(bad)])

    assert result.exit_code != 0


def test_diagram_xdsm_no_scenario_error_message(tmp_path):
    """xdsm emits a 'no scenarios' error when problem has no scenarios (lines 137-146)."""
    toml_path = tmp_path / "vleo.toml"
    shutil.copy(FIXTURES_TOML, toml_path)

    from gemseo_gantry.cli._result import ValidateResult
    from gemseo_gantry.model.data_model import Discipline, ProblemDefinition

    problem_no_scenarios = ProblemDefinition(
        disciplines=[Discipline(name="D", inputs=["x"], outputs=["y"])],
        variables=[],
    )
    fake_result = ValidateResult(
        valid=True, file="vleo.toml", problem=problem_no_scenarios
    )

    with patch("gemseo_gantry.cli.diagram.run_validate", return_value=fake_result):
        result = runner.invoke(
            get_app(),
            ["diagram", "xdsm", str(toml_path), "--output-dir", str(tmp_path)],
        )

    assert result.exit_code != 0
    assert "scenarios" in result.output.lower() or "XDSM" in result.output
