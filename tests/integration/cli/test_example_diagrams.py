from __future__ import annotations

import pytest
from typer.testing import CliRunner

runner = CliRunner()


def get_app():
    from gemseo_gantry.cli.main import app

    return app


@pytest.mark.slow
def test_plain_example_generates_diagrams(tmp_path):
    result = runner.invoke(get_app(), ["example", "sellar", str(tmp_path)])
    assert result.exit_code == 0, result.output
    diagrams = tmp_path / "sellar" / "diagrams"
    assert diagrams.is_dir()
    names = {p.name for p in diagrams.iterdir()}
    assert any(n.startswith("n2") for n in names)
    assert "xdsm.html" in names


@pytest.mark.slow
def test_plain_example_leaves_no_h5_or_stubs(tmp_path):
    runner.invoke(get_app(), ["example", "sellar", str(tmp_path)])
    out = tmp_path / "sellar"
    assert not list(out.rglob("*.h5"))
    assert not list(out.rglob("*_scaffold.py"))
