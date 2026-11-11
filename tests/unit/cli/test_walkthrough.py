from __future__ import annotations

import io
import sys

import pytest
from rich.console import Console

from gemseo_gantry.cli import _walkthrough
from gemseo_gantry.cli._render import live_header, render_file_snippet
from gemseo_gantry.examples.registry import get_example


def _console() -> Console:
    return Console(file=io.StringIO(), width=100)


def test_render_file_snippet_truncates_to_lines(tmp_path):
    f = tmp_path / "sample.py"
    f.write_text("\n".join(f"line{i}" for i in range(40)), encoding="utf-8")
    console = _console()
    render_file_snippet(f, "python", console, lines=5)
    out = console.file.getvalue()
    assert "line0" in out
    assert "line4" in out
    assert "line39" not in out  # truncated


def test_live_header_shows_command(tmp_path):
    console = _console()
    live_header("gantry build sellar.toml", console)
    out = console.file.getvalue()
    assert "gantry build sellar.toml" in out


class _FakeStream:
    def __init__(self, tty: bool) -> None:
        self._tty = tty

    def isatty(self) -> bool:
        return self._tty


def _patch_subprocess(monkeypatch, calls):
    def fake_run(argv, cwd, console, header, **kwargs):
        calls.append(header)
        if "--dump-toml" in header:
            # simulate what the real subprocess writes so file-tracking tests pass
            cwd.mkdir(parents=True, exist_ok=True)
            (cwd / f"{cwd.name}.toml").write_text("[test]", encoding="utf-8")
        return 0

    monkeypatch.setattr(_walkthrough, "_run_streamed", fake_run)


def _patch_tty(monkeypatch, stdin_tty, stdout_tty):
    monkeypatch.setattr(_walkthrough.sys, "stdin", _FakeStream(stdin_tty))
    monkeypatch.setattr(_walkthrough.sys, "stdout", _FakeStream(stdout_tty))


def test_walkthrough_runs_all_stage_commands(monkeypatch, tmp_path):
    calls: list[str] = []
    _patch_subprocess(monkeypatch, calls)
    _patch_tty(monkeypatch, False, False)  # non-TTY: no pauses
    console = _console()

    arts = run_helper(tmp_path, console)

    joined = " ".join(calls)
    assert "--dump-toml" in joined
    assert "gantry validate" in joined
    assert "gantry build" in joined
    assert "gantry diagram n2" in joined
    assert "gantry diagram xdsm" in joined
    assert "gantry scaffold" in joined
    assert "execute_Sellar.py" in joined
    assert "postprocess.py" in joined
    # summary excludes scaffold stubs and the .h5
    paths = {a.path.name for a in arts}
    assert "sellar.toml" in paths
    assert "Sellar1.py" in paths
    assert not any(n.endswith("_scaffold.py") for n in paths)
    assert "Sellar.h5" not in paths


def run_helper(tmp_path, console):
    from gemseo_gantry.cli._walkthrough import run_walkthrough  # noqa: PLC0415

    return run_walkthrough(get_example("sellar"), tmp_path / "sellar", console)


def test_walkthrough_progressive_file_appearance(monkeypatch, tmp_path):
    # build/scaffold are subprocesses (stubbed no-op); toml + fill are real file ops.
    _patch_subprocess(monkeypatch, [])
    _patch_tty(monkeypatch, False, False)
    target = tmp_path / "sellar"
    console = _console()
    assert not (target / "sellar.toml").exists()
    run_helper(tmp_path, console)
    assert (target / "sellar.toml").is_file()  # written by toml stage
    assert (target / "disciplines" / "Sellar1.py").is_file()  # written by fill stage


def test_walkthrough_pauses_n_minus_one_in_tty(monkeypatch, tmp_path):
    _patch_subprocess(monkeypatch, [])
    _patch_tty(monkeypatch, True, True)
    console = _console()
    pauses: list[str] = []
    monkeypatch.setattr(console, "input", lambda prompt="": pauses.append(prompt) or "")
    run_helper(tmp_path, console)
    # 10 narration stages -> 9 gaps -> 9 pauses
    assert len(pauses) == 9


def test_walkthrough_never_pauses_when_not_tty(monkeypatch, tmp_path):
    _patch_subprocess(monkeypatch, [])
    _patch_tty(monkeypatch, True, False)  # stdout not a tty
    console = _console()

    def _boom(prompt: str = "") -> str:
        raise AssertionError("must not pause when not a TTY")

    monkeypatch.setattr(console, "input", _boom)
    run_helper(tmp_path, console)  # must not raise


@pytest.mark.parametrize("exc", [KeyboardInterrupt, EOFError])
def test_walkthrough_aborts_cleanly_on_interrupt(monkeypatch, tmp_path, exc):
    _patch_subprocess(monkeypatch, [])
    _patch_tty(monkeypatch, True, True)
    console = _console()

    def _raise_second(prompt: str = "") -> str:
        _raise_second.n += 1  # type: ignore[attr-defined]
        if _raise_second.n >= 2:  # type: ignore[attr-defined]
            raise exc
        return ""

    _raise_second.n = 0  # type: ignore[attr-defined]
    monkeypatch.setattr(console, "input", _raise_second)
    # Must return normally (not propagate); partial generation is fine on disk.
    run_helper(tmp_path, console)


def test_walkthrough_continues_on_subprocess_failure(monkeypatch, tmp_path):
    def fail_run(argv, cwd, console, header, **kwargs):
        return 1  # non-zero, must be non-fatal

    monkeypatch.setattr(_walkthrough, "_run_streamed", fail_run)
    _patch_tty(monkeypatch, False, False)
    console = _console()
    arts = run_helper(tmp_path, console)  # must not raise
    # fill stage is in-process, so it still runs regardless of subprocess failures
    assert any(a.path.name == "Sellar1.py" for a in arts)


def test_walkthrough_renders_scaffold_stub_snippet(monkeypatch, tmp_path):
    # The scaffold subprocess is faked to drop a stub so the stub snippet renders.
    # (The TOML snippet at step 1 is already exercised by every run_helper call,
    # since the toml stage writes a real file.)
    def fake_run(argv, cwd, console, header, **kwargs):
        if "scaffold" in header:
            (tmp_path / "sellar" / "disciplines").mkdir(parents=True, exist_ok=True)
            (tmp_path / "sellar" / "disciplines" / "Sellar1_scaffold.py").write_text(
                "class Sellar1Scaffold:\n    pass\n", encoding="utf-8"
            )
        return 0

    monkeypatch.setattr(_walkthrough, "_run_streamed", fake_run)
    _patch_tty(monkeypatch, False, False)
    console = _console()
    run_helper(tmp_path, console)
    assert "Sellar1Scaffold" in console.file.getvalue()  # the stub snippet


def test_run_streamed_streams_real_subprocess(tmp_path):
    from gemseo_gantry.cli._walkthrough import _run_streamed

    console = _console()
    code = _run_streamed(
        [sys.executable, "-c", "print('hello-from-subprocess')"],
        cwd=tmp_path,
        console=console,
        header="demo",
    )
    assert code == 0
    assert "hello-from-subprocess" in console.file.getvalue()
