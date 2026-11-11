# pyright: reportMissingImports=false
from gemseo.problems.mdo.sobieski.disciplines import SobieskiPropulsion
from gemseo.typing import StrKeyMapping
from lib.Propulsion_base import PropulsionBase
from lib.Propulsion_io import PropulsionOutputs


class Propulsion(PropulsionBase):
    def __init__(self) -> None:
        super().__init__()
        self._impl = SobieskiPropulsion()

    def _run(self, input_data: StrKeyMapping) -> StrKeyMapping | None:
        out = self._impl.execute(input_data)
        return PropulsionOutputs(
            y_3=out["y_3"],
            y_31=out["y_31"],
            y_32=out["y_32"],
            y_34=out["y_34"],
            g_3=out["g_3"],
        )
