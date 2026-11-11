from gemseo_gantry import artifacts
from gemseo_gantry.cli import _result


def test_cli_result_reexports_the_neutral_enums():
    assert _result.ArtifactKind is artifacts.ArtifactKind
    assert _result.ArtifactStatus is artifacts.ArtifactStatus
