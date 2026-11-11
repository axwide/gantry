"""
Behavioral/structural tests for the code generator.

These tests assert semantic properties of the generated artifacts rather than
text equality, making them robust to formatting and structural refactors.
"""

import csv
import dataclasses
import importlib
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from gemseo_gantry.artifacts import ArtifactStatus
from gemseo_gantry.model.data_model import DataType
from tests.conftest import PYRIGHT_SUPPRESS_RULES

PROJECT_ROOT = Path(__file__).parent.parent
FIXTURES_DIR = PROJECT_ROOT / "fixtures"


# -- Grammar field names --------------------------------------------------------


def test_grammar_input_field_names(all_problem_defs, temp_generated_dir):
    """Each generated InputGrammar has exactly the discipline's input variable names."""
    from gemseo_gantry.generator.lib_generator import generate_discipline_grammars

    generate_discipline_grammars(all_problem_defs, temp_generated_dir)

    for discipline in all_problem_defs.disciplines:
        if not discipline.inputs:
            continue
        mod = importlib.import_module(f"generated.{discipline.name}_grammar")
        InputGrammar = getattr(mod, f"{discipline.name}InputGrammar")
        assert set(InputGrammar.model_fields) == set(discipline.inputs), (
            f"{discipline.name}InputGrammar field mismatch"
        )


def test_grammar_output_field_names(all_problem_defs, temp_generated_dir):
    """Each generated OutputGrammar has exactly the discipline's output variable names."""
    from gemseo_gantry.generator.lib_generator import generate_discipline_grammars

    generate_discipline_grammars(all_problem_defs, temp_generated_dir)

    for discipline in all_problem_defs.disciplines:
        if not discipline.outputs:
            continue
        mod = importlib.import_module(f"generated.{discipline.name}_grammar")
        OutputGrammar = getattr(mod, f"{discipline.name}OutputGrammar")
        assert set(OutputGrammar.model_fields) == set(discipline.outputs), (
            f"{discipline.name}OutputGrammar field mismatch"
        )


# -- IO module -----------------------------------------------------------------


def test_io_inputs_dataclass_fields(all_problem_defs, temp_generated_dir):
    """Generated Inputs is a dataclass whose fields match the discipline's inputs."""
    from gemseo_gantry.generator.lib_generator import (
        generate_discipline_io,
        generate_variables,
    )

    generate_variables(all_problem_defs, temp_generated_dir)
    generate_discipline_io(all_problem_defs, temp_generated_dir)

    for discipline in all_problem_defs.disciplines:
        if not discipline.inputs:
            continue
        mod = importlib.import_module(f"generated.{discipline.name}_io")
        InputsClass = getattr(mod, f"{discipline.name}Inputs")
        assert dataclasses.is_dataclass(InputsClass), (
            f"{discipline.name}Inputs is not a dataclass"
        )
        assert {f.name for f in dataclasses.fields(InputsClass)} == set(
            discipline.inputs
        ), f"{discipline.name}Inputs field mismatch"
        assert hasattr(InputsClass, "from_dict"), (
            f"{discipline.name}Inputs missing from_dict"
        )


def test_io_outputs_is_dict_subclass(all_problem_defs, temp_generated_dir):
    """Generated Outputs class is a dict subclass."""
    from gemseo_gantry.generator.lib_generator import (
        generate_discipline_io,
        generate_variables,
    )

    generate_variables(all_problem_defs, temp_generated_dir)
    generate_discipline_io(all_problem_defs, temp_generated_dir)

    for discipline in all_problem_defs.disciplines:
        mod = importlib.import_module(f"generated.{discipline.name}_io")
        OutputsClass = getattr(mod, f"{discipline.name}Outputs")
        assert issubclass(OutputsClass, dict), (
            f"{discipline.name}Outputs is not a dict subclass"
        )


# -- Scaffold files ------------------------------------------------------------


