from __future__ import annotations

import json
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from rich.console import Console
from typer.testing import CliRunner

runner = CliRunner()


def get_app():
    from gemseo_gantry.cli.main import app

    return app


def _console() -> tuple[Console, StringIO]:
    sio = StringIO()
    return Console(file=sio, force_terminal=False), sio


def _inv(path: Path):
    """Build the invocation `_run` expects, mirroring what `validate()` passes."""
    from gemseo_gantry.cli._result import Invocation

    return Invocation(command=["validate"], params={"toml": path.name})


VALID_TOML = (
    '[disciplines.drag]\ninputs = ["h"]\noutputs = ["duty_cycle"]\n\n'
    '[[variables]]\nname = "h"\nunit = "m"\ndata_type = "float"\ndimension = 1\n\n'
    '[[variables]]\nname = "duty_cycle"\nunit = "-"\ndata_type = "float"\ndimension = 1\n'
)


# -- Rich output (no --json) ---------------------------------------------------


def test_valid_file_returns_0(tmp_path: Path) -> None:
    toml = tmp_path / "problem.toml"
    toml.write_text(VALID_TOML)
    con, out = _console()
    from gemseo_gantry.cli.validate import _run

    assert (
        _run(toml, invocation=_inv(toml), watch=False, console=con, json_mode=False)
        == 0
    )
    assert "✓" in out.getvalue()


def test_missing_file_returns_1(tmp_path: Path) -> None:
    con, out = _console()
    from gemseo_gantry.cli.validate import _run

    assert (
        _run(
            tmp_path / "ghost.toml",
            invocation=_inv(tmp_path / "ghost.toml"),
            watch=False,
            console=con,
            json_mode=False,
        )
        == 1
    )
    assert "✗" in out.getvalue()


def test_toml_syntax_error_returns_1(tmp_path: Path) -> None:
    toml = tmp_path / "bad.toml"
    toml.write_text("[disciplines\n")
    con, out = _console()
    from gemseo_gantry.cli.validate import _run

    assert (
        _run(toml, invocation=_inv(toml), watch=False, console=con, json_mode=False)
        == 1
    )
    assert "✗" in out.getvalue()


def test_schema_error_returns_1(tmp_path: Path) -> None:
    toml = tmp_path / "bad.toml"
    toml.write_text(
        "[disciplines.drag]\n"
        'inputs = ["h"]\n'
        'outputs = ["duty_cycle"]\n'
        "\n[[variables]]\n"
        'name = "h"\n'
    )
    con, out = _console()
    from gemseo_gantry.cli.validate import _run

    assert (
        _run(toml, invocation=_inv(toml), watch=False, console=con, json_mode=False)
        == 1
    )
    assert "✗" in out.getvalue()


def test_semantic_error_returns_1_and_names_variable(tmp_path: Path) -> None:
    toml = tmp_path / "bad.toml"
    toml.write_text(
        "[disciplines.drag]\n"
        'inputs = ["h"]\noutputs = ["duty_cycle"]\n'
        "[disciplines.power]\n"
        'inputs = ["h"]\noutputs = ["duty_cycle"]\n'
    )
    con, out = _console()
    from gemseo_gantry.cli.validate import _run

    assert (
        _run(toml, invocation=_inv(toml), watch=False, console=con, json_mode=False)
        == 1
    )
    assert "duty_cycle" in out.getvalue()


def test_no_disciplines_returns_1(tmp_path: Path) -> None:
    toml = tmp_path / "empty.toml"
    toml.write_text("")
    con, _ = _console()
    from gemseo_gantry.cli.validate import _run

    assert (
        _run(toml, invocation=_inv(toml), watch=False, console=con, json_mode=False)
        == 1
    )


_SINGLE_ERROR_TOML = (
    "[disciplines.drag]\ninputs = ['h']\noutputs = ['dup']\n"
    "[disciplines.power]\ninputs = ['h']\noutputs = ['dup']\n"  # double output: one error
)


def test_rich_error_output_is_bulleted_even_for_single_error(tmp_path: Path) -> None:
    toml = tmp_path / "bad.toml"
    toml.write_text(_SINGLE_ERROR_TOML)
    con, out = _console()
    from gemseo_gantry.cli.validate import _run

    assert (
        _run(toml, invocation=_inv(toml), watch=False, console=con, json_mode=False)
        == 1
    )
    text = out.getvalue()
    assert "• " in text
    assert "dup" in text


