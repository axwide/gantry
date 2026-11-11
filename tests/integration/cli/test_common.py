from __future__ import annotations

from io import StringIO
from pathlib import Path

import pytest
from rich.console import Console
from rich.status import Status

from gemseo_gantry.cli._common import ResolveError, run_validate

# -- run_validate --------------------------------------------------------------


def test_run_validate_valid_file(tmp_path: Path) -> None:
    toml = tmp_path / "problem.toml"
    toml.write_text(
        '[disciplines.drag]\ninputs = ["h"]\noutputs = ["duty_cycle"]\n\n'
        '[[variables]]\nname = "h"\nunit = "m"\ndata_type = "float"\ndimension = 1\n\n'
        '[[variables]]\nname = "duty_cycle"\nunit = "-"\ndata_type = "float"\ndimension = 1\n'
    )
    result = run_validate(toml)
    assert result.valid is True
    assert result.file == "problem.toml"
    assert result.errors == []
    assert result.problem is not None


def test_run_validate_missing_file(tmp_path: Path) -> None:
    result = run_validate(tmp_path / "ghost.toml")
    assert result.valid is False
    assert result.problem is None
    assert len(result.errors) == 1
    assert result.errors[0].type == "file_not_found"


def test_run_validate_toml_syntax_error(tmp_path: Path) -> None:
    toml = tmp_path / "bad.toml"
    toml.write_text("[disciplines\n")
    result = run_validate(toml)
    assert result.valid is False
    assert result.errors[0].type == "syntax"


def test_run_validate_schema_error(tmp_path: Path) -> None:
    toml = tmp_path / "bad.toml"
    toml.write_text(
        "[disciplines.drag]\n"
        'inputs = ["h"]\n'
        'outputs = ["duty_cycle"]\n'
        "\n[[variables]]\n"
        'name = "h"\n'
    )
    result = run_validate(toml)
    assert result.valid is False
    assert result.errors[0].type == "structural"
    assert any(
        "unit" in e.message or "data_type" in e.message or "dimension" in e.message
        for e in result.errors
    )


def test_run_validate_semantic_error(tmp_path: Path) -> None:
    toml = tmp_path / "bad.toml"
    toml.write_text(
        "[disciplines.drag]\n"
        'inputs = ["h"]\n'
        'outputs = ["duty_cycle"]\n'
        "[disciplines.power]\n"
        'inputs = ["h"]\n'
        'outputs = ["duty_cycle"]\n'
    )
    result = run_validate(toml)
    assert result.valid is False
    assert any("duty_cycle" in e.message for e in result.errors)


def test_run_validate_sets_file_name(tmp_path: Path) -> None:
    toml = tmp_path / "my_problem.toml"
    toml.write_text(
        '[disciplines.drag]\ninputs = ["h"]\noutputs = ["f"]\n\n'
        '[[variables]]\nname = "h"\nunit = "m"\ndata_type = "float"\ndimension = 1\n\n'
        '[[variables]]\nname = "f"\nunit = "-"\ndata_type = "float"\ndimension = 1\n'
    )
    result = run_validate(toml)
    assert result.file == "my_problem.toml"


def test_run_validate_propagates_warnings_as_diagnostics(tmp_path: Path) -> None:
    """A discipline with no outputs produces a Diagnostic('validation', ...) warning."""
    toml = tmp_path / "problem.toml"
    toml.write_text(
        '[disciplines.drag]\ninputs = ["h"]\noutputs = ["f"]\n\n'
        '[disciplines.sink]\ninputs = ["f"]\noutputs = []\n\n'
        '[[variables]]\nname = "h"\nunit = "m"\ndata_type = "float"\ndimension = 1\n\n'
        '[[variables]]\nname = "f"\nunit = "-"\ndata_type = "float"\ndimension = 1\n'
    )
    result = run_validate(toml)
    assert result.valid is True
    assert len(result.warnings) == 1
    assert result.warnings[0].type == "validation"
    assert "sink" in result.warnings[0].message


