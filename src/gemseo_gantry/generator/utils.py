from collections.abc import Sequence
from pathlib import Path
from typing import cast

from gemseo import generate_n2_plot, generate_xdsm
from gemseo.discipline import Discipline
from gemseo.scenario import MDOScenario


def generate_coupling_diagrams(scenario: MDOScenario, save_folder: Path) -> None:
    save_folder.mkdir(exist_ok=True)
    generate_n2_plot(
        cast(Sequence[Discipline], scenario.disciplines),
        file_path=save_folder / "n2.png",
    )
    generate_xdsm(scenario, directory_path=save_folder)  # type: ignore[arg-type]  # XDSMizer handles MDOScenario explicitly (xdsmizer.py:27); GEMSEO annotation defect
