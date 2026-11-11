from pathlib import Path

import pytest

_TOML_PATH = Path(__file__).parent.parent.parent / "fixtures" / "vleo.toml"


def _discipline_names():
    """Discipline names from the TOML fixture, resolved at collection time so
    each discipline can be a separate parametrized test case."""
    from gemseo_gantry.parser.toml_parser import parse_toml

    return [d.name for d in parse_toml(_TOML_PATH).disciplines]


DISCIPLINE_NAMES = _discipline_names()


@pytest.fixture(scope="module")
def grammars_dir(problem_def, tmp_path_factory):
    """Generate all discipline grammars once for the module."""
    from gemseo_gantry.generator.lib_generator import generate_discipline_grammars

    out = tmp_path_factory.mktemp("grammars")
    generate_discipline_grammars(problem_def, out)
    return out


@pytest.fixture(scope="module")
def io_dir(problem_def, tmp_path_factory):
    """Generate variables + all discipline IO once for the module."""
    from gemseo_gantry.generator.lib_generator import (
        generate_discipline_io,
        generate_variables,
    )

    out = tmp_path_factory.mktemp("io")
    generate_variables(problem_def, out)
    generate_discipline_io(problem_def, out)
    return out


@pytest.fixture(scope="module")
def scaffold_dir(problem_def, tmp_path_factory):
    """Generate all prerequisites + discipline scaffold once for the module."""
    from gemseo_gantry.generator.lib_generator import (
        generate_discipline_bases,
        generate_discipline_grammars,
        generate_discipline_io,
        generate_discipline_scaffold,
        generate_variables,
    )

    out = tmp_path_factory.mktemp("scaffold")
    generate_variables(problem_def, out)
    generate_discipline_io(problem_def, out)
    generate_discipline_grammars(problem_def, out)
    generate_discipline_bases(problem_def, out)
    generate_discipline_scaffold(problem_def, out, lib_package="generated")
    return out


@pytest.fixture(scope="module")
def bases_dir(problem_def, tmp_path_factory):
    """Generate all prerequisites + discipline bases once for the module."""
    from gemseo_gantry.generator.lib_generator import (
        generate_discipline_bases,
        generate_discipline_grammars,
        generate_discipline_io,
        generate_variables,
    )

    out = tmp_path_factory.mktemp("bases")
    generate_variables(problem_def, out)
    generate_discipline_io(problem_def, out)
    generate_discipline_grammars(problem_def, out)
    generate_discipline_bases(problem_def, out)
    return out


# -- lib_import_root unit tests -------------------------------------------------


def test_lib_import_root_happy_path(tmp_path):
    from gemseo_gantry.generator.lib_generator import lib_import_root

    import_root = tmp_path / "src"
    lib_dest = import_root / "myproject" / "generated" / "lib"
    lib_dest.mkdir(parents=True)
    assert lib_import_root(lib_dest, import_root) == "myproject.generated.lib"


def test_lib_import_root_single_segment(tmp_path):
    from gemseo_gantry.generator.lib_generator import lib_import_root

    import_root = tmp_path / "src"
    lib_dest = import_root / "lib"
    lib_dest.mkdir(parents=True)
    assert lib_import_root(lib_dest, import_root) == "lib"


def test_lib_import_root_import_root_not_a_dir(tmp_path):
    from gemseo_gantry.generator.lib_generator import lib_import_root

    import_root = tmp_path / "nonexistent"
    lib_dest = tmp_path / "nonexistent" / "lib"
    with pytest.raises(ValueError, match="import_root"):
        lib_import_root(lib_dest, import_root)


def test_lib_import_root_lib_dest_outside_import_root(tmp_path):
    from gemseo_gantry.generator.lib_generator import lib_import_root

    import_root = tmp_path / "src"
    import_root.mkdir()
    lib_dest = tmp_path / "other" / "lib"
    lib_dest.mkdir(parents=True)
    with pytest.raises(ValueError, match="lib_dest"):
        lib_import_root(lib_dest, import_root)


