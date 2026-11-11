import json

from typer.testing import CliRunner

runner = CliRunner()


def get_app():
    from gemseo_gantry.cli.main import app

    return app


def test_init_creates_file(tmp_path):
    target = tmp_path / "problem.toml"
    result = runner.invoke(get_app(), ["init", str(target)])
    assert result.exit_code == 0
    assert target.exists()


def test_init_default_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(get_app(), ["init"])
    assert result.exit_code == 0
    assert (tmp_path / "problem.toml").exists()


def test_init_fails_if_file_exists(tmp_path):
    target = tmp_path / "problem.toml"
    target.write_text("existing", encoding="utf-8")
    result = runner.invoke(get_app(), ["init", str(target)])
    assert result.exit_code != 0
    assert target.read_text(encoding="utf-8") == "existing"


def test_init_template_is_valid_toml(tmp_path):
    import tomllib

    target = tmp_path / "problem.toml"
    result = runner.invoke(get_app(), ["init", str(target)])
    assert result.exit_code == 0
    tomllib.loads(target.read_text(encoding="utf-8"))  # raises on invalid TOML


def test_init_template_parses_as_problem_definition(tmp_path):
    from gemseo_gantry.parser.toml_parser import parse_toml

    target = tmp_path / "problem.toml"
    runner.invoke(get_app(), ["init", str(target)])
    problem = parse_toml(target)
    assert len(problem.disciplines) >= 1
    assert len(problem.scenarios) >= 1


def test_init_force_overwrites_existing(tmp_path):
    target = tmp_path / "problem.toml"
    target.write_text("# old content", encoding="utf-8")

    result = runner.invoke(get_app(), ["init", str(target), "--force"])

    assert result.exit_code == 0
    assert target.read_text(encoding="utf-8") != "# old content"


def test_init_quiet_suppresses_output(tmp_path):
    target = tmp_path / "problem.toml"

    result = runner.invoke(get_app(), ["init", str(target), "--quiet"])

    assert result.exit_code == 0
    assert target.exists()
    assert result.output.strip() == ""


def test_init_json_success(tmp_path):
    target = tmp_path / "problem.toml"
    result = runner.invoke(get_app(), ["init", str(target), "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["invocation"]["command"] == ["init"]
    assert data["success"] is True
    kinds = {a["kind"] for a in data["artifacts"]}
    assert kinds == {"problem_definition", "schema"}
    assert all(a["status"] == "written" for a in data["artifacts"])
    assert target.exists()


def test_init_json_file_exists_error(tmp_path):
    target = tmp_path / "problem.toml"
    target.write_text("existing", encoding="utf-8")
    result = runner.invoke(get_app(), ["init", str(target), "--json"])
    assert result.exit_code != 0
    data = json.loads(result.output)
    assert data["success"] is False
    assert data["errors"][0]["type"] == "usage"


def test_init_json_and_quiet_mutually_exclusive(tmp_path):
    target = tmp_path / "problem.toml"
    result = runner.invoke(get_app(), ["init", str(target), "--json", "--quiet"])
    assert result.exit_code != 0


def test_init_rejects_non_toml_extension(tmp_path):
    target = tmp_path / "problem.yaml"
    result = runner.invoke(get_app(), ["init", str(target)])
    assert result.exit_code != 0
    assert not target.exists()


def test_init_rejects_non_toml_extension_json(tmp_path):
    target = tmp_path / "problem.yaml"
    result = runner.invoke(get_app(), ["init", str(target), "--json"])
    assert result.exit_code != 0
    data = json.loads(result.output)
    assert data["success"] is False
    assert any(".toml" in e["message"] for e in data["errors"])


def test_init_rich_output_is_rich_specific(tmp_path):
    """Rich output contains 'Files created' panel text - definitively not JSON."""
    target = tmp_path / "problem.toml"
    result = runner.invoke(get_app(), ["init", str(target)])
    assert result.exit_code == 0
    assert "Files created" in result.output


def test_init_rich_output_lists_both_artifacts(tmp_path, monkeypatch):
    """Human output reports the schema alongside the toml, matching JSON parity.

    Runs from tmp_path so the artifacts render as short relative paths; an
    absolute path would be truncated by the Rich panel width.
    """
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(get_app(), ["init", "problem.toml"])
    assert result.exit_code == 0
    assert "problem.toml" in result.output
    assert ".schema.json" in result.output


def test_init_toml_starts_with_schema_directive(tmp_path):
    from gemseo_gantry.schema import SCHEMA_DIRECTIVE

    target = tmp_path / "problem.toml"
    result = runner.invoke(get_app(), ["init", str(target)])
    assert result.exit_code == 0
    first_line = target.read_text(encoding="utf-8").splitlines()[0]
    assert first_line == SCHEMA_DIRECTIVE


def test_init_writes_schema_alongside_toml(tmp_path):
    import json

    target = tmp_path / "problem.toml"
    result = runner.invoke(get_app(), ["init", str(target)])
    assert result.exit_code == 0
    schema_file = tmp_path / "schema" / "problem.schema.json"
    assert schema_file.exists()
    json.loads(schema_file.read_text(encoding="utf-8"))