def test_generate_discipline_scaffold_creates_scaffold_files(
    all_problem_defs, tmp_path
):
    """generate_discipline_scaffold() emits *_scaffold.py for each discipline."""
    from gemseo_gantry.generator.lib_generator import generate_discipline_scaffold

    generate_discipline_scaffold(all_problem_defs, tmp_path, lib_package="generated")
    for discipline in all_problem_defs.disciplines:
        assert (tmp_path / f"{discipline.name}_scaffold.py").exists()


# -- Variables enum -------------------------------------------------------------


def test_variables_enum_members(all_problem_defs, temp_generated_dir):
    """Generated Var enum values match all variable names from the problem definition."""
    from gemseo_gantry.generator.lib_generator import generate_variables

    generate_variables(all_problem_defs, temp_generated_dir)

    mod = importlib.import_module("generated.variables")
    Var = getattr(mod, "Var")
    expected = {var.name for var in all_problem_defs.variables}
    actual = {member.value for member in Var}
    assert actual == expected, (
        f"Var mismatch - extra: {actual - expected}, missing: {expected - actual}"
    )


# -- Design space CSV -----------------------------------------------------------


def test_design_space_rows_and_columns(all_problem_defs, temp_generated_dir):
    """Generated design_space.csv has required columns and one row per design variable."""
    if not any(v.is_design_variable for v in all_problem_defs.variables):
        pytest.skip("fixture has no design variables")

    from gemseo_gantry.generator.lib_generator import generate_design_space

    generate_design_space(all_problem_defs, temp_generated_dir)

    csv_path = temp_generated_dir / "design_space.csv"
    assert csv_path.exists()

    with csv_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = set(reader.fieldnames or [])

    assert {"name", "lower_bound", "value", "upper_bound", "type"}.issubset(
        fieldnames
    ), f"design_space.csv missing columns: {fieldnames}"

    expected_vars = {
        var.name for var in all_problem_defs.variables if var.is_design_variable
    }
    actual_vars = {row["name"] for row in rows}
    assert actual_vars == expected_vars, (
        f"design variable row mismatch - extra: {actual_vars - expected_vars}, "
        f"missing: {expected_vars - actual_vars}"
    )


def test_array_dimensioned_design_space_round_trips_through_gemseo(temp_generated_dir):
    """A dimension>1 design variable's design_space.csv reconstructs to the
    correct size, bounds, and current value via GEMSEO's DesignSpace.from_csv -
    confirming the repeated-row CSV layout is GEMSEO-compatible."""
    from gemseo.algos.design_space import DesignSpace

    from gemseo_gantry.generator.lib_generator import generate_design_space
    from gemseo_gantry.parser.toml_parser import parse_toml

    problem = parse_toml(FIXTURES_DIR / "array_dimensioned.toml")
    generate_design_space(problem, temp_generated_dir)

    design_space = DesignSpace.from_csv(
        file_path=temp_generated_dir / "design_space.csv",
        delimiter=",",
    )

    assert design_space.get_size("x") == 3
    np.testing.assert_array_equal(design_space.get_lower_bound("x"), [0.0, 0.0, 0.0])
    np.testing.assert_array_equal(design_space.get_upper_bound("x"), [10.0, 10.0, 10.0])
    np.testing.assert_array_equal(
        design_space.get_current_value(["x"]), [1.0, 2.0, 3.0]
    )


def test_design_space_missing_bounds_round_trip_to_infinity(temp_generated_dir):
    """A design variable with no bounds generates a CSV that GEMSEO loads as +/-inf.

    Omitted lower/upper bounds map to -inf/+inf.
    """
    from gemseo.algos.design_space import DesignSpace

    from gemseo_gantry.generator.lib_generator import generate_design_space
    from gemseo_gantry.model.data_model import (
        DataType,
        Discipline,
        ProblemDefinition,
        Variable,
    )

    problem = ProblemDefinition(
        variables=[
            Variable(
                name="x",
                unit="m",
                data_type=DataType.FLOAT,
                dimension=1,
                default_value=5.0,
                is_design_variable=True,
            ),  # no lower_bound / upper_bound
        ],
        disciplines=[Discipline(name="disc1", inputs=["x"], outputs=["y"])],
    )

    generate_design_space(problem, temp_generated_dir)

    ds = DesignSpace.from_csv(temp_generated_dir / "design_space.csv", delimiter=",")
    assert ds.get_lower_bound("x") == np.array([-np.inf])
    assert ds.get_upper_bound("x") == np.array([np.inf])
    np.testing.assert_array_equal(ds.get_current_value(["x"]), np.array([5.0]))


