import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from gemseo_gantry.artifacts import ArtifactKind, ArtifactStatus, GeneratedArtifact
from gemseo_gantry.generator.lib_generator import (
    _format_code,
    discipline_base_filename,
    discipline_io_filename,
    lib_import_root,
    scenario_filename,
)
from gemseo_gantry.model.data_model import FormulationType, ProblemDefinition


def _pascal_to_snake(s: str) -> str:
    """Convert PascalCase to snake_case."""
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", s).lower()


_FORMULATION_SETTINGS: dict[FormulationType, tuple[str, str]] = {
    FormulationType.MDF: ("gemseo.formulations.mdf_settings", "MDF_Settings"),
    FormulationType.BILEVEL: (
        "gemseo.formulations.bilevel_settings",
        "BiLevel_Settings",
    ),
    FormulationType.BILEVEL_BCD: (
        "gemseo.formulations.bilevel_bcd_settings",
        "BiLevel_BCD_Settings",
    ),
}


ALL_ARTIFACTS: frozenset[str] = frozenset({"disciplines", "executor", "loader"})


def required_lib_modules(
    problem: ProblemDefinition, artifacts: frozenset[str]
) -> list[str]:
    """List the lib modules that the requested seeds import.

    Args:
        problem: The parsed problem definition.
        artifacts: Which artifacts will be generated (see :data:`ALL_ARTIFACTS`).

    Returns:
        Module filenames relative to the lib directory, deduplicated, in order of
        first use. The loader imports nothing from lib, so it contributes none.
    """
    names: list[str] = []
    if "disciplines" in artifacts:
        for discipline in problem.disciplines:
            names.append(discipline_base_filename(discipline.name))
            names.append(discipline_io_filename(discipline.name))
    if "executor" in artifacts:
        for root in problem.root_scenarios:
            names.extend(
                scenario_filename(scenario.name)
                for scenario in problem.construction_order(root)
            )
    return list(dict.fromkeys(names))


def _check_lib_built(
    problem: ProblemDefinition, lib_dir: Path, artifacts: frozenset[str]
) -> None:
    """Raise ``FileNotFoundError`` unless ``lib_dir`` has every required module."""
    required = required_lib_modules(problem, artifacts)
    missing = sorted(name for name in required if not (lib_dir / name).is_file())
    if not missing:
        return
    if not lib_dir.is_dir():
        raise FileNotFoundError(f"No generated lib found at {lib_dir}/.")
    raise FileNotFoundError(
        f"The lib at {lib_dir}/ is missing {', '.join(missing)}; it is out of date "
        "or was built from a different problem definition."
    )


def discipline_scaffold_filename(name: str) -> str:
    """Build the discipline scaffold filename from a discipline name.

    Args:
        name: The discipline name (e.g. 'Drag').

    Returns:
        The scaffold filename (e.g. 'Drag_scaffold.py').
    """
    return f"{name}_scaffold.py"


def executor_filename(name: str) -> str:
    """Build the scenario executor filename from a scenario name.

    Args:
        name: The scenario name (e.g. 'MyScenario').

    Returns:
        The executor filename (e.g. 'execute_MyScenario.py').
    """
    return f"execute_{name}.py"


def loader_filename(name: str) -> str:
    """Build the scenario loader filename from a scenario name.

    Args:
        name: The scenario name (e.g. 'MyScenario').

    Returns:
        The loader filename (e.g. 'load_MyScenario.py').
    """
    return f"load_{name}.py"