# -- JSON output (--json) ------------------------------------------------------


def test_json_valid_file(tmp_path: Path, capsys) -> None:
    toml = tmp_path / "problem.toml"
    toml.write_text(VALID_TOML)
    result = runner.invoke(get_app(), ["validate", str(toml), "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["invocation"]["command"] == ["validate"]
    assert data["success"] is True
    assert data["errors"] == []
    assert "warnings" in data


def test_json_output_is_plain_ascii_and_bullet_free(tmp_path: Path) -> None:
    """JSON message text must be plain ASCII with no rich bullet decoration."""
    toml = tmp_path / "bad.toml"
    toml.write_text(_SINGLE_ERROR_TOML)
    result = runner.invoke(get_app(), ["validate", str(toml), "--json"])
    assert result.exit_code != 0
    data = json.loads(result.output)
    message = data["errors"][0]["message"]
    assert "•" not in message
    assert message.isascii()


def test_json_invalid_file(tmp_path: Path) -> None:
    toml = tmp_path / "bad.toml"
    toml.write_text(
        "[disciplines.drag]\ninputs = ['h']\noutputs = ['f']\n"
        "[disciplines.power]\ninputs = ['h']\noutputs = ['f']\n"  # double output
    )
    result = runner.invoke(get_app(), ["validate", str(toml), "--json"])
    assert result.exit_code != 0
    data = json.loads(result.output)
    assert data["success"] is False
    assert len(data["errors"]) > 0


def test_json_missing_file(tmp_path: Path) -> None:
    result = runner.invoke(
        get_app(), ["validate", str(tmp_path / "ghost.toml"), "--json"]
    )
    assert result.exit_code != 0
    data = json.loads(result.output)
    assert data["success"] is False
    assert data["errors"][0]["type"] == "file_not_found"


def test_json_resolve_error_no_toml(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(get_app(), ["validate", "--json"])
    assert result.exit_code != 0
    data = json.loads(result.output)
    assert data["success"] is False
    assert data["errors"][0]["type"] == "usage"


def test_json_and_quiet_are_mutually_exclusive(tmp_path: Path) -> None:
    toml = tmp_path / "problem.toml"
    toml.write_text(VALID_TOML)
    result = runner.invoke(get_app(), ["validate", str(toml), "--json", "--quiet"])
    assert result.exit_code != 0


# -- watch mode ----------------------------------------------------------------


def test_watch_reruns_on_change(tmp_path: Path) -> None:
    toml = tmp_path / "problem.toml"
    toml.write_text(VALID_TOML)
    con, out = _console()
    from gemseo_gantry.cli.validate import _run

    fake_changes = [frozenset([(1, str(toml))])]
    with patch("watchfiles.watch", return_value=iter(fake_changes)):
        rc = _run(toml, invocation=_inv(toml), watch=True, console=con, json_mode=False)
    assert rc == 0
    assert out.getvalue().count("✓") == 2


def test_watch_ctrl_c_exits_cleanly(tmp_path: Path) -> None:
    toml = tmp_path / "problem.toml"
    toml.write_text(VALID_TOML)
    con, _ = _console()
    from gemseo_gantry.cli.validate import _run

    with patch("watchfiles.watch", side_effect=KeyboardInterrupt):
        rc = _run(toml, invocation=_inv(toml), watch=True, console=con, json_mode=False)
    assert rc == 0


def test_watch_starts_even_when_initial_validation_fails(tmp_path: Path) -> None:
    toml = tmp_path / "bad.toml"
    toml.write_text(
        "[disciplines.drag]\ninputs=['h']\noutputs=['duty_cycle']\n"
        "[disciplines.power]\ninputs=['h']\noutputs=['duty_cycle']\n"
    )
    con, out = _console()
    from gemseo_gantry.cli.validate import _run

    fake_changes = [frozenset([(1, str(toml))])]
    with patch("watchfiles.watch", return_value=iter(fake_changes)):
        rc = _run(toml, invocation=_inv(toml), watch=True, console=con, json_mode=False)
    assert rc == 0
    assert "duty_cycle" in out.getvalue()


def test_watch_monitors_parent_directory_not_file(tmp_path: Path) -> None:
    toml = tmp_path / "problem.toml"
    toml.write_text(
        '[disciplines.drag]\ninputs = ["h"]\noutputs = ["f"]\n\n'
        '[[variables]]\nname = "h"\nunit = "m"\ndata_type = "float"\ndimension = 1\n\n'
        '[[variables]]\nname = "f"\nunit = "-"\ndata_type = "float"\ndimension = 1\n'
    )
    con, _ = _console()
    watched_first_arg = None

    def capture_watch(*args, **_kwargs):
        nonlocal watched_first_arg
        watched_first_arg = args[0] if args else None
        return iter([])

    from gemseo_gantry.cli.validate import _run

    with patch("watchfiles.watch", side_effect=capture_watch):
        _run(toml, invocation=_inv(toml), watch=True, console=con, json_mode=False)

    assert watched_first_arg == tmp_path


def test_watch_json_emits_ndjson(tmp_path: Path) -> None:
    toml = tmp_path / "problem.toml"
    toml.write_text(VALID_TOML)
    fake_changes = [frozenset([(1, str(toml))])]
    con, _ = _console()
    import contextlib
    import io

    from gemseo_gantry.cli.validate import _run

    buf = io.StringIO()
    with patch("watchfiles.watch", return_value=iter(fake_changes)):
        with contextlib.redirect_stdout(buf):
            _run(toml, invocation=_inv(toml), watch=True, console=con, json_mode=True)
    lines = [ln for ln in buf.getvalue().splitlines() if ln.strip()]
    assert len(lines) == 2  # initial + 1 watch event
    for line in lines:
        data = json.loads(line)
        assert data["success"] is True


_WARNING_TOML = (
    '[disciplines.drag]\ninputs = ["h"]\noutputs = ["f"]\n\n'
    '[disciplines.sink]\ninputs = ["f"]\noutputs = []\n\n'
    '[[variables]]\nname = "h"\nunit = "m"\ndata_type = "float"\ndimension = 1\n\n'
    '[[variables]]\nname = "f"\nunit = "-"\ndata_type = "float"\ndimension = 1\n'
)


def test_warnings_displayed_in_validate_output(tmp_path: Path) -> None:
    """A discipline with no outputs triggers a warning shown in validate output."""
    toml = tmp_path / "problem.toml"
    toml.write_text(_WARNING_TOML)
    con, out = _console()
    from gemseo_gantry.cli.validate import _run

    rc = _run(toml, invocation=_inv(toml), watch=False, console=con, json_mode=False)
    assert rc == 0
    assert "sink" in out.getvalue()
    assert "warning" in out.getvalue().lower() or "Warning" in out.getvalue()


def test_validate_output_escapes_brackets_in_messages(tmp_path: Path) -> None:
    """Square brackets in messages (e.g. '[[variables]]') must render literally,
    not be swallowed as rich markup."""
    toml = tmp_path / "problem.toml"
    toml.write_text(
        '[disciplines.drag]\ninputs = ["h"]\noutputs = ["f"]\n\n'
        '[[variables]]\nname = "h"\nunit = "m"\ndata_type = "float"\ndimension = 1\n\n'
        '[[variables]]\nname = "f"\nunit = "-"\ndata_type = "float"\ndimension = 1\n\n'
        '[[variables]]\nname = "orphan"\nunit = "-"\ndata_type = "float"\ndimension = 1\n'
    )
    con, out = _console()
    from gemseo_gantry.cli.validate import _run

    rc = _run(toml, invocation=_inv(toml), watch=False, console=con, json_mode=False)
    assert rc == 1
    assert "[[variables]]" in out.getvalue()


def test_watch_passes_stop_event_to_watchfiles(tmp_path: Path) -> None:
    import threading

    toml = tmp_path / "problem.toml"
    toml.write_text(VALID_TOML)
    con, _ = _console()
    captured_kwargs = {}

    def capture_watch(*_args, **kwargs):
        captured_kwargs.update(kwargs)
        return iter([])

    from gemseo_gantry.cli.validate import _run

    with patch("watchfiles.watch", side_effect=capture_watch):
        with patch(
            "gemseo_gantry.cli.validate._start_quit_key_listener", return_value=None
        ):
            _run(toml, invocation=_inv(toml), watch=True, console=con, json_mode=False)

    assert isinstance(captured_kwargs.get("stop_event"), threading.Event)


def test_is_quit_key_matches_q_and_case_variant() -> None:
    from gemseo_gantry.cli.validate import _is_quit_key

    assert _is_quit_key("q")
    assert _is_quit_key("Q")


def test_is_quit_key_matches_esc() -> None:
    import readchar

    from gemseo_gantry.cli.validate import _is_quit_key

    assert _is_quit_key(readchar.key.ESC)


def test_is_quit_key_rejects_other_keys() -> None:
    from gemseo_gantry.cli.validate import _is_quit_key

    assert not _is_quit_key("a")
    assert not _is_quit_key("\r")


def test_watch_stops_listener_thread_via_stop_event(tmp_path: Path) -> None:
    """stop_event is set in `finally`, which the listener thread polls."""
    toml = tmp_path / "problem.toml"
    toml.write_text(VALID_TOML)
    con, _ = _console()
    captured_stop_event = {}

    def capture_watch(*_args, **kwargs):
        captured_stop_event["event"] = kwargs.get("stop_event")
        return iter([])

    from gemseo_gantry.cli.validate import _run

    with patch("watchfiles.watch", side_effect=capture_watch):
        with patch(
            "gemseo_gantry.cli.validate._start_quit_key_listener", return_value=None
        ):
            rc = _run(
                toml, invocation=_inv(toml), watch=True, console=con, json_mode=False
            )

    assert rc == 0
    assert captured_stop_event["event"].is_set()


def test_watch_continues_when_listener_unavailable(tmp_path: Path) -> None:
    """If stdin isn't a tty (e.g. headless CI), watch still works via Ctrl+C."""
    toml = tmp_path / "problem.toml"
    toml.write_text(VALID_TOML)
    con, _ = _console()

    from gemseo_gantry.cli.validate import _run

    with patch("watchfiles.watch", side_effect=KeyboardInterrupt):
        with patch(
            "gemseo_gantry.cli.validate._start_quit_key_listener", return_value=None
        ):
            rc = _run(
                toml, invocation=_inv(toml), watch=True, console=con, json_mode=False
            )

    assert rc == 0


def test_start_quit_key_listener_returns_none_when_stdin_not_a_tty(
    monkeypatch,
) -> None:
    """Non-interactive stdin (e.g. redirected input, headless CI) degrades to
    Ctrl+C only, instead of trying to read keys from a non-terminal stream."""
    import threading

    from gemseo_gantry.cli import validate

    monkeypatch.setattr(validate.sys.stdin, "isatty", lambda: False)

    assert validate._start_quit_key_listener(threading.Event()) is None


def test_quit_key_listener_sets_stop_event_on_q(monkeypatch) -> None:
    """The background thread sets stop_event once a quit key is read.

    Mocks os.read/termios/tty rather than readchar's read functions, since
    the listener deliberately bypasses readchar's I/O (it disables ISIG as a
    side effect - see _start_quit_key_listener's docstring) in favor of the
    stdlib's tty.setcbreak plus a raw os.read loop.
    """
    import threading

    from gemseo_gantry.cli import validate

    monkeypatch.setattr(validate.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(validate.sys.stdin, "fileno", lambda: 0)
    monkeypatch.setattr("termios.tcgetattr", lambda fd: [])
    monkeypatch.setattr("termios.tcsetattr", lambda fd, when, attrs: None)
    monkeypatch.setattr("tty.setcbreak", lambda fd: None)
    monkeypatch.setattr("os.read", lambda fd, n: b"q")

    stop_event = threading.Event()
    thread = validate._start_quit_key_listener(stop_event)
    assert thread is not None
    assert stop_event.wait(timeout=2)
    thread.join(timeout=2)


def test_validate_watch_filter_is_applied(tmp_path: Path) -> None:
    """The _only_this_file callback is invoked by watchfiles.watch (line 27)."""
    import watchfiles

    toml = tmp_path / "problem.toml"
    toml.write_text(VALID_TOML)

    def fake_watch(_, watch_filter, **_kwargs):
        # Call the filter exactly once to cover the callback body
        watch_filter(watchfiles.Change.modified, str(toml))
        raise KeyboardInterrupt

    con, _ = _console()
    from gemseo_gantry.cli.validate import _run

    with patch("watchfiles.watch", fake_watch):
        rc = _run(toml, invocation=_inv(toml), watch=True, console=con, json_mode=False)

    assert rc == 0


def test_json_output_includes_warnings(tmp_path: Path) -> None:
    """Warnings are emitted in the JSON output, not just rich mode."""
    toml = tmp_path / "problem.toml"
    toml.write_text(_WARNING_TOML)
    result = runner.invoke(get_app(), ["validate", str(toml), "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["success"] is True
    assert len(data["warnings"]) == 1
    assert data["warnings"][0]["type"] == "validation"
    assert "sink" in data["warnings"][0]["message"]
