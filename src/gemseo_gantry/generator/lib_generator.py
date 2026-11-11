import keyword
import shutil
from pathlib import Path

import black
import pandas as pd
from isort import code as isort_code
from jinja2 import Environment, FileSystemLoader

from gemseo_gantry.artifacts import ArtifactKind, GeneratedArtifact
from gemseo_gantry.model.data_model import DataType, ProblemDefinition


def lib_import_root(lib_dest: Path, import_root: Path) -> str:
    """Dotted module path of `lib_dest`, measured from `import_root`.

    `import_root` is the directory on `sys.path` from which the user's project is
    importable - e.g. the `src/` directory in a src-layout project, or the project
    root if that is what is on the path. It is NOT necessarily the repo/project root;
    it is specifically the path entry that makes the user's packages importable.

    The returned dotted name is what scaffold files use to import lib by an absolute,
    relocation-proof path. lib's own internal imports stay relative and never use it.

    Example:
        import_root = <repo>/src
        lib_dest    = <repo>/src/myproject/generated/lib
        returns     "myproject.generated.lib"

    Raises:
        ValueError: if `import_root` is not an existing directory, if `lib_dest` is not
            located under `import_root`, or if any path segment between them is not a
            valid Python identifier (and thus not importable).
    """
    import_root = import_root.resolve()
    lib_dest = lib_dest.resolve()

    if not import_root.is_dir():
        raise ValueError(
            f"import_root does not exist or is not a directory: {import_root}"
        )

    try:
        relative = lib_dest.relative_to(import_root)
    except ValueError:
        raise ValueError(
            f"lib_dest ({lib_dest}) is not located under import_root ({import_root}). lib must live somewhere inside the importable source root."
        )

    parts = relative.parts
    bad = [p for p in parts if not p.isidentifier() or keyword.iskeyword(p)]
    if bad:
        from slugify import slugify

        suggestions = [slugify(p, separator="_") for p in bad]
        raise ValueError(
            f"Path segment(s) {bad!r} between import_root and lib_dest are not valid Python identifiers "
            f"and cannot form an importable dotted name. "
            f"Rename using only letters, digits, and underscores (e.g. {suggestions!r})."
        )

    return ".".join(parts)


def _format_code(source: str) -> str:
    """Sort imports and format Python source code."""
    source = isort_code(source, profile="black")
    return black.format_str(source, mode=black.Mode())


def discipline_io_filename(name: str) -> str:
    """Build the lib IO-dataclass module filename from a discipline name.

    Args:
        name: The discipline name (e.g. 'Drag').

    Returns:
        The module filename (e.g. 'Drag_io.py').
    """
    return f"{name}_io.py"


def discipline_base_filename(name: str) -> str:
    """Build the lib base-class module filename from a discipline name.

    Args:
        name: The discipline name (e.g. 'Drag').

    Returns:
        The module filename (e.g. 'Drag_base.py').
    """
    return f"{name}_base.py"


def scenario_filename(name: str) -> str:
    """Build the lib scenario-construction module filename from a scenario name.

    Args:
        name: The scenario name (e.g. 'MyScenario').

    Returns:
        The module filename (e.g. 'MyScenario.py').
    """
    return f"{name}.py"


def _display_description(description: str | None, unit: str | None) -> str:
    """Combine description and unit into a display string.

    Args:
        description: The description text, or None.
        unit: The unit text, or None.

    Returns:
        A formatted string like "Orbit altitude [km]" (with unit in brackets),
        or "Orbit altitude" (without unit), or "[km]" (unit only), or ""
        (empty string if both are missing). Whitespace is stripped.
    """
    desc = (description or "").strip()
    unit_str = (unit or "").strip()
    unit_formatted = f"[{unit_str}]" if unit_str else ""
    return f"{desc} {unit_formatted}".strip()


