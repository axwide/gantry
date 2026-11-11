from pathlib import Path
from typing import Sequence, cast

from gemseo import generate_n2_plot, generate_xdsm
from gemseo.core.discipline import Discipline
from gemseo.scenarios.base_scenario import BaseScenario


def generate_coupling_diagrams(scenario: BaseScenario, save_folder: Path) -> None:
    save_folder.mkdir(exist_ok=True)
    generate_n2_plot(
        cast(Sequence[Discipline], scenario.disciplines),
        file_path=save_folder / "n2.png",
    )
    generate_xdsm(scenario, directory_path=save_folder)  # type: ignore[arg-type]  # XDSMizer handles BaseScenario explicitly (xdsmizer.py:27); GEMSEO annotation defect
