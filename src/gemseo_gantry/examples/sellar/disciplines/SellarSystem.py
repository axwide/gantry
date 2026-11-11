# pyright: reportMissingImports=false, reportArgumentType=false
import numpy as np
from gemseo.typing import StrKeyMapping
from lib.SellarSystem_base import SellarSystemBase
from lib.SellarSystem_io import (
    SellarSystemInputs,
    SellarSystemOutputs,
)


class SellarSystem(SellarSystemBase):
    def _run(self, input_data: StrKeyMapping) -> StrKeyMapping | None:
        inputs = SellarSystemInputs.from_dict(input_data)

        # -------------------- Start of your analysis computation -------------------- #
        x_1 = inputs.x_1
        z = inputs.z
        y_1 = inputs.y_1
        y_2 = inputs.y_2

        # obj = x_1^2 + z_2 + y_1^2 + exp(-y_2)
        obj = x_1**2 + z[1] + y_1**2 + np.exp(-y_2)
        # c_1 = 3.16 - y_1^2  (feasible when <= 0, i.e. y_1^2 >= 3.16)
        c_1 = 3.16 - y_1**2
        # c_2 = y_2 - 24.0    (feasible when <= 0)
        c_2 = y_2 - 24.0

        outputs = SellarSystemOutputs(
            obj=obj,
            c_1=c_1,
            c_2=c_2,
        )
        # --------------------- End of your analysis computation --------------------- #
        return outputs