def generate_variables(
    problem: ProblemDefinition, output_dir: Path
) -> list[GeneratedArtifact]:
    """
    Generates the variables.py file with an enum of all problem variables.

    Args:
        problem: The parsed problem definition.
        output_dir: The directory where the generated code should be saved.

    Returns:
        List of generated artifacts.
    """
    env = Environment(loader=FileSystemLoader(Path(__file__).parent / "templates"))
    template = env.get_template("variables.jinja")

    variables_list = []
    for var in problem.variables:
        variables_list.append(
            {
                "name": var.name,
                "description": _display_description(var.description, var.unit),
            }
        )

    content = template.render(variables=variables_list)
    content = _format_code(content)
    out = output_dir / "variables.py"
    out.write_text(content, encoding="utf-8")
    return [GeneratedArtifact(out, ArtifactKind.VARIABLES)]


def generate_design_space(
    problem: ProblemDefinition, output_dir: Path
) -> list[GeneratedArtifact]:
    """
    Generates the design_space.csv file with design variables.

    Args:
        problem: The parsed problem definition.
        output_dir: The directory where the generated CSV should be saved.

    Returns:
        List of generated artifacts.
    """
    out = output_dir / "design_space.csv"
    df = pd.DataFrame(problem.design_space)
    df.to_csv(out, index=False)
    return [GeneratedArtifact(out, ArtifactKind.DESIGN_SPACE)]


def _grammar_type(data_type: DataType) -> str:
    """Pydantic field annotation enforcing dtype for a grammar field."""
    if data_type is DataType.INTEGER:
        return "NDArrayPydantic[np.int64]"
    return "NDArrayPydantic"


def generate_discipline_grammars(
    problem: ProblemDefinition, output_dir: Path
) -> list[GeneratedArtifact]:
    """
    Generates Pydantic grammar modules for discipline inputs and outputs.

    Args:
        problem: The parsed problem definition.
        output_dir: The directory where the generated grammar modules should be saved.

    Returns:
        List of generated artifacts.
    """
    env = Environment(loader=FileSystemLoader(Path(__file__).parent / "templates"))
    template = env.get_template("grammar.jinja")

    var_map = {var.name: var for var in problem.variables}
    written: list[GeneratedArtifact] = []

    for discipline in problem.disciplines:
        input_fields = [
            {
                "name": var_name,
                "default_values": var_map[var_name].default_values()
                if var_name in var_map
                else None,
                "description": _display_description(
                    var_map[var_name].description, var_map[var_name].unit
                )
                if var_name in var_map
                else None,
                "grammar_type": _grammar_type(var_map[var_name].data_type)
                if var_name in var_map
                else _grammar_type(DataType.FLOAT),
            }
            for var_name in sorted(discipline.inputs)
        ]
        output_fields = [
            {
                "name": var_name,
                "description": _display_description(
                    var_map[var_name].description, var_map[var_name].unit
                )
                if var_name in var_map
                else None,
                "grammar_type": _grammar_type(var_map[var_name].data_type)
                if var_name in var_map
                else _grammar_type(DataType.FLOAT),
            }
            for var_name in sorted(discipline.outputs)
        ]
        has_defaults = any(f["default_values"] is not None for f in input_fields)
        has_integer_field = any(
            f["grammar_type"] != "NDArrayPydantic" for f in input_fields + output_fields
        )
        needs_numpy = has_defaults or has_integer_field
        needs_field = has_defaults or any(
            f["description"] for f in input_fields + output_fields
        )

        content = template.render(
            discipline_name=discipline.name,
            input_fields=input_fields,
            output_fields=output_fields,
            has_defaults=has_defaults,
            needs_numpy=needs_numpy,
            needs_field=needs_field,
        )
        content = _format_code(content)
        file_path = output_dir / f"{discipline.name}_grammar.py"
        file_path.write_text(content, encoding="utf-8")
        written.append(GeneratedArtifact(file_path, ArtifactKind.DISCIPLINE_GRAMMAR))
    return written


def _io_field_type(data_type: DataType) -> str:
    """Per-field numpy annotation for IO dataclasses."""
    if data_type is DataType.INTEGER:
        return "np.integer"
    return "np.floating"


def _io_common_type(data_types: list[DataType]) -> str:
    """Shared numpy base type for a discipline's fields.

    `np.number` is not a supertype dtype-checkers accept for narrower fields
    (e.g. `np.integer`), so mixed-type disciplines fall back to `Any`.
    """
    unique = set(data_types)
    if len(unique) == 1:
        return _io_field_type(unique.pop())
    return "Any"