# -- Scenario structural --------------------------------------------------------


def test_scenario_structure_and_construct(all_problem_defs, temp_generated_dir):
    """Generated scenario module exposes construct_* + *Disciplines and returns a BaseScenario."""
    if not all_problem_defs.scenarios:
        pytest.skip("fixture has no scenarios")
    scenario_names = {s.name for s in all_problem_defs.scenarios}
    if any(set(s.disciplines) & scenario_names for s in all_problem_defs.scenarios):
        # Nested scenarios reference sub-scenarios (not disciplines) in their
        # discipline list; constructing them is out of scope here.
        pytest.skip("fixture has nested scenarios")

    from gemseo.formulations.mdf_settings import MDF_Settings
    from gemseo.scenarios.base_scenario import BaseScenario

    from gemseo_gantry.generator.lib_generator import (
        generate_design_space,
        generate_discipline_bases,
        generate_discipline_grammars,
        generate_discipline_io,
        generate_discipline_scaffold,
        generate_scenario,
        generate_variables,
    )

    generate_variables(all_problem_defs, temp_generated_dir)
    generate_discipline_grammars(all_problem_defs, temp_generated_dir)
    generate_discipline_io(all_problem_defs, temp_generated_dir)
    generate_discipline_bases(all_problem_defs, temp_generated_dir)
    generate_discipline_scaffold(
        all_problem_defs, temp_generated_dir, lib_package="generated"
    )
    generate_design_space(all_problem_defs, temp_generated_dir)
    generate_scenario(all_problem_defs, temp_generated_dir)

    for scenario in all_problem_defs.scenarios:
        mod = importlib.import_module(f"generated.{scenario.name}")

        construct_fn = getattr(mod, f"construct_{scenario.name}", None)
        assert construct_fn is not None, f"missing construct_{scenario.name}"

        DisciplinesClass: type | None = getattr(
            mod, f"{scenario.name}Disciplines", None
        )
        assert DisciplinesClass is not None, (
            f"missing {scenario.name}Disciplines dataclass"
        )
        assert dataclasses.is_dataclass(DisciplinesClass)

        disc_kwargs = {}
        for disc_name in all_problem_defs.plain_discipline_names_of(scenario):
            scaffold_mod = importlib.import_module(f"generated.{disc_name}_scaffold")
            disc_kwargs[disc_name] = getattr(scaffold_mod, disc_name)()

        result = construct_fn(
            disciplines=DisciplinesClass(**disc_kwargs),
            formulation_settings_model=MDF_Settings(),
        )
        assert isinstance(result, BaseScenario)


# -- basedpyright on generated lib ----------------------------------------------


def test_generated_lib_basedpyright_clean(tmp_path):
    """Every generated lib/ passes basedpyright with no type errors.

    All fixtures are checked in a *single* basedpyright invocation rather than one
    subprocess per fixture: the type checker's cold start (and the surrounding
    ``uv run``) dominated the cost, so spawning it 15x was the test suite's biggest
    hotspot. Each lib gets its own ``executionEnvironments`` root so intra-lib imports
    resolve exactly as they would when checked in isolation.

    The shared suppression rules silence upstream limitations in the generated lib:
    - reportMissingTypeStubs: gemseo ships no stubs
    - reportMissingTypeArgument/reportAssignmentType: NDArrayPydantic used bare to
      avoid pydantic runtime errors when GEMSEO passes numpy.float64 arrays
    - reportUnannotatedClassAttribute: self.input_grammar / self.output_grammar invoke
      property setters defined on BaseDiscipline, but GEMSEO ships no type stubs so
      basedpyright cannot see the parent property and treats the assignments as creating
      new unannotated attributes - a false positive caused by missing stubs
    """
    import json

    from gemseo_gantry.generator.lib_generator import generate_lib
    from gemseo_gantry.parser.toml_parser import parse_toml

    lib_dirs: list[Path] = []
    for toml_path in sorted(FIXTURES_DIR.glob("*.toml")):
        generate_lib(parse_toml(toml_path), tmp_path / toml_path.stem)
        lib_dirs.append(tmp_path / toml_path.stem / "lib")

    config = {
        **PYRIGHT_SUPPRESS_RULES,
        "include": [str(d) for d in lib_dirs],
        "executionEnvironments": [{"root": str(d)} for d in lib_dirs],
    }
    (tmp_path / "pyrightconfig.json").write_text(
        json.dumps(config),
        encoding="utf-8",
    )

    result = subprocess.run(
        ["uv", "run", "basedpyright", "--project", str(tmp_path)],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )
    assert result.returncode == 0, (
        f"basedpyright found errors in generated libs:\n{result.stdout}\n{result.stderr}"
    )