def test_lib_import_root_non_identifier_segment(tmp_path):
    from gemseo_gantry.generator.lib_generator import lib_import_root

    import_root = tmp_path / "src"
    lib_dest = import_root / "my-proj" / "lib"
    lib_dest.mkdir(parents=True)
    with pytest.raises(ValueError, match="identifier"):
        lib_import_root(lib_dest, import_root)


def test_lib_import_root_keyword_segment(tmp_path):
    from gemseo_gantry.generator.lib_generator import lib_import_root

    import_root = tmp_path / "src"
    lib_dest = import_root / "for" / "lib"
    lib_dest.mkdir(parents=True)
    with pytest.raises(ValueError, match="identifier"):
        lib_import_root(lib_dest, import_root)


def test_generate_discipline_grammars_complete(problem_def, grammars_dir):
    generated = {
        f.stem.replace("_grammar", "") for f in grammars_dir.glob("*_grammar.py")
    }
    assert generated == {d.name for d in problem_def.disciplines}


@pytest.mark.parametrize("discipline", DISCIPLINE_NAMES)
def test_generate_discipline_grammars(grammars_dir, snapshot, discipline):
    content = (grammars_dir / f"{discipline}_grammar.py").read_text(encoding="utf-8")
    assert content == snapshot


def test_generate_discipline_io_complete(problem_def, io_dir):
    generated = {f.stem.replace("_io", "") for f in io_dir.glob("*_io.py")}
    assert generated == {d.name for d in problem_def.disciplines}


@pytest.mark.parametrize("discipline", DISCIPLINE_NAMES)
def test_generate_discipline_io(io_dir, snapshot, discipline):
    content = (io_dir / f"{discipline}_io.py").read_text(encoding="utf-8")
    assert content == snapshot


def test_generate_discipline_scaffold_complete(problem_def, scaffold_dir):
    generated = {
        f.stem.replace("_scaffold", "") for f in scaffold_dir.glob("*_scaffold.py")
    }
    assert generated == {d.name for d in problem_def.disciplines}


@pytest.mark.parametrize("discipline", DISCIPLINE_NAMES)
def test_generate_discipline_scaffold(scaffold_dir, snapshot, discipline):
    content = (scaffold_dir / f"{discipline}_scaffold.py").read_text(encoding="utf-8")
    assert content == snapshot


@pytest.fixture(scope="module")
def scaffold_runnable_dir(problem_def, tmp_path_factory):
    """Generate scaffold files with runnable=True once for the module."""
    from gemseo_gantry.generator.lib_generator import (
        generate_discipline_grammars,
        generate_discipline_io,
        generate_discipline_scaffold,
        generate_variables,
    )

    out = tmp_path_factory.mktemp("scaffold_runnable")
    generate_variables(problem_def, out)
    generate_discipline_io(problem_def, out)
    generate_discipline_grammars(problem_def, out)
    generate_discipline_scaffold(
        problem_def, out, lib_package="generated", runnable=True
    )
    return out


@pytest.mark.parametrize("discipline", DISCIPLINE_NAMES)
def test_generate_discipline_scaffold_runnable(
    scaffold_runnable_dir, snapshot, discipline
):
    content = (scaffold_runnable_dir / f"{discipline}_scaffold.py").read_text(
        encoding="utf-8"
    )
    assert content == snapshot


def test_generate_discipline_bases_complete(problem_def, bases_dir):
    generated = {f.stem.replace("_base", "") for f in bases_dir.glob("*_base.py")}
    assert generated == {d.name for d in problem_def.disciplines}


@pytest.mark.parametrize("discipline", DISCIPLINE_NAMES)
def test_generate_discipline_bases(bases_dir, snapshot, discipline):
    content = (bases_dir / f"{discipline}_base.py").read_text(encoding="utf-8")
    assert content == snapshot