def test_run_validate_surfaces_warnings_even_when_invalid(tmp_path: Path) -> None:
    """Warnings must still be reported when validation fails with errors."""
    toml = tmp_path / "problem.toml"
    toml.write_text(
        # 'dup' is output by two disciplines -> semantic error;
        # 'sink' has no outputs -> warning. Both must surface.
        '[disciplines.drag]\ninputs = ["h"]\noutputs = ["dup"]\n\n'
        '[disciplines.power]\ninputs = ["h"]\noutputs = ["dup"]\n\n'
        '[disciplines.sink]\ninputs = ["dup"]\noutputs = []\n\n'
        '[[variables]]\nname = "h"\nunit = "m"\ndata_type = "float"\ndimension = 1\n\n'
        '[[variables]]\nname = "dup"\nunit = "-"\ndata_type = "float"\ndimension = 1\n'
    )
    result = run_validate(toml)
    assert result.valid is False
    assert any("dup" in e.message for e in result.errors)
    assert any("sink" in w.message for w in result.warnings)
    assert all(w.type == "validation" for w in result.warnings)


# -- ResolveError --------------------------------------------------------------


def test_resolve_error_is_exception() -> None:
    exc = ResolveError("no toml found")
    assert isinstance(exc, Exception)
    assert str(exc) == "no toml found"


# -- resolve_toml --------------------------------------------------------------


def test_resolve_toml_returns_given_path(tmp_path: Path) -> None:
    toml = tmp_path / "problem.toml"
    toml.touch()
    from gemseo_gantry.cli._common import resolve_toml

    assert resolve_toml(toml) == toml


def test_resolve_toml_wrong_suffix_raises(tmp_path: Path) -> None:
    from gemseo_gantry.cli._common import ResolveError, resolve_toml

    with pytest.raises(ResolveError, match="Expected a .toml file"):
        resolve_toml(tmp_path / "problem.json")


def test_resolve_toml_auto_detects_single_toml(tmp_path: Path, monkeypatch) -> None:
    toml = tmp_path / "problem.toml"
    toml.touch()
    monkeypatch.chdir(tmp_path)
    from gemseo_gantry.cli._common import resolve_toml

    assert resolve_toml(None) == toml


def test_resolve_toml_no_toml_raises(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    from gemseo_gantry.cli._common import ResolveError, resolve_toml

    with pytest.raises(ResolveError, match="No .toml file found"):
        resolve_toml(None)


def test_resolve_toml_multiple_tomls_raises(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "a.toml").touch()
    (tmp_path / "b.toml").touch()
    monkeypatch.chdir(tmp_path)
    from gemseo_gantry.cli._common import ResolveError, resolve_toml

    with pytest.raises(ResolveError, match="Multiple .toml files found"):
        resolve_toml(None)


# -- make_spinner --------------------------------------------------------------


def _test_console() -> Console:
    return Console(file=StringIO(), force_terminal=False)


def test_make_spinner_returns_status_by_default() -> None:
    from gemseo_gantry.cli._common import make_spinner

    spinner = make_spinner(_test_console(), "Working...")
    assert isinstance(spinner, Status)


def test_make_spinner_quiet_returns_noop() -> None:
    from gemseo_gantry.cli._common import _NoOpSpinner, make_spinner

    spinner = make_spinner(_test_console(), "Working...", quiet=True)
    assert isinstance(spinner, _NoOpSpinner)


def test_make_spinner_json_mode_returns_noop() -> None:
    from gemseo_gantry.cli._common import _NoOpSpinner, make_spinner

    spinner = make_spinner(_test_console(), "Working...", json_mode=True)
    assert isinstance(spinner, _NoOpSpinner)


def test_noop_spinner_is_context_manager() -> None:
    from gemseo_gantry.cli._common import _NoOpSpinner

    with _NoOpSpinner() as s:
        assert s is not None


def test_noop_spinner_start_stop_are_callable() -> None:
    from gemseo_gantry.cli._common import _NoOpSpinner

    s = _NoOpSpinner()
    s.start()
    s.stop()


def test_noop_spinner_update_accepts_any_args() -> None:
    from gemseo_gantry.cli._common import _NoOpSpinner

    s = _NoOpSpinner()
    s.update("status text", spinner="dots", style="green")  # should not raise
