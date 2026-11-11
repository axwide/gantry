# pyright: reportMissingImports=false
from pathlib import Path

from disciplines.Aerodynamics import Aerodynamics
from disciplines.Mission import Mission
from disciplines.Propulsion import Propulsion
from disciplines.Structure import Structure
from gemseo.formulations.bilevel_bcd_settings import BiLevel_BCD_Settings
from gemseo.formulations.mdf_settings import MDF_Settings
from gemseo.settings.opt import NLOPT_COBYLA_Settings, SLSQP_Settings
from lib.AerodynamicsScenario import (
    AerodynamicsScenarioDisciplines,
    construct_AerodynamicsScenario,
)
from lib.PropulsionScenario import (
    PropulsionScenarioDisciplines,
    construct_PropulsionScenario,
)
from lib.StructureScenario import (
    StructureScenarioDisciplines,
    construct_StructureScenario,
)
from lib.SystemScenario import (
    SystemScenarioDisciplines,
    SystemScenarioSubScenarios,
    construct_SystemScenario,
)


def execute_SystemScenario():
    structure = construct_StructureScenario(
        disciplines=StructureScenarioDisciplines(Structure=Structure()),
        formulation_settings_model=MDF_Settings(),
    )
    structure.set_differentiation_method("finite_differences")
    structure.set_algorithm(SLSQP_Settings(max_iter=30))

    aerodynamics = construct_AerodynamicsScenario(
        disciplines=AerodynamicsScenarioDisciplines(Aerodynamics=Aerodynamics()),
        formulation_settings_model=MDF_Settings(),
    )
    aerodynamics.set_differentiation_method("finite_differences")
    aerodynamics.set_algorithm(SLSQP_Settings(max_iter=30))

    propulsion = construct_PropulsionScenario(
        disciplines=PropulsionScenarioDisciplines(Propulsion=Propulsion()),
        formulation_settings_model=MDF_Settings(),
    )
    propulsion.set_differentiation_method("finite_differences")
    propulsion.set_algorithm(SLSQP_Settings(max_iter=30))

    system = construct_SystemScenario(
        disciplines=SystemScenarioDisciplines(Mission=Mission()),
        sub_scenarios=SystemScenarioSubScenarios(
            StructureScenario=structure,
            AerodynamicsScenario=aerodynamics,
            PropulsionScenario=propulsion,
        ),
        formulation_settings_model=BiLevel_BCD_Settings(),
    )
    system.set_differentiation_method("finite_differences")
    system.execute(algo_settings_model=NLOPT_COBYLA_Settings(max_iter=50))
    return system


def main() -> None:
    system = execute_SystemScenario()
    system.save_optimization_history(Path(__file__).parent / "SystemScenario.h5")


if __name__ == "__main__":
    main()
