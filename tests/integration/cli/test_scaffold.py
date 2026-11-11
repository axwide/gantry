import json
import shutil
from pathlib import Path

from typer.testing import CliRunner

runner = CliRunner()

FIXTURES_TOML = Path(__file__).parent.parent.parent / "fixtures" / "vleo.toml"


def get_app():
    from gemseo_gantry.cli.main import app

    return app


def _setup(tmp_path: Path) -> Path:
    """Copy vleo.toml to tmp_path and pre-build lib/. Returns the toml path."""
    from gemseo_gantry.generator.lib_generator import generate_lib
    from gemseo_gantry.parser.toml_parser import parse_toml

    toml_path = tmp_path / "vleo.toml"
    shutil.copy(FIXTURES_TOML, toml_path)
    generate_lib(parse_toml(toml_path), tmp_path)
    return toml_path


def test_scaffold_default_writes_disciplines_and_executor(tmp_path):
    toml_path = _setup(tmp_path)

    result = runner.invoke(
        get_app(),
        ["scaffold", str(toml_path), "--import-root", str(tmp_path)],
    )

    assert result.exit_code == 0
    assert (tmp_path / "disciplines").is_dir()
    assert (tmp_path / "execute_Vleo.py").exists()
    assert (tmp_path / "load_Vleo.py").exists()


def test_scaffold_only_disciplines(tmp_path):
    toml_path = _setup(tmp_path)

    result = runner.invoke(
        get_app(),
        ["scaffold", str(toml_path), "--import-root", str(tmp_path), "--only", "d"],
    )

    assert result.exit_code == 0
    assert (tmp_path / "disciplines").is_dir()
    assert not (tmp_path / "execute_Vleo.py").exists()
    assert not (tmp_path / "load_Vleo.py").exists()


def test_scaffold_only_disciplines_long_form(tmp_path):
    toml_path = _setup(tmp_path)

    result = runner.invoke(
        get_app(),
        [
            "scaffold",
            str(toml_path),
            "--import-root",
            str(tmp_path),
            "--only",
            "disciplines",
        ],
    )

    assert result.exit_code == 0
    assert (tmp_path / "disciplines").is_dir()
    assert not (tmp_path / "execute_Vleo.py").exists()


def test_scaffold_only_executor(tmp_path):
    toml_path = _setup(tmp_path)

    result = runner.invoke(
        get_app(),
        ["scaffold", str(toml_path), "--import-root", str(tmp_path), "--only", "e"],
    )

    assert result.exit_code == 0
    assert not (tmp_path / "disciplines").exists()
    assert (tmp_path / "execute_Vleo.py").exists()
    assert not (tmp_path / "load_Vleo.py").exists()


def test_scaffold_only_loader(tmp_path):
    toml_path = _setup(tmp_path)

    result = runner.invoke(
        get_app(),
        ["scaffold", str(toml_path), "--import-root", str(tmp_path), "--only", "l"],
    )

    assert result.exit_code == 0
    assert not (tmp_path / "disciplines").exists()
    assert not (tmp_path / "execute_Vleo.py").exists()
    assert (tmp_path / "load_Vleo.py").exists()


def test_scaffold_only_comma_separated(tmp_path):
    toml_path = _setup(tmp_path)

    result = runner.invoke(
        get_app(),
        ["scaffold", str(toml_path), "--import-root", str(tmp_path), "--only", "d,e"],
    )

    assert result.exit_code == 0
    assert (tmp_path / "disciplines").is_dir()
    assert (tmp_path / "execute_Vleo.py").exists()
    assert not (tmp_path / "load_Vleo.py").exists()


def test_scaffold_only_repeated_flags(tmp_path):
    toml_path = _setup(tmp_path)

    result = runner.invoke(
        get_app(),
        [
            "scaffold",
            str(toml_path),
            "--import-root",
            str(tmp_path),
            "--only",
            "e",
            "--only",
            "l",
        ],
    )

    assert result.exit_code == 0
    assert not (tmp_path / "disciplines").exists()
    assert (tmp_path / "execute_Vleo.py").exists()
    assert (tmp_path / "load_Vleo.py").exists()


