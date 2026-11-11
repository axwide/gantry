# pyright: reportMissingImports=false, reportArgumentType=false
import numpy as np
from gemseo.typing import StrKeyMapping
from lib.Sellar2_base import Sellar2Base
from lib.Sellar2_io import (
    Sellar2Inputs,
    Sellar2Outputs,
)


class Sellar2(Sellar2Base):
    def _run(self, input_data: StrKeyMapping) -> StrKeyMapping | None:
        inputs = Sellar2Inputs.from_dict(input_data)

        # -------------------- Start of your analysis computation -------------------- #
        z = inputs.z
        y_1 = inputs.y_1

        # y_2 = |y_1| + z_1 + z_2
        y_2 = np.abs(y_1) + z[0] + z[1]

        outputs = Sellar2Outputs(
            y_2=y_2,
        )
        # --------------------- End of your analysis computation --------------------- #
        return outputs
