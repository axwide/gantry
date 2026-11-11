# pyright: reportMissingImports=false
from gemseo.problems.mdo.sobieski.disciplines import SobieskiAerodynamics
from gemseo.typing import StrKeyMapping
from lib.Aerodynamics_base import AerodynamicsBase
from lib.Aerodynamics_io import AerodynamicsOutputs


class Aerodynamics(AerodynamicsBase):
    def __init__(self) -> None:
        super().__init__()
        self._impl = SobieskiAerodynamics()

    def _run(self, input_data: StrKeyMapping) -> StrKeyMapping | None:
        out = self._impl.execute(input_data)
        return AerodynamicsOutputs(
            y_2=out["y_2"],
            y_21=out["y_21"],
            y_23=out["y_23"],
            y_24=out["y_24"],
            g_2=out["g_2"],
        )