# -- Grammar field defaults ------------------------------------------------------


def test_grammar_default_values(all_problem_defs, temp_generated_dir):
    """
    Test that generated grammar models have correct field defaults embedded via
    Field(default_factory=...), matching the default_value from the problem definition.
    """
    from gemseo_gantry.generator.lib_generator import generate_discipline_grammars

    generate_discipline_grammars(all_problem_defs, temp_generated_dir)

    var_defaults = {
        var.name: var.default_values()
        for var in all_problem_defs.variables
        if var.default_value is not None
    }

    imported_modules = []
    try:
        for discipline in all_problem_defs.disciplines:
            module_name = f"generated.{discipline.name}_grammar"
            grammar_module = importlib.import_module(module_name)
            imported_modules.append(module_name)
            InputGrammar = getattr(grammar_module, f"{discipline.name}InputGrammar")

            for var_name in discipline.inputs:
                field_info = InputGrammar.model_fields.get(var_name)
                assert field_info is not None, (
                    f"Field '{var_name}' missing from {discipline.name}InputGrammar"
                )

                if var_name in var_defaults:
                    default = field_info.get_default(call_default_factory=True)
                    expected = np.array(var_defaults[var_name])
                    np.testing.assert_array_equal(
                        default,
                        expected,
                        err_msg=f"Default mismatch for '{var_name}' in {discipline.name}InputGrammar",
                    )
    finally:
        for module_name in imported_modules:
            sys.modules.pop(module_name, None)
        sys.modules.pop("generated", None)


# -- generate_lib + scaffold ----------------------------------------------------


def test_generate_lib_creates_lib_dir(all_problem_defs, tmp_path):
    """generate_lib() creates output_dir/lib/ with all expected lib files."""
    from gemseo_gantry.generator.lib_generator import generate_lib

    output_dir = tmp_path / "out"
    generate_lib(all_problem_defs, output_dir)

    lib_dir = output_dir / "lib"
    assert lib_dir.is_dir()
    assert (lib_dir / "variables.py").exists()
    assert (lib_dir / "design_space.csv").exists()
    for discipline in all_problem_defs.disciplines:
        assert (lib_dir / f"{discipline.name}_grammar.py").exists()
        assert (lib_dir / f"{discipline.name}_io.py").exists()
        assert (lib_dir / f"{discipline.name}_base.py").exists()


def test_generate_lib_only_touches_lib(all_problem_defs, tmp_path):
    """generate_lib() never writes outside lib/ - scaffold/ is untouched."""
    from gemseo_gantry.generator.lib_generator import generate_lib

    output_dir = tmp_path / "out"
    scaffold_dir = output_dir / "scaffold"
    scaffold_dir.mkdir(parents=True)
    sentinel = scaffold_dir / "user_code.py"
    sentinel.write_text("# user code", encoding="utf-8")

    generate_lib(all_problem_defs, output_dir)

    assert sentinel.exists(), "generate_lib must not touch scaffold/"
    assert not list(scaffold_dir.glob("*_scaffold.py")), (
        "generate_lib must not write scaffold files"
    )


