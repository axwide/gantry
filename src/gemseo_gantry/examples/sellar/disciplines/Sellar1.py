# pyright: reportMissingImports=false, reportArgumentType=false
import numpy as np
from gemseo.typing import StrKeyMapping
from lib.Sellar1_base import Sellar1Base
from lib.Sellar1_io import (
    Sellar1Inputs,
    Sellar1Outputs,
)


class Sellar1(Sellar1Base):
    def _run(self, input_data: StrKeyMapping) -> StrKeyMapping | None:
        inputs = Sellar1Inputs.from_dict(input_data)

        # -------------------- Start of your analysis computation -------------------- #
        x_1 = inputs.x_1
        z = inputs.z
        y_2 = inputs.y_2

        # y_1 = sqrt(z_1^2 + z_2 + x_1 - 0.2 * y_2)
        y_1 = np.sqrt(np.maximum(0.0, z[0] ** 2 + z[1] + x_1 - 0.2 * y_2))

        outputs = Sellar1Outputs(
            y_1=y_1,
        )
        # --------------------- End of your analysis computation --------------------- #
        return outputs
