from pathlib import Path

from gemseo_gantry.artifacts import ArtifactKind, ArtifactStatus, GeneratedArtifact


def test_generated_artifact_defaults_to_written():
    ga = GeneratedArtifact(path=Path("lib/variables.py"), kind=ArtifactKind.VARIABLES)
    assert ga.path == Path("lib/variables.py")
    assert ga.kind is ArtifactKind.VARIABLES
    assert ga.status is ArtifactStatus.WRITTEN


def test_kind_and_status_string_values():
    assert ArtifactKind.DISCIPLINE_GRAMMAR == "discipline_grammar"
    assert ArtifactStatus.SKIPPED == "skipped"