def test_generate_lib_wipes_stale_lib(all_problem_defs, tmp_path):
    """Calling generate_lib twice removes stale lib files from the first call."""
    from gemseo_gantry.generator.lib_generator import generate_lib

    output_dir = tmp_path / "out"
    generate_lib(all_problem_defs, output_dir)
    stale = output_dir / "lib" / "stale_file.py"
    stale.write_text("# stale", encoding="utf-8")

    generate_lib(all_problem_defs, output_dir)

    assert not stale.exists(), "second generate_lib call should wipe stale_file.py"


# -- Problem layout (lib/) --------------------------------------------------------


def test_generate_lib_creates_only_lib(all_problem_defs, tmp_path):
    """
    generate_lib() creates lib/ with all expected lib files, and never creates scaffold/.
    The invariant: generate touches lib and nothing else.
    """
    from gemseo_gantry.generator.lib_generator import generate_lib

    output_dir = tmp_path / "generated"
    generate_lib(all_problem_defs, output_dir)

    lib_dir = output_dir / "lib"
    scaffold_dir = output_dir / "scaffold"

    assert lib_dir.is_dir(), "lib/ subdirectory was not created"
    assert not scaffold_dir.exists(), (
        "scaffold/ must not exist after generate_lib - it is not generated by this operation"
    )

    assert (lib_dir / "variables.py").exists()
    assert (lib_dir / "design_space.csv").exists()
    for discipline in all_problem_defs.disciplines:
        assert (lib_dir / f"{discipline.name}_grammar.py").exists()
        assert (lib_dir / f"{discipline.name}_io.py").exists()
        assert (lib_dir / f"{discipline.name}_base.py").exists()

    assert not list(lib_dir.glob("*_scaffold.py")), (
        "Scaffold files must not appear in lib/"
    )


def test_discipline_scaffold_subclasses_base(all_problem_defs, temp_generated_dir):
    """Each generated scaffold class is a runtime subclass of its {Name}Base."""
    from gemseo_gantry.generator.lib_generator import (
        generate_discipline_bases,
        generate_discipline_grammars,
        generate_discipline_io,
        generate_discipline_scaffold,
        generate_variables,
    )

    generate_variables(all_problem_defs, temp_generated_dir)
    generate_discipline_grammars(all_problem_defs, temp_generated_dir)
    generate_discipline_io(all_problem_defs, temp_generated_dir)
    generate_discipline_bases(all_problem_defs, temp_generated_dir)
    generate_discipline_scaffold(
        all_problem_defs, temp_generated_dir, lib_package="generated"
    )

    for discipline in all_problem_defs.disciplines:
        base_mod = importlib.import_module(f"generated.{discipline.name}_base")
        scaffold_mod = importlib.import_module(f"generated.{discipline.name}_scaffold")

        BaseClass = getattr(base_mod, f"{discipline.name}Base")
        ScaffoldClass = getattr(scaffold_mod, discipline.name)

        assert issubclass(ScaffoldClass, BaseClass), (
            f"{discipline.name} scaffold does not subclass {discipline.name}Base"
        )


# -- scaffold_generator tests --------------------------------------------------


@pytest.fixture
def scaffold_lib_setup(all_problem_defs, tmp_path):
    """Generate lib/ into a temp dir; return (lib_dir, import_root)."""
    from gemseo_gantry.generator.lib_generator import generate_lib

    gen_dir = tmp_path / "generated"
    generate_lib(all_problem_defs, gen_dir)
    import_root = tmp_path
    return gen_dir / "lib", import_root


def test_scaffold_creates_target_dir(all_problem_defs, scaffold_lib_setup):
    """Non-existent target_dir is created; all disciplines are in result.written."""
    from gemseo_gantry.generator.scaffold_generator import generate_disciplines

    lib_dir, import_root = scaffold_lib_setup
    target_dir = lib_dir.parent.parent / "new_target"
    assert not target_dir.exists()

    result = generate_disciplines(all_problem_defs, target_dir, lib_dir, import_root)

    assert target_dir.exists()
    assert {a.path.name for a in result if a.status is ArtifactStatus.WRITTEN} == {
        f"{d.name}_scaffold.py" for d in all_problem_defs.disciplines
    }
    assert all(a.status is ArtifactStatus.WRITTEN for a in result)
    for d in all_problem_defs.disciplines:
        assert (target_dir / f"{d.name}_scaffold.py").exists()


