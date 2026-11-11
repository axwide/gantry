from gemseo_gantry.model.data_model import Variable
from gemseo_gantry.parser.toml_data_model import TomlVariable


def test_toml_variable_unit_defaults_to_none():
    v = TomlVariable(name="x", data_type="float", dimension=1)
    assert v.unit is None


def test_toml_variable_unit_accepts_string():
    v = TomlVariable(name="x", unit="km", data_type="float", dimension=1)
    assert v.unit == "km"


def test_toml_variable_unit_accepts_empty_string():
    v = TomlVariable(name="x", unit="", data_type="float", dimension=1)
    assert v.unit == ""


def test_variable_unit_defaults_to_none():
    v = Variable(name="x", data_type="float", dimension=1)
    assert v.unit is None


def test_variable_unit_accepts_string():
    v = Variable(name="x", unit="km", data_type="float", dimension=1)
    assert v.unit == "km"
