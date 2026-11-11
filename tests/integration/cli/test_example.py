import json

import pytest
from typer.testing import CliRunner

runner = CliRunner()


@pytest.fixture(autouse=True)
def _stub_diagrams(monkeypatch):
    # Keep the fast example tests off the heavy GEMSEO diagram path.
    monkeypatch.setattr(
        "gemseo_gantry.examples.runner.generate_diagrams",
        lambda problem, target: [],
    )


def get_app():
    from gemseo_gantry.cli.main import app

    return app


def test_example_generates_tree(tmp_path):
    result = runner.invoke(get_app(), ["example", "sellar", str(tmp_path)])
    assert result.exit_code == 0, result.output
    out = tmp_path / "sellar"
    assert (out / "sellar.toml").is_file()
    assert (out / "lib").is_dir()
    assert (out / "disciplines" / "Sellar1.py").is_file()
    assert (out / "execute_Sellar.py").is_file()
    assert (out / "postprocess.py").is_file()


def test_example_unknown_name_errors(tmp_path):
    result = runner.invoke(get_app(), ["example", "nope", str(tmp_path)])
    assert result.exit_code == 2  # Typer argument validation error
    assert "sellar" in result.output  # lists available


def test_example_refuses_nonempty_target_without_force(tmp_path):
    existing = tmp_path / "sellar"
    existing.mkdir()
    (existing / "keep.txt").write_text("x", encoding="utf-8")
    result = runner.invoke(get_app(), ["example", "sellar", str(tmp_path)])
    assert result.exit_code == 1
    assert not (existing / "sellar.toml").exists()


def test_example_force_overwrites_nonempty_target(tmp_path):
    existing = tmp_path / "sellar"
    existing.mkdir()
    (existing / "keep.txt").write_text("x", encoding="utf-8")
    result = runner.invoke(get_app(), ["example", "sellar", str(tmp_path), "--force"])
    assert result.exit_code == 0, result.output
    assert (existing / "sellar.toml").is_file()


def test_example_json_success(tmp_path):
    result = runner.invoke(get_app(), ["example", "sellar", str(tmp_path), "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["invocation"]["command"] == ["example"]
    assert data["success"] is True
    paths = [a["path"] for a in data["artifacts"]]
    assert any("sellar.toml" in p for p in paths)


def test_example_quiet_suppresses_output(tmp_path):
    result = runner.invoke(get_app(), ["example", "sellar", str(tmp_path), "--quiet"])
    assert result.exit_code == 0
    assert result.output.strip() == ""


def test_example_human_output_uses_envelope_panel(tmp_path):
    result = runner.invoke(get_app(), ["example", "sellar", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert "gantry example" in result.output
    assert "'sellar'" in result.output
    assert "uv run python" not in result.output


def test_example_sobieski_generates_tree(tmp_path):
    result = runner.invoke(get_app(), ["example", "sobieski", str(tmp_path)])
    assert result.exit_code == 0, result.output
    out = tmp_path / "sobieski"
    assert (out / "sobieski.toml").is_file()
    assert (out / "lib").is_dir()
    assert (out / "disciplines" / "Structure.py").is_file()
    assert (out / "execute_SystemScenario.py").is_file()
    assert (out / "postprocess.py").is_file()
