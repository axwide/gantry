from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures"


@pytest.fixture
def vleo_problem():
    from gemseo_gantry.parser.toml_parser import parse_toml

    return parse_toml(FIXTURES_DIR / "vleo.toml")


def test_generate_n2_creates_file(tmp_path, vleo_problem):
    from gemseo_gantry.diagram import generate_n2

    generate_n2(vleo_problem, tmp_path)

    assert (tmp_path / "n2.pdf").exists()


def test_generate_xdsm_creates_file(tmp_path, vleo_problem):
    from gemseo_gantry.diagram import generate_xdsm

    generate_xdsm(vleo_problem, tmp_path)

    assert (tmp_path / "xdsm.html").exists()


def test_generate_xdsm_raises_without_scenario(tmp_path):
    from gemseo_gantry.diagram import generate_xdsm
    from gemseo_gantry.model.data_model import Discipline, ProblemDefinition

    problem = ProblemDefinition(
        disciplines=[Discipline(name="Drag", inputs=["altitude"], outputs=["drag"])],
        variables=[],
    )

    with pytest.raises(ValueError, match="no scenarios"):
        generate_xdsm(problem, tmp_path)