def generate_disciplines(
    problem: ProblemDefinition,
    target_dir: Path,
    lib_dir: Path,
    import_root: Path,
    force: bool = False,
    runnable: bool = False,
) -> list[GeneratedArtifact]:
    """Write-once discipline scaffold into target_dir.

    For each discipline in `problem`, writes `<DisciplineName>_scaffold.py` into
    `target_dir`. Skips existing files unless `force=True`. `target_dir` is created
    if absent.

    Args:
        problem: The parsed problem definition.
        target_dir: Directory to write scaffold files into. Created if absent.
        lib_dir: Path to the generated lib/ directory.
        import_root: sys.path root for absolute imports (e.g. src/).
        force: When True, overwrite existing files. Default False.
        runnable: When True, _run returns placeholder outputs instead of raising
            NotImplementedError. Default False.

    Returns:
        List of :class:`~gemseo_gantry.artifacts.GeneratedArtifact` with kind
        ``DISCIPLINE_SCAFFOLD`` and status ``WRITTEN`` or ``SKIPPED`` per file.
    """
    target_dir = Path(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    lib_package = lib_import_root(Path(lib_dir), Path(import_root))
    var_map = {var.name: var for var in problem.variables}

    env = Environment(loader=FileSystemLoader(Path(__file__).parent / "templates"))
    template = env.get_template("discipline_scaffold.jinja")

    out: list[GeneratedArtifact] = []

    for discipline in problem.disciplines:
        file_path = target_dir / discipline_scaffold_filename(discipline.name)
        if file_path.exists() and not force:
            out.append(
                GeneratedArtifact(
                    file_path, ArtifactKind.DISCIPLINE_SCAFFOLD, ArtifactStatus.SKIPPED
                )
            )
            continue

        content = template.render(
            discipline_name=discipline.name,
            inputs=sorted(discipline.inputs),
            outputs=[
                {
                    "name": name,
                    "dimension": var_map[name].dimension if name in var_map else 1,
                }
                for name in sorted(discipline.outputs)
            ],
            lib_package=lib_package,
            runnable=runnable,
        )
        content = _format_code(content)
        file_path.write_text(content, encoding="utf-8")
        out.append(
            GeneratedArtifact(
                file_path, ArtifactKind.DISCIPLINE_SCAFFOLD, ArtifactStatus.WRITTEN
            )
        )

    return out


def generate_scenario_executor(
    problem: ProblemDefinition,
    target_dir: Path,
    lib_dir: Path,
    disciplines_dir: Path,
    import_root: Path,
    force: bool = False,
) -> list[GeneratedArtifact]:
    """Write-once scenario executor into target_dir.

    For the problem's scenario(s), writes ``execute_<ScenarioName>.py`` into
    ``target_dir``. Skips existing files unless ``force=True``. ``target_dir`` is
    created (along with an ``__init__.py``) if absent.

    Args:
        problem: The parsed problem definition.
        target_dir: Directory to write executor file(s) into. Created if absent.
        lib_dir: Path to the generated lib/ directory.
        disciplines_dir: Path to the discipline stubs directory.
        import_root: sys.path root for absolute imports (e.g. src/).
        force: When True, overwrite existing files. Default False.

    Returns:
        List of :class:`~gemseo_gantry.artifacts.GeneratedArtifact` with kind
        ``EXECUTOR`` per scenario file (and ``PACKAGE_INIT`` when ``__init__.py`` is
        newly created), each with status ``WRITTEN`` or ``SKIPPED``.
    """
    target_dir = Path(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    out: list[GeneratedArtifact] = []

    init_file = target_dir / "__init__.py"
    if not init_file.exists():
        init_file.write_text("", encoding="utf-8")
        out.append(
            GeneratedArtifact(
                init_file, ArtifactKind.PACKAGE_INIT, ArtifactStatus.WRITTEN
            )
        )

    lib_package = lib_import_root(Path(lib_dir), Path(import_root))
    discipline_package = lib_import_root(Path(disciplines_dir), Path(import_root))

    env = Environment(loader=FileSystemLoader(Path(__file__).parent / "templates"))
    template = env.get_template("execute_scaffold.jinja")

    for root in problem.root_scenarios:
        file_path = target_dir / executor_filename(root.name)
        if file_path.exists() and not force:
            out.append(
                GeneratedArtifact(
                    file_path, ArtifactKind.EXECUTOR, ArtifactStatus.SKIPPED
                )
            )
            continue

        # Build the template context for this root's executor. Walk the
        # scenarios in construction order (sub-scenarios before parents) and,
        # for each, collect: its per-scenario render block (`scenarios_ctx`),
        # the union of plain discipline names across all scenarios (for the
        # import block, deduplicated but order-preserving), and the set of
        # formulation-settings classes to import (`formulation_imports`).
        ordered = problem.construction_order(root)
        scenarios_ctx = []
        plain_disc_names: list[str] = []
        formulation_imports: dict[str, str] = {}
        for scenario in ordered:
            formulation = problem.resolve_formulation(scenario)
            module, cls = _FORMULATION_SETTINGS[formulation]
            formulation_imports[cls] = module
            plain = sorted(problem.plain_discipline_names_of(scenario))
            for name in plain:
                if name not in plain_disc_names:
                    plain_disc_names.append(name)
            scenarios_ctx.append(
                {
                    "name": scenario.name,
                    "var": _pascal_to_snake(scenario.name),
                    "is_root": scenario.name == root.name,
                    "plain_disciplines": plain,
                    "sub_scenarios": [
                        {"field": sub, "var": _pascal_to_snake(sub)}
                        for sub in sorted(problem.sub_scenario_names_of(scenario))
                    ],
                    "settings_cls": cls,
                }
            )

        content = template.render(
            root_name=root.name,
            root_var=_pascal_to_snake(root.name),
            root_is_doe=root.formulation_type == "DOE",
            scenarios=scenarios_ctx,
            disciplines=sorted(plain_disc_names),
            lib_package=lib_package,
            discipline_package=discipline_package,
            formulation_imports=[
                {"cls": cls, "module": module}
                for cls, module in formulation_imports.items()
            ],
        )
        content = _format_code(content)
        file_path.write_text(content, encoding="utf-8")
        out.append(
            GeneratedArtifact(file_path, ArtifactKind.EXECUTOR, ArtifactStatus.WRITTEN)
        )

    return out


def generate_scenario_loader(
    problem: ProblemDefinition,
    target_dir: Path,
    force: bool = False,
) -> list[GeneratedArtifact]:
    """Write-once scenario data-loader script into target_dir.

    For each scenario in `problem`, writes ``load_<ScenarioName>.py`` into
    ``target_dir``. Skips existing files unless ``force=True``. ``target_dir`` is
    created if absent.

    Args:
        problem: The parsed problem definition.
        target_dir: Directory to write loader file(s) into. Created if absent.
        force: When True, overwrite existing files. Default False.

    Returns:
        List of :class:`~gemseo_gantry.artifacts.GeneratedArtifact` with kind
        ``POSTPROCESSOR`` and status ``WRITTEN`` or ``SKIPPED`` per file.
    """
    target_dir = Path(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    env = Environment(loader=FileSystemLoader(Path(__file__).parent / "templates"))
    template = env.get_template("load_scenario.jinja")

    out: list[GeneratedArtifact] = []

    for scenario in problem.root_scenarios:
        file_path = target_dir / loader_filename(scenario.name)
        if file_path.exists() and not force:
            out.append(
                GeneratedArtifact(
                    file_path, ArtifactKind.POSTPROCESSOR, ArtifactStatus.SKIPPED
                )
            )
            continue

        content = template.render(scenario_name=scenario.name)
        content = _format_code(content)
        file_path.write_text(content, encoding="utf-8")
        out.append(
            GeneratedArtifact(
                file_path, ArtifactKind.POSTPROCESSOR, ArtifactStatus.WRITTEN
            )
        )

    return out


def generate_scaffold(
    problem: ProblemDefinition,
    *,
    disciplines_into: Path,
    lib_dir: Path,
    executor_into: Path | None = None,
    import_root: Path | None = None,
    artifacts: frozenset[str] = ALL_ARTIFACTS,
    force: bool = False,
    runnable: bool = False,
) -> list[GeneratedArtifact]:
    """Generate discipline stubs and scenario executor/loader files.

    Args:
        problem: Parsed problem definition.
        disciplines_into: Directory for discipline stub files. Created if absent.
        lib_dir: Path to the generated lib/ directory (output of :func:`generate_lib`).
        executor_into: Directory for executor and loader files. Defaults to
            ``disciplines_into.parent`` when ``None``.
        import_root: sys.path root for absolute import-path computation. Defaults to
            ``Path.cwd()`` when ``None``.
        artifacts: Which artifacts to generate. Defaults to all three:
            ``frozenset({"disciplines", "executor", "loader"})``.
        force: When True, overwrite existing files. Default False.
        runnable: When True, discipline stubs return placeholder outputs instead of
            raising ``NotImplementedError``. Default False.

    Returns:
        Flat list of :class:`~gemseo_gantry.artifacts.GeneratedArtifact` in order:
        disciplines, executor (including ``PACKAGE_INIT`` when newly created), loader.

    Raises:
        FileNotFoundError: If ``lib_dir`` lacks a module the requested seeds
            import. Checked before anything is written.
    """
    lib_dir = Path(lib_dir)
    _check_lib_built(problem, lib_dir, artifacts)
    resolved_executor_into = (
        executor_into if executor_into is not None else disciplines_into.parent
    )
    resolved_import_root = import_root if import_root is not None else Path.cwd()

    out: list[GeneratedArtifact] = []

    if "disciplines" in artifacts:
        out += generate_disciplines(
            problem,
            disciplines_into,
            lib_dir,
            resolved_import_root,
            force=force,
            runnable=runnable,
        )
    if "executor" in artifacts:
        out += generate_scenario_executor(
            problem,
            resolved_executor_into,
            lib_dir,
            disciplines_into,
            resolved_import_root,
            force=force,
        )
    if "loader" in artifacts:
        out += generate_scenario_loader(
            problem,
            resolved_executor_into,
            force=force,
        )

    return out
