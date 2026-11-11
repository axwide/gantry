# pyright: reportMissingImports=false
from gemseo.problems.mdo.sobieski.disciplines import SobieskiStructure
from gemseo.typing import StrKeyMapping
from lib.Structure_base import StructureBase
from lib.Structure_io import StructureOutputs


class Structure(StructureBase):
    def __init__(self) -> None:
        super().__init__()
        self._impl = SobieskiStructure()

    def _run(self, input_data: StrKeyMapping) -> StrKeyMapping | None:
        out = self._impl.execute(input_data)
        return StructureOutputs(
            y_1=out["y_1"],
            y_11=out["y_11"],
            y_12=out["y_12"],
            y_14=out["y_14"],
            g_1=out["g_1"],
        )