def generate_discipline_io(
    problem: ProblemDefinition, output_dir: Path
) -> list[GeneratedArtifact]:
    """
    Generates the <discipline>_io.py files with input/output dataclasses for each discipline.

    Args:
        problem: The parsed problem definition.
        output_dir: The directory where the generated code should be saved.

    Returns:
        List of generated artifacts.
    """
    env = Environment(loader=FileSystemLoader(Path(__file__).parent / "templates"))
    template = env.get_template("discipline_io.jinja")

    var_map = {var.name: var for var in problem.variables}
    written: list[GeneratedArtifact] = []

    for discipline in problem.disciplines:
        input_fields = [
            {
                "name": name,
                "np_type": _io_field_type(var_map[name].data_type)
                if name in var_map
                else _io_field_type(DataType.FLOAT),
            }
            for name in discipline.inputs
        ]
        output_fields = [
            {
                "name": name,
                "np_type": _io_field_type(var_map[name].data_type)
                if name in var_map
                else _io_field_type(DataType.FLOAT),
            }
            for name in discipline.outputs
        ]
        inputs_dict_type = _io_common_type(
            [
                var_map[name].data_type if name in var_map else DataType.FLOAT
                for name in discipline.inputs
            ]
        )
        outputs_dict_type = _io_common_type(
            [
                var_map[name].data_type if name in var_map else DataType.FLOAT
                for name in discipline.outputs
            ]
        )

        content = template.render(
            discipline_name=discipline.name,
            input_fields=input_fields,
            output_fields=output_fields,
            inputs_dict_type=inputs_dict_type,
            outputs_dict_type=outputs_dict_type,
            needs_any="Any" in (inputs_dict_type, outputs_dict_type),
        )
        content = _format_code(content)
        file_path = output_dir / discipline_io_filename(discipline.name)
        file_path.write_text(content, encoding="utf-8")
        written.append(GeneratedArtifact(file_path, ArtifactKind.DISCIPLINE_IO))
    return written


def generate_discipline_bases(
    problem: ProblemDefinition, output_dir: Path
) -> list[GeneratedArtifact]:
    """
    Generates the <discipline>_base.py files with grammar-wiring base classes for each discipline.

    Args:
        problem: The parsed problem definition.
        output_dir: The directory where the generated code should be saved.

    Returns:
        List of generated artifacts.
    """
    env = Environment(loader=FileSystemLoader(Path(__file__).parent / "templates"))
    template = env.get_template("discipline_base.jinja")
    written: list[GeneratedArtifact] = []

    for discipline in problem.disciplines:
        content = template.render(discipline_name=discipline.name)
        content = _format_code(content)
        file_path = output_dir / discipline_base_filename(discipline.name)
        file_path.write_text(content, encoding="utf-8")
        written.append(GeneratedArtifact(file_path, ArtifactKind.DISCIPLINE_BASE))
    return written


def generate_discipline_scaffold(
    problem: ProblemDefinition,
    output_dir: Path,
    lib_package: str,
    runnable: bool = False,
) -> None:
    """
    Generates the <discipline>_scaffold.py files with scaffold implementations for each discipline.

    Args:
        problem: The parsed problem definition.
        output_dir: The directory where the generated code should be saved.
        lib_package: The package path used to import grammar and IO modules.
        runnable: When True, _run returns placeholder outputs instead of raising
            NotImplementedError. Useful for end-to-end smoke tests.
    """
    env = Environment(loader=FileSystemLoader(Path(__file__).parent / "templates"))
    template = env.get_template("discipline_scaffold.jinja")

    var_map = {var.name: var for var in problem.variables}

    for discipline in problem.disciplines:
        inputs = sorted(discipline.inputs)
        outputs = [
            {
                "name": name,
                "dimension": var_map[name].dimension if name in var_map else 1,
            }
            for name in sorted(discipline.outputs)
        ]

        content = template.render(
            discipline_name=discipline.name,
            inputs=inputs,
            outputs=outputs,
            lib_package=lib_package,
            runnable=runnable,
        )
        content = _format_code(content)
        file_name = f"{discipline.name}_scaffold.py"
        file_path = output_dir / file_name
        file_path.write_text(content, encoding="utf-8")