def test_generate_variables(problem_def, temp_generated_dir, snapshot):
    from gemseo_gantry.generator.lib_generator import generate_variables

    generate_variables(problem_def, temp_generated_dir)
    content = (temp_generated_dir / "variables.py").read_text(encoding="utf-8")
    assert content == snapshot


def test_generate_design_space(problem_def, temp_generated_dir, snapshot):
    from gemseo_gantry.generator.lib_generator import generate_design_space

    generate_design_space(problem_def, temp_generated_dir)
    content = (
        (temp_generated_dir / "design_space.csv")
        .read_text(encoding="utf-8")
        .replace("\r\n", "\n")
    )
    assert content == snapshot


def test_generate_scenario(problem_def, temp_generated_dir, snapshot):
    from gemseo_gantry.generator.lib_generator import generate_scenario

    generate_scenario(problem_def, temp_generated_dir)
    scenario = problem_def.scenarios[0]
    content = (temp_generated_dir / f"{scenario.name}.py").read_text(encoding="utf-8")
    assert content == snapshot


def test_generate_lib_returns_artifacts(problem_def, tmp_path):
    from gemseo_gantry.artifacts import ArtifactKind, ArtifactStatus
    from gemseo_gantry.generator.lib_generator import generate_lib

    artifacts = generate_lib(problem_def, tmp_path)

    lib_dir = tmp_path / "lib"
    # every artifact is a real file under lib/, all WRITTEN
    assert artifacts, "expected a non-empty artifact list"
    assert all(a.status is ArtifactStatus.WRITTEN for a in artifacts)
    assert all(a.path.parent == lib_dir for a in artifacts)
    by_path = {a.path: a.kind for a in artifacts}
    assert by_path[lib_dir / "__init__.py"] is ArtifactKind.PACKAGE_INIT
    assert by_path[lib_dir / "variables.py"] is ArtifactKind.VARIABLES
    assert by_path[lib_dir / "design_space.csv"] is ArtifactKind.DESIGN_SPACE
    # outer init is written but NOT reported
    assert (tmp_path / "__init__.py").exists()
    assert (tmp_path / "__init__.py") not in by_path


def test_build_lib_with_problem_def_returns_lib_path(problem_def, tmp_path):
    from gemseo_gantry.generator.lib_generator import generate_lib

    generate_lib(problem_def, tmp_path)

    assert (tmp_path / "lib").is_dir()
    assert (tmp_path / "lib" / "__init__.py").exists()


def test_build_lib_custom_package_name(problem_def, tmp_path):
    from gemseo_gantry.generator.lib_generator import generate_lib

    generate_lib(problem_def, tmp_path, lib_name="mylib")

    assert (tmp_path / "mylib").is_dir()


def test_build_lib_flat_skips_outer_init(problem_def, tmp_path):
    from gemseo_gantry.generator.lib_generator import generate_lib

    generate_lib(problem_def, tmp_path, is_import_root=True)

    assert not (tmp_path / "__init__.py").exists()


# -- integer variable type propagation ------------------------------------------


def _mixed_type_problem_def():
    from gemseo_gantry.parser.toml_parser import parse_toml

    return parse_toml(
        Path(__file__).parent.parent.parent / "fixtures" / "mixed_types.toml"
    )


def test_generate_discipline_grammars_integer_field(tmp_path):
    """An integer variable's grammar field is constrained to int64 via NDArrayPydantic."""
    from gemseo_gantry.generator.lib_generator import generate_discipline_grammars

    problem = _mixed_type_problem_def()
    generate_discipline_grammars(problem, tmp_path)

    content = (tmp_path / "Discipline1_grammar.py").read_text(encoding="utf-8")
    assert "n: NDArrayPydantic[np.int64]" in content
    assert "x: NDArrayPydantic" in content
    assert "x: NDArrayPydantic[np.int64]" not in content