def test_scaffold_only_invalid_value(tmp_path):
    toml_path = _setup(tmp_path)

    result = runner.invoke(
        get_app(),
        ["scaffold", str(toml_path), "--only", "unknown"],
    )

    assert result.exit_code != 0


def test_scaffold_write_once_skips_existing(tmp_path):
    toml_path = _setup(tmp_path)
    # First call - writes
    runner.invoke(
        get_app(),
        ["scaffold", str(toml_path), "--import-root", str(tmp_path)],
    )
    drag_stub = tmp_path / "disciplines" / "Drag_scaffold.py"
    original_content = drag_stub.read_text(encoding="utf-8")

    # Second call - should skip
    result = runner.invoke(
        get_app(),
        ["scaffold", str(toml_path), "--import-root", str(tmp_path)],
    )

    assert result.exit_code == 0
    assert drag_stub.read_text(encoding="utf-8") == original_content
    assert "skipped" in result.output.lower()


def test_scaffold_force_overwrites(tmp_path):
    toml_path = _setup(tmp_path)
    runner.invoke(
        get_app(),
        ["scaffold", str(toml_path), "--import-root", str(tmp_path)],
    )
    drag_stub = tmp_path / "disciplines" / "Drag_scaffold.py"
    drag_stub.write_text("# modified", encoding="utf-8")

    result = runner.invoke(
        get_app(),
        ["scaffold", str(toml_path), "--import-root", str(tmp_path), "--force"],
    )

    assert result.exit_code == 0
    assert drag_stub.read_text(encoding="utf-8") != "# modified"