def test_scaffold_write_once_skips_existing(
    all_problem_defs, scaffold_lib_setup, tmp_path
):
    """Second scaffold call skips all files; existing content is unchanged."""
    from gemseo_gantry.generator.scaffold_generator import generate_disciplines

    lib_dir, import_root = scaffold_lib_setup
    target_dir = tmp_path / "target"

    generate_disciplines(all_problem_defs, target_dir, lib_dir, import_root)

    # Capture file contents after first run
    first_contents = {
        d.name: (target_dir / f"{d.name}_scaffold.py").read_bytes()
        for d in all_problem_defs.disciplines
    }

    result2 = generate_disciplines(all_problem_defs, target_dir, lib_dir, import_root)

    assert {a.path.name for a in result2 if a.status is ArtifactStatus.SKIPPED} == {
        f"{d.name}_scaffold.py" for d in all_problem_defs.disciplines
    }
    assert all(a.status is ArtifactStatus.SKIPPED for a in result2)
    for d in all_problem_defs.disciplines:
        assert (target_dir / f"{d.name}_scaffold.py").read_bytes() == first_contents[
            d.name
        ]


def test_scaffold_force_overwrites_existing(
    all_problem_defs, scaffold_lib_setup, tmp_path
):
    """force=True overwrites mutated files; result.written contains all disciplines."""
    from gemseo_gantry.generator.scaffold_generator import generate_disciplines

    lib_dir, import_root = scaffold_lib_setup
    target_dir = tmp_path / "target"

    generate_disciplines(all_problem_defs, target_dir, lib_dir, import_root)

    # Mutate one file
    first_discipline = all_problem_defs.disciplines[0]
    mutated_file = target_dir / f"{first_discipline.name}_scaffold.py"
    original_content = mutated_file.read_bytes()
    mutated_file.write_text("# mutated", encoding="utf-8")

    result = generate_disciplines(
        all_problem_defs, target_dir, lib_dir, import_root, force=True
    )

    assert {a.path.name for a in result if a.status is ArtifactStatus.WRITTEN} == {
        f"{d.name}_scaffold.py" for d in all_problem_defs.disciplines
    }
    assert all(a.status is ArtifactStatus.WRITTEN for a in result)
    assert mutated_file.read_bytes() == original_content


# -- Scaffold runnable/non-runnable behaviour ----------------------------------


def test_discipline_scaffold_raises_not_implemented(
    all_problem_defs, temp_generated_dir
):
    """Default scaffold _run raises NotImplementedError."""
    import importlib.util

    import numpy as np

    from gemseo_gantry.generator.lib_generator import generate_lib
    from gemseo_gantry.generator.scaffold_generator import generate_disciplines

    lib_dir = temp_generated_dir / "lib"
    import_root = temp_generated_dir.parent
    generate_lib(all_problem_defs, temp_generated_dir)
    target_dir = temp_generated_dir.parent / "scaffold_default"
    generate_disciplines(
        all_problem_defs, target_dir, lib_dir, import_root, runnable=False
    )

    for discipline in all_problem_defs.disciplines:
        scaffold_file = target_dir / f"{discipline.name}_scaffold.py"
        spec = importlib.util.spec_from_file_location(discipline.name, scaffold_file)
        assert spec is not None and spec.loader is not None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        cls = getattr(mod, discipline.name)
        instance = cls()
        input_data = {var_name: np.array([0.0]) for var_name in discipline.inputs}
        with pytest.raises(NotImplementedError):
            instance._run(input_data)


