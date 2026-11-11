from pathlib import Path

from gemseo_gantry.examples.narration import NarrationStep, build_narration
from gemseo_gantry.examples.registry import Example, get_example


def _sentinel_example() -> Example:
    return Example(
        name="demo",
        summary="s",
        root=Path("/tmp"),
        intro="i",
        outro="o",
        expected_objective=0.0,
        executor="execute_RootScenario.py",  # not "execute_Demo.py"
        objective_tolerance=1.0,
        physics_note="PHYSICS_SENTINEL_NOTE",
        run_note="RUN_SENTINEL_NOTE",
    )


def test_narration_uses_example_notes():
    steps = build_narration(_sentinel_example())
    bodies = " ".join(s.body for s in steps)
    assert "PHYSICS_SENTINEL_NOTE" in bodies
    assert "RUN_SENTINEL_NOTE" in bodies
    commands = [s.command for s in steps if s.command]
    assert any("execute_RootScenario.py" in c for c in commands)


def test_build_narration_has_intro_eight_steps_outro():
    steps = build_narration(get_example("sellar"))
    assert all(isinstance(s, NarrationStep) for s in steps)
    # intro + 8 workflow steps + outro
    assert len(steps) == 10


def test_narration_mentions_validate_build_scaffold_and_diagrams():
    titles = [s.title.lower() for s in build_narration(get_example("sellar"))]
    joined = " ".join(titles)
    assert "validate" in joined
    assert "build" in joined
    assert "scaffold" in joined
    assert "diagram" in joined


def test_narration_attaches_artifacts_to_diagram_step():
    steps = build_narration(
        get_example("sellar"), artifacts_by_step={4: ["diagrams/n2.pdf"]}
    )
    # workflow step 4 == index 4 in the list (0=intro, 1=step1, 2=step2, 3=step3, 4=step4)
    assert "diagrams/n2.pdf" in steps[4].artifacts


def test_run_step_command_references_scenario():
    steps = build_narration(get_example("sellar"))
    commands = [s.command for s in steps if s.command]
    assert any("execute_Sellar" in c for c in commands)
    assert any("postprocess" in c for c in commands)
