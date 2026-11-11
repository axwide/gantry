from gemseo_gantry.artifacts import ArtifactKind, ArtifactStatus, GeneratedArtifact
from gemseo_gantry.generator.lib_generator import (
    generate_design_space,
    generate_discipline_bases,
    generate_discipline_grammars,
    generate_discipline_io,
    generate_scenario,
    generate_variables,
)


def test_helpers_return_written_artifacts(problem_def, tmp_path):
    assert generate_variables(problem_def, tmp_path) == [
        GeneratedArtifact(tmp_path / "variables.py", ArtifactKind.VARIABLES)
    ]
    assert generate_design_space(problem_def, tmp_path) == [
        GeneratedArtifact(tmp_path / "design_space.csv", ArtifactKind.DESIGN_SPACE)
    ]

    grammars = generate_discipline_grammars(problem_def, tmp_path)
    assert grammars == [
        GeneratedArtifact(
            tmp_path / f"{d.name}_grammar.py", ArtifactKind.DISCIPLINE_GRAMMAR
        )
        for d in problem_def.disciplines
    ]

    ios = generate_discipline_io(problem_def, tmp_path)
    assert ios == [
        GeneratedArtifact(tmp_path / f"{d.name}_io.py", ArtifactKind.DISCIPLINE_IO)
        for d in problem_def.disciplines
    ]

    bases = generate_discipline_bases(problem_def, tmp_path)
    assert bases == [
        GeneratedArtifact(tmp_path / f"{d.name}_base.py", ArtifactKind.DISCIPLINE_BASE)
        for d in problem_def.disciplines
    ]

    scenarios = generate_scenario(problem_def, tmp_path)
    assert scenarios == [
        GeneratedArtifact(tmp_path / f"{s.name}.py", ArtifactKind.SCENARIO)
        for s in problem_def.scenarios
    ]

    # all lib helpers report WRITTEN status
    for artifact in [*grammars, *ios, *bases, *scenarios]:
        assert artifact.status is ArtifactStatus.WRITTEN
