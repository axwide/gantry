from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console

from ..examples.narration import NarrationStep, build_narration
from ..examples.registry import Example
from ..examples.runner import ExampleArtifact, _fill_finished_files
from ._render import _narration_panel, live_header, render_file_snippet

_MAX_STREAMED_LINES = 40


def _run_streamed(
    argv: list[str], cwd: Path, console: Console, header: str, *, bookend: bool = False
) -> int:
    """Run a subprocess under a header rule, streaming combined output live.

    Output is capped at ``_MAX_STREAMED_LINES`` lines; excess is replaced with
    a single "[… N lines trimmed]" notice. When *bookend* is True a closing
    rule + blank line are printed after the subprocess finishes, visually
    bracketing raw output that has no trailing rich panel of its own (e.g. the
    executor and post-processor scripts).
    """
    live_header(header, console)
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    env["PYTHONPATH"] = str(cwd)
    proc = subprocess.Popen(
        argv,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    assert proc.stdout is not None
    emitted = 0
    trimmed = 0
    for line in proc.stdout:
        if emitted < _MAX_STREAMED_LINES:
            console.out(line.rstrip("\n"), highlight=False)
            emitted += 1
        else:
            trimmed += 1
    if trimmed:
        console.out(f"[… {trimmed} lines trimmed]", highlight=False)
    rc = proc.wait()
    if bookend:
        console.rule()
        console.print()
    return rc


@dataclass
class _Stage:
    step: NarrationStep
    action: Callable[[], list[str]]  # returns rel-to-target paths produced
    snippet: tuple[str, str] | None = None  # (rel_path, lexer)
    in_summary: bool = False
    show_files: bool = False  # True only for in-process stages with no subprocess output and no snippet


def _gantry(*args: str) -> list[str]:
    return [sys.executable, "-m", "gemseo_gantry", *args]


def _rels(target: Path, paths: list[Path]) -> list[str]:
    return sorted(str(p.relative_to(target)) for p in paths if p.is_file())


def _build_stages(example: Example, target: Path, console: Console) -> list[_Stage]:
    name = example.name
    executor = example.executor
    toml_name = f"{name}.toml"
    steps = build_narration(example)  # [intro, s1..s7, outro]

    def write_toml() -> list[str]:
        _run_streamed(
            _gantry("example", name, "--dump-toml"),
            target,
            console,
            f"gantry example {name} --dump-toml",
        )
        return [toml_name] if (target / toml_name).is_file() else []

    def validate_toml() -> list[str]:
        _run_streamed(
            _gantry("validate", toml_name),
            target,
            console,
            f"gantry validate {toml_name}",
        )
        return []

    def build_lib() -> list[str]:
        _run_streamed(
            _gantry("build", toml_name),
            target,
            console,
            f"gantry build {toml_name}",
        )
        return _rels(
            target,
            list((target / "lib").rglob("*")) if (target / "lib").is_dir() else [],
        )

    def diagrams() -> list[str]:
        _run_streamed(_gantry("diagram", "n2"), target, console, "gantry diagram n2")
        _run_streamed(
            _gantry("diagram", "xdsm"), target, console, "gantry diagram xdsm"
        )
        return _rels(
            target,
            list((target / "diagrams").rglob("*"))
            if (target / "diagrams").is_dir()
            else [],
        )

    def scaffold() -> list[str]:
        _run_streamed(
            _gantry("scaffold", toml_name),
            target,
            console,
            f"gantry scaffold {toml_name}",
        )
        stubs = list(target.glob("disciplines/*_scaffold.py"))
        stubs += (
            list((target / "scenarios").rglob("*"))
            if (target / "scenarios").is_dir()
            else []
        )
        return _rels(target, stubs)

    def fill() -> list[str]:
        arts = _fill_finished_files(example, target)
        return _rels(target, [a.path for a in arts])

    def run_executor() -> list[str]:
        _run_streamed(
            [sys.executable, executor],
            target,
            console,
            f"uv run {executor}",
            bookend=True,
        )
        stem = Path(executor).stem
        return _rels(
            target,
            [target / f"{stem}.h5"] if (target / f"{stem}.h5").is_file() else [],
        )

    def postprocess() -> list[str]:
        _run_streamed(
            [sys.executable, "postprocess.py"],
            target,
            console,
            "uv run postprocess.py",
            bookend=True,
        )
        return []

    def noop() -> list[str]:
        return []

    return [
        _Stage(steps[0], noop),  # intro
        _Stage(steps[1], write_toml, snippet=(toml_name, "toml"), in_summary=True),
        _Stage(steps[2], validate_toml),
        _Stage(steps[3], build_lib, in_summary=True),
        _Stage(steps[4], diagrams, in_summary=True),
        _Stage(steps[5], scaffold, snippet=("__scaffold_stub__", "python")),
        _Stage(
            steps[6],
            fill,
            snippet=("__discipline_file__", "python"),
            in_summary=True,
            show_files=True,
        ),
        _Stage(steps[7], run_executor),
        _Stage(steps[8], postprocess),
        _Stage(steps[9], noop),  # outro
    ]


def run_walkthrough(
    example: Example, target: Path, console: Console
) -> list[ExampleArtifact]:
    """Drive the interactive --explain walkthrough; return summary artifacts."""
    target = Path(target)
    target.mkdir(parents=True, exist_ok=True)
    interactive = sys.stdin.isatty() and sys.stdout.isatty()
    stages = _build_stages(example, target, console)
    summary_rels: list[str] = []

    try:
        for index, stage in enumerate(stages):
            if interactive and index > 0:
                console.input("[dim]Press Enter to continue…[/dim]")
            # show_files stages are in-process (no console output), so we can run the
            # action early to attach produced paths inside the narration panel.
            # Other stages call _run_streamed, which streams to the console; those must
            # run after the panel so subprocess output follows the narration, not precedes it.
            produced: list[str] = []
            if stage.show_files:
                produced = stage.action()
                stage.step.artifacts = produced
            console.print(_narration_panel(stage.step))
            console.print()
            if not stage.show_files:
                produced = stage.action()
            _maybe_snippet(stage, target, console)
            if stage.in_summary:
                summary_rels.extend(produced)
    except (KeyboardInterrupt, EOFError):
        pass

    return _to_artifacts(target, sorted(set(summary_rels)))


def _maybe_snippet(stage: _Stage, target: Path, console: Console) -> None:
    if stage.snippet is None:
        return
    rel, lexer = stage.snippet
    if rel == "__scaffold_stub__":
        stubs = sorted(target.glob("disciplines/*_scaffold.py"))
        if stubs:
            render_file_snippet(
                stubs[0], lexer, console, lines=30, title=f"{stubs[0].name} (snippet)"
            )
            console.print()
        return
    if rel == "__discipline_file__":
        real = sorted(
            f
            for f in target.glob("disciplines/*.py")
            if not f.name.endswith("_scaffold.py") and f.name != "__init__.py"
        )
        if real:
            render_file_snippet(
                real[0], lexer, console, lines=30, title=f"{real[0].name} (snippet)"
            )
            console.print()
        return
    path = target / rel
    if path.is_file():
        render_file_snippet(path, lexer, console, lines=30, title=f"{rel} (snippet)")
        console.print()


def _to_artifacts(target: Path, rels: list[str]) -> list[ExampleArtifact]:
    return [ExampleArtifact(path=target / rel, kind="example") for rel in rels]
