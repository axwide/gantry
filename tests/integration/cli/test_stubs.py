from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

runner = CliRunner()

FIXTURES_TOML = Path(__file__).parent.parent.parent / "fixtures" / "vleo.toml"


def get_app():
    from gemseo_gantry.cli.main import app

    return app


def test_validate_exits_zero():
    result = runner.invoke(get_app(), ["validate", str(FIXTURES_TOML)])
    assert "not yet implemented" not in result.output
    assert result.exit_code == 0


def test_validate_watch_flag_exits_zero():
    with patch("watchfiles.watch", side_effect=KeyboardInterrupt):
        result = runner.invoke(get_app(), ["validate", str(FIXTURES_TOML), "--watch"])
    assert "not yet implemented" not in result.output
    assert result.exit_code == 0
