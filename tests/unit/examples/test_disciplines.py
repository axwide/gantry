import shutil
import sys

import numpy as np
import pytest

from gemseo_gantry.examples.registry import get_example
from gemseo_gantry.generator import generate_lib
from gemseo_gantry.parser.toml_parser import parse_toml


@pytest.fixture()
def sellar_tree(tmp_path):
    """A minimal generated tree: lib/ regenerated, disciplines/ copied in."""
    ex = get_example("sellar")
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


def test_sellar_1_physics(sellar_tree):
    from disciplines.Sellar1 import Sellar1

    out = Sellar1().execute(
        {"x_1": np.array([1.0]), "z": np.array([4.0, 3.0]), "y_2": np.array([1.0])}
    )
    expected = np.sqrt(4.0**2 + 3.0 + 1.0 - 0.2 * 1.0)
    assert out["y_1"] == pytest.approx(expected)


def test_sellar_2_physics(sellar_tree):
    from disciplines.Sellar2 import Sellar2

    out = Sellar2().execute({"z": np.array([4.0, 3.0]), "y_1": np.array([4.0])})
    expected = abs(4.0) + 4.0 + 3.0
    assert out["y_2"] == pytest.approx(expected)


def test_sellar_system_physics(sellar_tree):
    from disciplines.SellarSystem import SellarSystem

    out = SellarSystem().execute(
        {
            "x_1": np.array([1.0]),
            "z": np.array([4.0, 3.0]),
            "y_1": np.array([4.0]),
            "y_2": np.array([25.0]),
        }
    )
    assert out["obj"] == pytest.approx(1.0**2 + 3.0 + 4.0**2 + np.exp(-25.0))
    assert out["c_1"] == pytest.approx(3.16 - 4.0**2)
    assert out["c_2"] == pytest.approx(25.0 - 24.0)
