# pyright: reportMissingImports=false
from pathlib import Path

from disciplines.Sellar1 import Sellar1
from disciplines.Sellar2 import Sellar2
from disciplines.SellarSystem import SellarSystem
from gemseo.formulations.mdf_settings import MDF_Settings
from gemseo.settings.opt import NLOPT_COBYLA_Settings
from lib.Sellar import SellarDisciplines, construct_Sellar


def execute_Sellar():
    scenario = construct_Sellar(
        disciplines=SellarDisciplines(
            Sellar1=Sellar1(),
            Sellar2=Sellar2(),
            SellarSystem=SellarSystem(),
        ),
        formulation_settings_model=MDF_Settings(),
    )

    scenario.execute(algo_settings_model=NLOPT_COBYLA_Settings(max_iter=100))
    return scenario


def main() -> None:
    scenario = execute_Sellar()
    scenario.save_optimization_history(Path(__file__).parent / "Sellar.h5")


if __name__ == "__main__":
    main()