def generate_scenario(
    problem: ProblemDefinition, output_dir: Path
) -> list[GeneratedArtifact]:
    """
    Generates one <ScenarioName>.py file per scenario in the problem definition.

    Args:
        problem: The parsed problem definition.
        output_dir: The directory where the generated code should be saved.

    Returns:
        List of generated artifacts.
    """
    env = Environment(loader=FileSystemLoader(Path(__file__).parent / "templates"))
    template = env.get_template("scenario.jinja")
    written: list[GeneratedArtifact] = []

    for scenario in problem.scenarios:
        context = {
            "scenario_name": scenario.name,
            "scenario_type": scenario.formulation_type,
            "maximize_objective": scenario.objective.maximize,
            "design_variables": sorted(scenario.design_variables),
            "objective": scenario.objective.variable,
            "plain_disciplines": sorted(problem.plain_discipline_names_of(scenario)),
            "sub_scenarios": sorted(problem.sub_scenario_names_of(scenario)),
            "constraints": [
                {
                    "var": constraint.variable,
                    "type": constraint.constraint_type,
                    "value": constraint.value,
                    "positive": constraint.positive,
                }
                for constraint in scenario.constraints
            ],
            "observables": scenario.observables,
        }

        content = template.render(**context)
        content = _format_code(content)
        file_path = output_dir / scenario_filename(scenario.name)
        file_path.write_text(content, encoding="utf-8")
        written.append(GeneratedArtifact(file_path, ArtifactKind.SCENARIO))
    return written


def generate_lib(
    problem: ProblemDefinition,
    output_dir: Path,
    lib_name: str = "lib",
    is_import_root: bool = False,
) -> list[GeneratedArtifact]:
    """
    Regenerates the lib package from the problem definition. Destructive and idempotent.

    Creates output_dir/ and (when not the import root) output_dir/__init__.py, then
    wipes and rebuilds output_dir/<lib_name>/. Never touches scaffold/ or any other directory.

    Generated layout (nested, default)::

        output_dir/
            __init__.py
            <lib_name>/
                __init__.py
                ...

    Generated layout (flat, ``is_import_root=True``)::

        output_dir/
            <lib_name>/
                __init__.py
                ...

    Args:
        problem: The parsed problem definition.
        output_dir: The root directory for generated lib files.
        lib_name: Name of the generated lib package directory. Defaults to ``"lib"``.
        is_import_root: When True, skip writing ``output_dir/__init__.py``. Use this
            when ``output_dir`` is directly on ``sys.path`` (flat layout); writing an
            ``__init__.py`` there would make the import root look like a package and
            break type-checker path resolution.

    Returns:
        List of generated artifacts under ``output_dir/lib_name/``, all with
        ``status=WRITTEN``. The outer ``output_dir/__init__.py`` is written as a
        packaging side effect but intentionally not included in the returned list.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    outer_init = output_dir / "__init__.py"
    if not is_import_root and not outer_init.exists():
        # packaging side effect; intentionally not reported as an artifact
        outer_init.write_text("", encoding="utf-8")

    lib_dir = output_dir / lib_name
    if lib_dir.exists():
        shutil.rmtree(lib_dir)
    lib_dir.mkdir()

    artifacts: list[GeneratedArtifact] = []
    init_path = lib_dir / "__init__.py"
    init_path.write_text("", encoding="utf-8")
    artifacts.append(GeneratedArtifact(init_path, ArtifactKind.PACKAGE_INIT))

    artifacts += generate_variables(problem, lib_dir)
    artifacts += generate_discipline_grammars(problem, lib_dir)
    artifacts += generate_discipline_io(problem, lib_dir)
    artifacts += generate_discipline_bases(problem, lib_dir)
    artifacts += generate_design_space(problem, lib_dir)
    artifacts += generate_scenario(problem, lib_dir)
    return artifacts
