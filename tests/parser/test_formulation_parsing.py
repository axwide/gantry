from pathlib import Path

from gemseo_gantry.model.data_model import FormulationType
from gemseo_gantry.validation.pipeline import validate_toml

TOML = """
[disciplines.disc_a]
inputs = ["x"]
outputs = ["sub_obj"]

[disciplines.disc_b]
inputs = ["x"]
outputs = ["obj"]

[scenarios.sub]
design_variables = ["x"]
disciplines = ["disc_a"]
objective = { variable = "sub_obj" }

[scenarios.root]
design_variables = ["x"]
disciplines = ["disc_b", "Sub"]
formulation = "BiLevel"
objective = { variable = "obj" }

[[variables]]
name = "x"
data_type = "float"
dimension = 1
lower_bound = 0.0
upper_bound = 1.0
default_value = 0.5

[[variables]]
name = "sub_obj"
data_type = "float"
dimension = 1

[[variables]]
name = "obj"
data_type = "float"
dimension = 1
"""


def test_formulation_is_parsed(tmp_path: Path):
    toml = tmp_path / "p.toml"
    toml.write_text(TOML)
    result = validate_toml(toml)
    by_name = {s.name: s for s in result.problem.scenarios}
    assert by_name["Root"].formulation == FormulationType.BILEVEL
    assert by_name["Sub"].formulation is None
