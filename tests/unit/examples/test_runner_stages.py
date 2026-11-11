from __future__ import annotations

import pytest

from gemseo_gantry.examples.registry import get_example
from gemseo_gantry.examples.runner import (
    _build_lib,
    _fill_finished_files,
    _write_toml,
    generate_diagrams,
    generate_example,
)
from gemseo_gantry.parser.toml_parser import parse_toml


def test_write_toml_copies_definition(tmp_path):
    ex = get_example("sellar")
    arts = _write_toml(ex, tmp_path)
    assert (tmp_path / "sellar.toml").is_file()
    assert [a.kind for a in arts] == ["problem_definition"]


def test_build_lib_emits_package(tmp_path):
    ex = get_example("sellar")
    _write_toml(ex, tmp_path)
    problem = parse_toml(tmp_path / "sellar.toml")
    arts = _build_lib(problem, tmp_path)
    assert (tmp_path / "lib").is_dir()
    assert arts  # generate_lib reported files
    assert all((tmp_path / "lib") in a.path.parents for a in arts)


def test_fill_finished_files_drops_finished_and_cleans_stubs(tmp_path):
    ex = get_example("sellar")
    _write_toml(ex, tmp_path)
    # Simulate scaffold leftovers that fill must remove.
    (tmp_path / "disciplines").mkdir()
    (tmp_path / "disciplines" / "Sellar1_scaffold.py").write_text(
        "stub", encoding="utf-8"
    )
    (tmp_path / "scenarios").mkdir()
    (tmp_path / "scenarios" / "load_Sellar.py").write_text("stub", encoding="utf-8")

    arts = _fill_finished_files(ex, tmp_path)

    disc = (tmp_path / "disciplines" / "Sellar1.py").read_text(encoding="utf-8")
    assert "np.sqrt" in disc  # finished physics
    assert not list(tmp_path.glob("disciplines/*_scaffold.py"))  # stubs gone
    assert not (tmp_path / "scenarios").exists()  # scaffold scenarios dir gone
    assert (tmp_path / "execute_Sellar.py").is_file()
    assert (tmp_path / "postprocess.py").is_file()
    kinds = {a.kind for a in arts}
    assert {"discipline", "executor", "postprocessor"} <= kinds


@pytest.mark.slow
def test_generate_diagrams_writes_into_diagrams_dir(tmp_path):
    ex = get_example("sellar")
    _write_toml(ex, tmp_path)
    problem = parse_toml(tmp_path / "sellar.toml")
    arts = generate_diagrams(problem, tmp_path)
    assert (tmp_path / "diagrams").is_dir()
    names = {a.path.name for a in arts}
    assert any(n.startswith("n2") for n in names)
    assert "xdsm.html" in names
    assert all(a.kind == "diagram" for a in arts)


def test_generate_example_skips_scaffold_no_execution(tmp_path, monkeypatch):
    # Avoid the heavy GEMSEO diagram path in this structural test.
    monkeypatch.setattr(
        "gemseo_gantry.examples.runner.generate_diagrams",
        lambda problem, target: [],
    )
    ex = get_example("sellar")
    run = generate_example(ex, tmp_path / "sellar")
    files = {p.name for p in (tmp_path / "sellar").rglob("*") if p.is_file()}
    assert "sellar.toml" in files
    assert "Sellar1.py" in files
    assert not any(n.endswith("_scaffold.py") for n in files)  # scaffold skipped
    assert "Sellar.h5" not in files  # no execution
    assert len(run.narration) == 10
