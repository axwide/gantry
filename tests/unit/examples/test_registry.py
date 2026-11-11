import tomllib

import pytest

from gemseo_gantry.examples.registry import (
    UnknownExampleError,
    available_names,
    get_example,
)


def test_sellar_is_registered():
    assert "sellar" in available_names()


def test_get_example_returns_sellar():
    ex = get_example("sellar")
    assert ex.name == "sellar"
    assert ex.root.is_dir()
    assert (ex.root / "sellar.toml").is_file()
    assert ex.expected_objective == pytest.approx(3.18, abs=0.3)


def test_unknown_example_raises_with_available():
    with pytest.raises(UnknownExampleError) as exc:
        get_example("nope")
    assert exc.value.name == "nope"
    assert "sellar" in exc.value.available


def test_problem_toml_parses_as_problem_definition():
    from gemseo_gantry.parser.toml_parser import parse_toml

    ex = get_example("sellar")
    problem = parse_toml(ex.root / "sellar.toml")
    assert {d.name for d in problem.disciplines} == {
        "Sellar1",
        "Sellar2",
        "SellarSystem",
    }
    assert len(problem.scenarios) == 1


def test_problem_toml_is_valid_toml():
    ex = get_example("sellar")
    tomllib.loads((ex.root / "sellar.toml").read_text(encoding="utf-8"))


def test_sellar_has_execution_metadata():
    ex = get_example("sellar")
    assert ex.executor == "execute_Sellar.py"
    assert ex.objective_tolerance == pytest.approx(0.3)
    assert ex.physics_note
    assert ex.run_note
