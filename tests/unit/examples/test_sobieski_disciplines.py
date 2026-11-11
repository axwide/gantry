import shutil
import sys

import pytest

from gemseo_gantry.examples.registry import get_example
from gemseo_gantry.generator import generate_lib
from gemseo_gantry.parser.toml_parser import parse_toml


@pytest.fixture()
def sobieski_tree(tmp_path):
    ex = get_example("sobieski")
    problem = parse_toml(ex.root / f"{ex.name}.toml")
    generate_lib(problem, tmp_path, lib_name="lib")
    shutil.copytree(ex.root / "disciplines", tmp_path / "disciplines")
    (tmp_path / "disciplines" / "__init__.py").write_text("", encoding="utf-8")
    sys.path.insert(0, str(tmp_path))
    try:
        yield tmp_path
    finally:
        for key in list(sys.modules):
            if key == "lib" or key.startswith("lib.") or key.startswith("disciplines"):
                sys.modules.pop(key, None)
        sys.path.remove(str(tmp_path))


@pytest.mark.parametrize(
    ("module", "cls", "gemseo_cls", "outputs"),
    [
        (
            "Structure",
            "Structure",
            "SobieskiStructure",
            ["y_1", "y_11", "y_12", "y_14", "g_1"],
        ),
        (
            "Aerodynamics",
            "Aerodynamics",
            "SobieskiAerodynamics",
            ["y_2", "y_21", "y_23", "y_24", "g_2"],
        ),
        (
            "Propulsion",
            "Propulsion",
            "SobieskiPropulsion",
            ["y_3", "y_31", "y_32", "y_34", "g_3"],
        ),
        ("Mission", "Mission", "SobieskiMission", ["y_4"]),
    ],
)
def test_sobieski_discipline_delegates_to_gemseo(
    sobieski_tree, module, cls, gemseo_cls, outputs
):
    import importlib

    import gemseo.problems.mdo.sobieski.disciplines as gem

    wrapper = getattr(importlib.import_module(f"disciplines.{module}"), cls)()
    reference = getattr(gem, gemseo_cls)()

    # GEMSEO disciplines have full default inputs; run both on those defaults.
    ref_out = reference.execute()
    inputs = {k: ref_out[k] for k in reference.io.input_grammar.names}
    wrap_out = wrapper.execute(inputs)

    for name in outputs:
        assert wrap_out[name] == pytest.approx(ref_out[name])
