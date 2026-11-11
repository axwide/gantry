# pyright: reportMissingImports=false
from gemseo.problems.mdo.sobieski.disciplines import SobieskiMission
from gemseo.typing import StrKeyMapping
from lib.Mission_base import MissionBase
from lib.Mission_io import MissionOutputs


class Mission(MissionBase):
    def __init__(self) -> None:
        super().__init__()
        self._impl = SobieskiMission()

    def _run(self, input_data: StrKeyMapping) -> StrKeyMapping | None:
        out = self._impl.execute(input_data)
        return MissionOutputs(y_4=out["y_4"])
