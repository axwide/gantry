from __future__ import annotations

import pytest
from typer.testing import CliRunner

runner = CliRunner()


def get_app():
    from gemseo_gantry.cli.main import app

    return app


@pytest.fixture(autouse=True)
def _fast_walkthrough(monkeypatch):
    # Stub the heavy diagram generation and the subprocess runner so the fast
    # --explain tests exercise the driver + file-op stages without spawning builds.
    monkeypatch.setattr(
        "gemseo_gantry.examples.runner.generate_diagrams",
        lambda problem, target: [],
    )

    def _fake_run(argv, cwd, console, header, **kwargs):
        if "--dump-toml" in header:
            cwd.mkdir(parents=True, exist_ok=True)
            (cwd / f"{cwd.name}.toml").write_text("[test]", encoding="utf-8")
        return 0

    monkeypatch.setattr("gemseo_gantry.cli._walkthrough._run_streamed", _fake_run)


def test_explain_narrates_all_steps(tmp_path):
    result = runner.invoke(get_app(), ["example", "sellar", str(tmp_path), "--explain"])
    assert result.exit_code == 0, result.output
    out = result.output.lower()
    for marker in [
        "problem definition",
        "validate",
        "build",
        "diagram",
        "scaffold",
        "physics",
        "run",
        "post-process",
    ]:
        assert marker in out


def test_explain_fills_finished_discipline(tmp_path):
    runner.invoke(get_app(), ["example", "sellar", str(tmp_path), "--explain"])
    out = tmp_path / "sellar"
    disc = (out / "disciplines" / "Sellar1.py").read_text(encoding="utf-8")
    assert "np.sqrt" in disc
    assert "raise NotImplementedError" not in disc


def test_explain_writes_toml(tmp_path):
    runner.invoke(get_app(), ["example", "sellar", str(tmp_path), "--explain"])
    assert (tmp_path / "sellar" / "sellar.toml").is_file()
