from typer.testing import CliRunner

runner = CliRunner()


def get_app():
    from gemseo_gantry.cli.main import app

    return app


def test_schema_writes_file_under_dir(tmp_path):
    result = runner.invoke(get_app(), ["schema", str(tmp_path)])
    assert result.exit_code == 0
    written = tmp_path / "schema" / "problem.schema.json"
    assert written.exists()
    import json

    json.loads(written.read_text(encoding="utf-8"))


def test_schema_default_path_is_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(get_app(), ["schema"])
    assert result.exit_code == 0
    assert (tmp_path / "schema" / "problem.schema.json").exists()


def test_schema_refuses_overwrite_without_force(tmp_path):
    target = tmp_path / "schema" / "problem.schema.json"
    target.parent.mkdir(parents=True)
    target.write_text("OLD", encoding="utf-8")
    result = runner.invoke(get_app(), ["schema", str(tmp_path)])
    assert result.exit_code == 1
    assert target.read_text(encoding="utf-8") == "OLD"


def test_schema_force_overwrites(tmp_path):
    target = tmp_path / "schema" / "problem.schema.json"
    target.parent.mkdir(parents=True)
    target.write_text("OLD", encoding="utf-8")
    result = runner.invoke(get_app(), ["schema", str(tmp_path), "--force"])
    assert result.exit_code == 0
    assert target.read_text(encoding="utf-8") != "OLD"