def test_generate_discipline_io_integer_field(tmp_path):
    """An integer variable's IO field is annotated NDArray[np.integer]."""
    from gemseo_gantry.generator.lib_generator import (
        generate_discipline_io,
        generate_variables,
    )

    problem = _mixed_type_problem_def()
    generate_variables(problem, tmp_path)
    generate_discipline_io(problem, tmp_path)

    content = (tmp_path / "Discipline1_io.py").read_text(encoding="utf-8")
    assert "n: NDArray[np.integer]" in content
    assert "x: NDArray[np.floating]" in content


# -- _display_description unit tests --------------------------------------------


def test_display_description_both_present():
    from gemseo_gantry.generator.lib_generator import _display_description

    assert _display_description("Orbit altitude", "km") == "Orbit altitude [km]"


def test_display_description_unit_none():
    from gemseo_gantry.generator.lib_generator import _display_description

    assert _display_description("Orbit altitude", None) == "Orbit altitude"


def test_display_description_unit_empty_string():
    from gemseo_gantry.generator.lib_generator import _display_description

    assert _display_description("Orbit altitude", "") == "Orbit altitude"


def test_display_description_desc_none_unit_present():
    from gemseo_gantry.generator.lib_generator import _display_description

    assert _display_description(None, "km") == "[km]"


def test_display_description_both_none():
    from gemseo_gantry.generator.lib_generator import _display_description

    assert _display_description(None, None) == ""


def test_display_description_both_empty():
    from gemseo_gantry.generator.lib_generator import _display_description

    assert _display_description("", "") == ""


def test_display_description_whitespace_description():
    from gemseo_gantry.generator.lib_generator import _display_description

    assert _display_description("  ", "km") == "[km]"


def test_display_description_whitespace_unit():
    from gemseo_gantry.generator.lib_generator import _display_description

    assert _display_description("Orbit altitude", "  ") == "Orbit altitude"


def test_generate_variables_includes_unit_in_docstring(tmp_path):
    from gemseo_gantry.generator.lib_generator import generate_variables
    from gemseo_gantry.model.data_model import Discipline, ProblemDefinition, Variable

    problem = ProblemDefinition(
        variables=[
            Variable(
                name="altitude",
                unit="km",
                data_type="float",
                dimension=1,
                description="Orbit altitude",
            ),
        ],
        disciplines=[Discipline(name="d", inputs=["altitude"])],
    )
    generate_variables(problem, tmp_path)
    content = (tmp_path / "variables.py").read_text()
    assert "Orbit altitude [km]" in content


def test_generate_variables_no_brackets_when_unit_absent(tmp_path):
    from gemseo_gantry.generator.lib_generator import generate_variables
    from gemseo_gantry.model.data_model import Discipline, ProblemDefinition, Variable

    problem = ProblemDefinition(
        variables=[
            Variable(
                name="altitude",
                unit=None,
                data_type="float",
                dimension=1,
                description="Orbit altitude",
            ),
        ],
        disciplines=[Discipline(name="d", inputs=["altitude"])],
    )
    generate_variables(problem, tmp_path)
    content = (tmp_path / "variables.py").read_text()
    assert "Orbit altitude" in content
    assert "[]" not in content


def test_generate_grammar_includes_unit_in_field_description(tmp_path):
    from gemseo_gantry.generator.lib_generator import generate_discipline_grammars
    from gemseo_gantry.model.data_model import Discipline, ProblemDefinition, Variable

    problem = ProblemDefinition(
        variables=[
            Variable(
                name="x",
                unit="m",
                data_type="float",
                dimension=1,
                description="Position",
            ),
            Variable(
                name="y", unit="N", data_type="float", dimension=1, description="Force"
            ),
        ],
        disciplines=[Discipline(name="disc", inputs=["x"], outputs=["y"])],
    )
    generate_discipline_grammars(problem, tmp_path)
    content = (tmp_path / "disc_grammar.py").read_text()
    assert "Position [m]" in content
    assert "Force [N]" in content