def test_discipline_scaffold_runnable_does_not_raise(
    all_problem_defs, temp_generated_dir
):
    """Runnable scaffold _run does not raise NotImplementedError."""
    import importlib.util

    import numpy as np

    from gemseo_gantry.generator.lib_generator import generate_lib
    from gemseo_gantry.generator.scaffold_generator import generate_disciplines

    lib_dir = temp_generated_dir / "lib"
    import_root = temp_generated_dir.parent
    generate_lib(all_problem_defs, temp_generated_dir)
    target_dir = temp_generated_dir.parent / "scaffold_runnable"
    generate_disciplines(
        all_problem_defs, target_dir, lib_dir, import_root, runnable=True
    )

    for discipline in all_problem_defs.disciplines:
        scaffold_file = target_dir / f"{discipline.name}_scaffold.py"
        spec = importlib.util.spec_from_file_location(discipline.name, scaffold_file)
        assert spec is not None and spec.loader is not None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        cls = getattr(mod, discipline.name)
        instance = cls()
        input_data = {var_name: np.array([0.0]) for var_name in discipline.inputs}
        try:
            instance._run(input_data)
        except NotImplementedError:
            pytest.fail(
                f"{discipline.name} runnable scaffold raised NotImplementedError"
            )


# -- End-to-end scenario execution ---------------------------------------------


def test_generated_executor_runs_scenario_end_to_end(
    all_problem_defs, tmp_path, request
):
    """Generated execute_<ScenarioName>() constructs and fully executes the scenario."""
    if not all_problem_defs.scenarios:
        pytest.skip("fixture has no scenarios")
    if any(
        v.lower_bound is None
        for v in all_problem_defs.variables
        if v.is_design_variable
    ):
        request.node.add_marker(
            pytest.mark.xfail(
                strict=True,
                reason="missing variable bounds - GEMSEO DesignSpace rejects NaN lower_bound",
            )
        )

    if any(
        v.data_type == DataType.INTEGER
        for v in all_problem_defs.variables
        if v.is_design_variable
    ) and any(s.formulation_type == "MDO" for s in all_problem_defs.scenarios):
        request.node.add_marker(
            pytest.mark.xfail(
                strict=True,
                reason="default MDO scenario algorithm does not handle integer design variables",
            )
        )

    from gemseo_gantry.generator.lib_generator import generate_lib
    from gemseo_gantry.generator.scaffold_generator import (
        generate_disciplines,
        generate_scenario_executor,
    )

    # Build package structure under tmp_path/study/ so absolute imports resolve.
    # import_root = study/  (added to sys.path)
    # study/generated/lib/   <- lib
    # study/disciplines/     <- runnable stubs
    # study/scenarios/       <- executor
    import_root = tmp_path / "study"
    import_root.mkdir()

    gen_dir = import_root / "generated"
    generate_lib(all_problem_defs, gen_dir)
    lib_dir = gen_dir / "lib"

    disciplines_dir = import_root / "disciplines"
    disciplines_dir.mkdir()
    (disciplines_dir / "__init__.py").write_text("", encoding="utf-8")
    generate_disciplines(
        all_problem_defs, disciplines_dir, lib_dir, import_root, runnable=True
    )

    scenarios_dir = import_root / "scenarios"
    generate_scenario_executor(
        all_problem_defs, scenarios_dir, lib_dir, disciplines_dir, import_root
    )
    # generate_scenario_executor creates __init__.py in scenarios_dir automatically

    from gemseo.scenarios.base_scenario import BaseScenario

    sys.path.insert(0, str(import_root))
    imported = []
    try:
        for scenario in all_problem_defs.scenarios:
            mod_name = f"scenarios.execute_{scenario.name}"
            mod = importlib.import_module(mod_name)
            imported.append(mod_name)
            execute_fn = getattr(mod, f"execute_{scenario.name}")
            result_scenario = execute_fn()
            assert isinstance(result_scenario, BaseScenario)
    finally:
        for mod_name in imported:
            sys.modules.pop(mod_name, None)
        for key in list(sys.modules.keys()):
            if key.startswith(("scenarios.", "disciplines.", "generated.")):
                sys.modules.pop(key, None)
        for bare in ("scenarios", "disciplines", "generated"):
            sys.modules.pop(bare, None)
        sys.path.remove(str(import_root))