def test_scaffold_custom_directories(tmp_path):
    toml_path = _setup(tmp_path)
    disc_dir = tmp_path / "my_stubs"
    exec_dir = tmp_path / "my_runners"

    result = runner.invoke(
        get_app(),
        [
            "scaffold",
            str(toml_path),
            "--disciplines-into",
            str(disc_dir),
            "--executor-into",
            str(exec_dir),
            "--import-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert disc_dir.is_dir()
    assert exec_dir.is_dir()


def test_scaffold_runnable_writes_placeholder_stubs(tmp_path):
    toml_path = _setup(tmp_path)

    result = runner.invoke(
        get_app(),
        ["scaffold", str(toml_path), "--import-root", str(tmp_path), "--runnable"],
    )

    assert result.exit_code == 0
    drag_stub = tmp_path / "disciplines" / "Drag_scaffold.py"
    assert drag_stub.exists()
    content = drag_stub.read_text(encoding="utf-8")
    assert "NotImplementedError" not in content


def test_scaffold_runnable_without_disciplines_is_rejected(tmp_path):
    toml_path = _setup(tmp_path)

    result = runner.invoke(
        get_app(),
        ["scaffold", str(toml_path), "--runnable", "--only", "e"],
    )

    assert result.exit_code != 0


def test_scaffold_custom_lib_dir(tmp_path):
    toml_path = _setup(tmp_path)
    custom_lib_dir = tmp_path / "custom_lib"
    # generate lib into custom path so scaffold can find it
    from gemseo_gantry.generator.lib_generator import generate_lib
    from gemseo_gantry.parser.toml_parser import parse_toml

    generate_lib(parse_toml(toml_path), custom_lib_dir.parent, lib_name="custom_lib")

    result = runner.invoke(
        get_app(),
        [
            "scaffold",
            str(toml_path),
            "--lib-dir",
            str(custom_lib_dir),
            "--import-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert (tmp_path / "disciplines").is_dir()


def test_scaffold_quiet_suppresses_output(tmp_path):
    toml_path = _setup(tmp_path)

    result = runner.invoke(
        get_app(),
        ["scaffold", str(toml_path), "--import-root", str(tmp_path), "--quiet"],
    )

    assert result.exit_code == 0
    assert result.output.strip() == ""


def test_scaffold_fails_on_invalid_toml(tmp_path):
    bad_toml = tmp_path / "bad.toml"
    bad_toml.write_text("not valid toml [[[", encoding="utf-8")

    result = runner.invoke(get_app(), ["scaffold", str(bad_toml)])

    assert result.exit_code != 0


def test_scaffold_json_success(tmp_path):
    toml_path = _setup(tmp_path)
    result = runner.invoke(
        get_app(),
        ["scaffold", str(toml_path), "--import-root", str(tmp_path), "--json"],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["success"] is True
    assert data["invocation"]["command"] == ["scaffold"]
    assert isinstance(data["artifacts"], list)
    assert len(data["artifacts"]) > 0
    assert all(a["status"] in ("written", "skipped") for a in data["artifacts"])


def test_scaffold_json_invalid_toml(tmp_path):
    bad = tmp_path / "bad.toml"
    bad.write_text("[disciplines.drag]\noutputs=['f']\n", encoding="utf-8")
    result = runner.invoke(get_app(), ["scaffold", str(bad), "--json"])
    assert result.exit_code != 0
    data = json.loads(result.output)
    assert data["success"] is False
    assert len(data["errors"]) > 0


def test_scaffold_json_resolve_error(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(get_app(), ["scaffold", "--json"])
    assert result.exit_code != 0
    data = json.loads(result.output)
    assert data["success"] is False
    assert data["errors"][0]["type"] == "usage"


def test_scaffold_json_and_quiet_mutually_exclusive(tmp_path):
    toml_path = _setup(tmp_path)
    result = runner.invoke(
        get_app(),
        [
            "scaffold",
            str(toml_path),
            "--import-root",
            str(tmp_path),
            "--json",
            "--quiet",
        ],
    )
    assert result.exit_code != 0


def test_scaffold_rich_output_is_rich_specific(tmp_path):
    """Rich output path contains ✓ - definitively not JSON."""
    toml_path = _setup(tmp_path)
    result = runner.invoke(
        get_app(),
        ["scaffold", str(toml_path), "--import-root", str(tmp_path)],
    )
    assert result.exit_code == 0
    assert "✓" in result.output or "written" in result.output.lower()


_WARNING_TOML = (
    '[disciplines.drag]\ninputs = ["h"]\noutputs = ["f"]\n\n'
    '[disciplines.sink]\ninputs = ["f"]\noutputs = []\n\n'
    '[[variables]]\nname = "h"\nunit = "m"\ndata_type = "float"\ndimension = 1\n\n'
    '[[variables]]\nname = "f"\nunit = "-"\ndata_type = "float"\ndimension = 1\n'
)


def test_warnings_displayed_before_scaffold_success(tmp_path: Path) -> None:
    """Warnings from validation are shown before the scaffold success panel."""
    from gemseo_gantry.generator.lib_generator import generate_lib
    from gemseo_gantry.parser.toml_parser import parse_toml

    toml = tmp_path / "problem.toml"
    toml.write_text(_WARNING_TOML)
    generate_lib(parse_toml(toml), tmp_path)
    result = runner.invoke(
        get_app(), ["scaffold", str(toml), "--import-root", str(tmp_path)]
    )
    assert result.exit_code == 0
    assert "sink" in result.output
    # Warning must appear before the success panel ("✓ problem.toml is valid")
    assert result.output.index("sink") < result.output.index("✓")


def test_scaffold_without_build_fails_with_hint(tmp_path):
    toml_path = tmp_path / "vleo.toml"
    shutil.copy(FIXTURES_TOML, toml_path)

    result = runner.invoke(
        get_app(),
        ["scaffold", str(toml_path), "--import-root", str(tmp_path)],
    )

    assert result.exit_code == 1
    assert "No generated lib found" in result.output
    assert "gantry build" in result.output
    assert "--lib-dir" in result.output
    assert not (tmp_path / "disciplines").exists()
    assert not (tmp_path / "execute_Vleo.py").exists()