def test_generate_grammar_unit_only_no_description(tmp_path):
    from gemseo_gantry.generator.lib_generator import generate_discipline_grammars
    from gemseo_gantry.model.data_model import Discipline, ProblemDefinition, Variable

    problem = ProblemDefinition(
        variables=[
            Variable(name="x", unit="m", data_type="float", dimension=1),
        ],
        disciplines=[Discipline(name="disc", inputs=["x"], outputs=[])],
    )
    generate_discipline_grammars(problem, tmp_path)
    content = (tmp_path / "disc_grammar.py").read_text()
    assert "[m]" in content


def test_generate_grammar_no_brackets_when_both_absent(tmp_path):
    from gemseo_gantry.generator.lib_generator import generate_discipline_grammars
    from gemseo_gantry.model.data_model import Discipline, ProblemDefinition, Variable

    problem = ProblemDefinition(
        variables=[
            Variable(name="x", unit=None, data_type="float", dimension=1),
        ],
        disciplines=[Discipline(name="disc", inputs=["x"], outputs=[])],
    )
    generate_discipline_grammars(problem, tmp_path)
    content = (tmp_path / "disc_grammar.py").read_text()
    assert "[]" not in content
    assert "Field" not in content


def test_generate_grammar_vector_default_emits_full_array(tmp_path):
    from gemseo_gantry.generator.lib_generator import generate_discipline_grammars
    from gemseo_gantry.model.data_model import Discipline, ProblemDefinition, Variable

    problem = ProblemDefinition(
        variables=[
            Variable(
                name="x",
                data_type="float",
                dimension=3,
                default_value=[1.0, 2.0, 3.0],
            ),
        ],
        disciplines=[Discipline(name="disc", inputs=["x"])],
    )
    generate_discipline_grammars(problem, tmp_path)
    content = (tmp_path / "disc_grammar.py").read_text()
    assert "np.array([1.0, 2.0, 3.0])" in content


def test_generate_grammar_scalar_default_unchanged(tmp_path):
    """Dimension-1 scalar default still renders as a single-element array."""
    from gemseo_gantry.generator.lib_generator import generate_discipline_grammars
    from gemseo_gantry.model.data_model import Discipline, ProblemDefinition, Variable

    problem = ProblemDefinition(
        variables=[
            Variable(name="x", data_type="float", dimension=1, default_value=5.0),
        ],
        disciplines=[Discipline(name="disc", inputs=["x"])],
    )
    generate_discipline_grammars(problem, tmp_path)
    content = (tmp_path / "disc_grammar.py").read_text()
    assert "np.array([5.0])" in content


def test_generate_scaffold_vector_output_uses_np_zeros(tmp_path):
    from gemseo_gantry.generator.lib_generator import generate_discipline_scaffold
    from gemseo_gantry.model.data_model import Discipline, ProblemDefinition, Variable

    problem = ProblemDefinition(
        variables=[
            Variable(name="x", data_type="float", dimension=1),
            Variable(name="y", data_type="float", dimension=4),
        ],
        disciplines=[Discipline(name="disc", inputs=["x"], outputs=["y"])],
    )
    generate_discipline_scaffold(problem, tmp_path, lib_package="generated")
    content = (tmp_path / "disc_scaffold.py").read_text()
    assert "np.zeros(4)" in content
    assert "np.array([0.0])" not in content


def test_generate_scaffold_scalar_output_uses_np_zeros_one(tmp_path):
    from gemseo_gantry.generator.lib_generator import generate_discipline_scaffold
    from gemseo_gantry.model.data_model import Discipline, ProblemDefinition, Variable

    problem = ProblemDefinition(
        variables=[
            Variable(name="x", data_type="float", dimension=1),
            Variable(name="y", data_type="float", dimension=1),
        ],
        disciplines=[Discipline(name="disc", inputs=["x"], outputs=["y"])],
    )
    generate_discipline_scaffold(problem, tmp_path, lib_package="generated")
    content = (tmp_path / "disc_scaffold.py").read_text()
    assert "np.zeros(1)" in content
