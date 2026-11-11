from pathlib import Path

import pytest

from gemseo_gantry.artifacts import ArtifactKind, ArtifactStatus

_TOML_PATH = Path(__file__).parent.parent.parent / "fixtures" / "vleo.toml"


def _discipline_names():
    from gemseo_gantry.parser.toml_parser import parse_toml

    return [d.name for d in parse_toml(_TOML_PATH).disciplines]


DISCIPLINE_NAMES = _discipline_names()


@pytest.fixture(scope="module")
def lib_setup(problem_def, tmp_path_factory):
    """Generate lib/ once; return (lib_dir, import_root) for use by scaffold fixtures."""
    from gemseo_gantry.generator.lib_generator import generate_lib

    root = tmp_path_factory.mktemp("scaffold_gen_root")
    gen_dir = root / "generated"
    generate_lib(problem_def, gen_dir)
    return gen_dir / "lib", root


@pytest.fixture(scope="module")
def scaffold_dir(problem_def, lib_setup, tmp_path_factory):
    """Generate default (non-runnable) scaffold files once for the module."""
    from gemseo_gantry.generator.scaffold_generator import generate_disciplines

    lib_dir, import_root = lib_setup
    out = tmp_path_factory.mktemp("scaffold_default")
    generate_disciplines(problem_def, out, lib_dir, import_root, runnable=False)
    return out


@pytest.fixture(scope="module")
def scaffold_runnable_dir(problem_def, lib_setup, tmp_path_factory):
    """Generate runnable scaffold files once for the module."""
    from gemseo_gantry.generator.scaffold_generator import generate_disciplines

    lib_dir, import_root = lib_setup
    out = tmp_path_factory.mktemp("scaffold_runnable")
    generate_disciplines(problem_def, out, lib_dir, import_root, runnable=True)
    return out


def test_generate_disciplines_complete(problem_def, scaffold_dir):
    """generate_disciplines() emits one *_scaffold.py per discipline."""
    generated = {
        f.stem.replace("_scaffold", "") for f in scaffold_dir.glob("*_scaffold.py")
    }
    assert generated == {d.name for d in problem_def.disciplines}


@pytest.mark.parametrize("discipline", DISCIPLINE_NAMES)
def test_generate_disciplines(scaffold_dir, snapshot, discipline):
    content = (scaffold_dir / f"{discipline}_scaffold.py").read_text(encoding="utf-8")
    assert content == snapshot


@pytest.mark.parametrize("discipline", DISCIPLINE_NAMES)
def test_generate_disciplines_runnable(scaffold_runnable_dir, snapshot, discipline):
    content = (scaffold_runnable_dir / f"{discipline}_scaffold.py").read_text(
        encoding="utf-8"
    )
    assert content == snapshot


def test_generate_disciplines_vector_output_uses_np_zeros(tmp_path):
    """generate_disciplines() sizes scaffold placeholders to each output's dimension."""
    from gemseo_gantry.generator.lib_generator import generate_lib
    from gemseo_gantry.generator.scaffold_generator import generate_disciplines
    from gemseo_gantry.model.data_model import Discipline, ProblemDefinition, Variable

    problem = ProblemDefinition(
        variables=[
            Variable(name="x", data_type="float", dimension=1),
            Variable(name="y", data_type="float", dimension=4),
        ],
        disciplines=[Discipline(name="Disc", inputs=["x"], outputs=["y"])],
    )

    import_root = tmp_path / "root"
    import_root.mkdir()
    gen_dir = import_root / "generated"
    generate_lib(problem, gen_dir)
    lib_dir = gen_dir / "lib"

    target_dir = import_root / "disciplines"
    generate_disciplines(problem, target_dir, lib_dir, import_root)

    content = (target_dir / "Disc_scaffold.py").read_text(encoding="utf-8")
    assert "np.zeros(4)" in content
    assert "np.array([0.0])" not in content


# -- generate_scenario_executor ------------------------------------------------


@pytest.fixture(scope="module")
def executor_setup(problem_def, lib_setup, tmp_path_factory):
    """Generate scenario executor once for snapshot tests."""
    from gemseo_gantry.generator.scaffold_generator import generate_scenario_executor

    lib_dir, import_root = lib_setup
    disciplines_dir = import_root / "disciplines"
    disciplines_dir.mkdir(exist_ok=True)
    out = tmp_path_factory.mktemp("executor_out")
    generate_scenario_executor(problem_def, out, lib_dir, disciplines_dir, import_root)
    return out


def test_generate_scenario_executor_snapshot(problem_def, executor_setup, snapshot):
    """Rendered executor content matches snapshot."""
    for scenario in problem_def.scenarios:
        content = (executor_setup / f"execute_{scenario.name}.py").read_text(
            encoding="utf-8"
        )
        assert content == snapshot


def test_generate_scenario_executor_write_once(problem_def, lib_setup, tmp_path):
    """Second call with same target_dir skips the file; content is unchanged."""
    from gemseo_gantry.generator.scaffold_generator import generate_scenario_executor

    lib_dir, import_root = lib_setup
    disciplines_dir = import_root / "disciplines"
    disciplines_dir.mkdir(exist_ok=True)

    arts1 = generate_scenario_executor(
        problem_def, tmp_path, lib_dir, disciplines_dir, import_root
    )
    written1 = {
        a.path.stem.removeprefix("execute_")
        for a in arts1
        if a.kind is ArtifactKind.EXECUTOR and a.status is ArtifactStatus.WRITTEN
    }
    skipped1 = [
        a
        for a in arts1
        if a.kind is ArtifactKind.EXECUTOR and a.status is ArtifactStatus.SKIPPED
    ]
    assert written1 == {s.name for s in problem_def.scenarios}
    assert skipped1 == []

    first_contents = {
        s.name: (tmp_path / f"execute_{s.name}.py").read_bytes()
        for s in problem_def.scenarios
    }

    arts2 = generate_scenario_executor(
        problem_def, tmp_path, lib_dir, disciplines_dir, import_root
    )
    skipped2 = {
        a.path.stem.removeprefix("execute_")
        for a in arts2
        if a.kind is ArtifactKind.EXECUTOR and a.status is ArtifactStatus.SKIPPED
    }
    written2 = [
        a
        for a in arts2
        if a.kind is ArtifactKind.EXECUTOR and a.status is ArtifactStatus.WRITTEN
    ]
    assert skipped2 == {s.name for s in problem_def.scenarios}
    assert written2 == []
    for s in problem_def.scenarios:
        assert (tmp_path / f"execute_{s.name}.py").read_bytes() == first_contents[
            s.name
        ]


def test_generate_scenario_executor_force(problem_def, lib_setup, tmp_path):
    """force=True overwrites existing file; result contains WRITTEN EXECUTOR artifact."""
    from gemseo_gantry.generator.scaffold_generator import generate_scenario_executor

    lib_dir, import_root = lib_setup
    disciplines_dir = import_root / "disciplines"
    disciplines_dir.mkdir(exist_ok=True)

    generate_scenario_executor(
        problem_def, tmp_path, lib_dir, disciplines_dir, import_root
    )

    first_scenario = problem_def.scenarios[0]
    executor_file = tmp_path / f"execute_{first_scenario.name}.py"
    original_content = executor_file.read_bytes()
    executor_file.write_text("# mutated", encoding="utf-8")

    arts = generate_scenario_executor(
        problem_def, tmp_path, lib_dir, disciplines_dir, import_root, force=True
    )
    written = {
        a.path.stem.removeprefix("execute_")
        for a in arts
        if a.kind is ArtifactKind.EXECUTOR and a.status is ArtifactStatus.WRITTEN
    }
    skipped = [
        a
        for a in arts
        if a.kind is ArtifactKind.EXECUTOR and a.status is ArtifactStatus.SKIPPED
    ]
    assert written == {s.name for s in problem_def.scenarios}
    assert skipped == []
    assert executor_file.read_bytes() == original_content


def test_generate_scenario_executor_creates_init(problem_def, lib_setup, tmp_path):
    """generate_scenario_executor() creates __init__.py in a new target_dir."""
    from gemseo_gantry.generator.scaffold_generator import generate_scenario_executor

    lib_dir, import_root = lib_setup
    disciplines_dir = import_root / "disciplines"
    disciplines_dir.mkdir(exist_ok=True)
    target_dir = tmp_path / "new_scenarios"

    generate_scenario_executor(
        problem_def, target_dir, lib_dir, disciplines_dir, import_root
    )

    assert (target_dir / "__init__.py").exists()


def test_generate_scenario_executor_root_level_disciplines(
    problem_def, lib_setup, tmp_path
):
    """disciplines_dir == import_root generates unqualified imports (no package prefix)."""
    from gemseo_gantry.generator.scaffold_generator import generate_scenario_executor

    lib_dir, import_root = lib_setup

    generate_scenario_executor(problem_def, tmp_path, lib_dir, import_root, import_root)

    for scenario in problem_def.scenarios:
        content = (tmp_path / f"execute_{scenario.name}.py").read_text(encoding="utf-8")
        for disc in scenario.disciplines:
            assert f"from {disc}_scaffold import {disc}" in content
            assert f"from .{disc}_scaffold" not in content


# -- generate_scenario_loader --------------------------------------------------


@pytest.fixture(scope="module")
def loader_setup(problem_def, tmp_path_factory):
    """Generate scenario loader once for snapshot tests."""
    from gemseo_gantry.generator.scaffold_generator import generate_scenario_loader

    out = tmp_path_factory.mktemp("loader_out")
    generate_scenario_loader(problem_def, out)
    return out


def test_generate_scenario_loader_snapshot(problem_def, loader_setup, snapshot):
    """Rendered loader content matches snapshot."""
    for scenario in problem_def.scenarios:
        content = (loader_setup / f"load_{scenario.name}.py").read_text(
            encoding="utf-8"
        )
        assert content == snapshot


def test_generate_scenario_loader_write_once(problem_def, tmp_path):
    """Second call with same target_dir skips the file; content is unchanged."""
    from gemseo_gantry.generator.scaffold_generator import generate_scenario_loader

    arts1 = generate_scenario_loader(problem_def, tmp_path)
    written1 = {
        a.path.stem.removeprefix("load_")
        for a in arts1
        if a.status is ArtifactStatus.WRITTEN
    }
    skipped1 = [a for a in arts1 if a.status is ArtifactStatus.SKIPPED]
    assert written1 == {s.name for s in problem_def.scenarios}
    assert skipped1 == []

    first_contents = {
        s.name: (tmp_path / f"load_{s.name}.py").read_bytes()
        for s in problem_def.scenarios
    }

    arts2 = generate_scenario_loader(problem_def, tmp_path)
    skipped2 = {
        a.path.stem.removeprefix("load_")
        for a in arts2
        if a.status is ArtifactStatus.SKIPPED
    }
    written2 = [a for a in arts2 if a.status is ArtifactStatus.WRITTEN]
    assert skipped2 == {s.name for s in problem_def.scenarios}
    assert written2 == []
    for s in problem_def.scenarios:
        assert (tmp_path / f"load_{s.name}.py").read_bytes() == first_contents[s.name]


def test_generate_lib_flat_layout_skips_outer_init(problem_def, tmp_path):
    """generate_lib with is_import_root=True must not write __init__.py at output_dir."""
    from gemseo_gantry.generator.lib_generator import generate_lib

    generate_lib(problem_def, tmp_path, is_import_root=True)

    assert not (tmp_path / "__init__.py").exists(), (
        "output_dir/__init__.py must not exist when output_dir is the import root"
    )
    assert (tmp_path / "lib" / "__init__.py").exists(), (
        "lib/__init__.py must always be written"
    )


def test_generate_lib_nested_layout_writes_outer_init(problem_def, tmp_path):
    """generate_lib default behaviour writes __init__.py at output_dir (nested layout)."""
    from gemseo_gantry.generator.lib_generator import generate_lib

    generate_lib(problem_def, tmp_path)

    assert (tmp_path / "__init__.py").exists()


def test_generate_lib_does_not_overwrite_existing_outer_init(problem_def, tmp_path):
    """generate_lib must not overwrite an existing output_dir/__init__.py."""
    from gemseo_gantry.generator.lib_generator import generate_lib

    init = tmp_path / "__init__.py"
    init.write_text("# user content", encoding="utf-8")

    generate_lib(problem_def, tmp_path)

    assert init.read_text(encoding="utf-8") == "# user content", (
        "generate_lib must not overwrite an existing output_dir/__init__.py"
    )


def test_generate_scenario_loader_force(problem_def, tmp_path):
    """force=True overwrites existing file; result contains WRITTEN POSTPROCESSOR artifact."""
    from gemseo_gantry.generator.scaffold_generator import generate_scenario_loader

    generate_scenario_loader(problem_def, tmp_path)

    first_scenario = problem_def.scenarios[0]
    loader_file = tmp_path / f"load_{first_scenario.name}.py"
    original_content = loader_file.read_bytes()
    loader_file.write_text("# mutated", encoding="utf-8")

    arts = generate_scenario_loader(problem_def, tmp_path, force=True)
    written = {
        a.path.stem.removeprefix("load_")
        for a in arts
        if a.status is ArtifactStatus.WRITTEN
    }
    skipped = [a for a in arts if a.status is ArtifactStatus.SKIPPED]
    assert written == {s.name for s in problem_def.scenarios}
    assert skipped == []
    assert loader_file.read_bytes() == original_content


# -- scaffold (public wrapper) -------------------------------------------------


def test_scaffold_all_artifacts(problem_def, tmp_path):
    from gemseo_gantry.generator.lib_generator import generate_lib
    from gemseo_gantry.generator.scaffold_generator import generate_scaffold

    generate_lib(problem_def, tmp_path / "out")
    arts = generate_scaffold(
        problem_def,
        disciplines_into=tmp_path / "disciplines",
        lib_dir=tmp_path / "out" / "lib",
        import_root=tmp_path,
    )

    assert isinstance(arts, list)
    kinds = {a.kind for a in arts}
    assert ArtifactKind.DISCIPLINE_SCAFFOLD in kinds
    assert ArtifactKind.EXECUTOR in kinds
    assert ArtifactKind.POSTPROCESSOR in kinds
    disc_written = [
        a
        for a in arts
        if a.kind is ArtifactKind.DISCIPLINE_SCAFFOLD
        and a.status is ArtifactStatus.WRITTEN
    ]
    assert len(disc_written) > 0


def test_scaffold_only_disciplines(problem_def, tmp_path):
    from gemseo_gantry.generator.lib_generator import generate_lib
    from gemseo_gantry.generator.scaffold_generator import generate_scaffold

    generate_lib(problem_def, tmp_path / "out")
    arts = generate_scaffold(
        problem_def,
        disciplines_into=tmp_path / "disciplines",
        lib_dir=tmp_path / "out" / "lib",
        import_root=tmp_path,
        artifacts=frozenset({"disciplines"}),
    )

    kinds = {a.kind for a in arts}
    assert ArtifactKind.DISCIPLINE_SCAFFOLD in kinds
    assert ArtifactKind.EXECUTOR not in kinds
    assert ArtifactKind.POSTPROCESSOR not in kinds


def test_scaffold_force_overwrites(problem_def, tmp_path):
    from gemseo_gantry.generator.lib_generator import generate_lib
    from gemseo_gantry.generator.scaffold_generator import generate_scaffold

    generate_lib(problem_def, tmp_path / "out")
    disciplines_into = tmp_path / "disciplines"
    lib_dir = tmp_path / "out" / "lib"
    artifacts = frozenset({"disciplines"})
    generate_scaffold(
        problem_def,
        disciplines_into=disciplines_into,
        lib_dir=lib_dir,
        import_root=tmp_path,
        artifacts=artifacts,
    )
    arts2 = generate_scaffold(
        problem_def,
        disciplines_into=disciplines_into,
        lib_dir=lib_dir,
        import_root=tmp_path,
        artifacts=artifacts,
        force=True,
    )

    disc_arts = [a for a in arts2 if a.kind is ArtifactKind.DISCIPLINE_SCAFFOLD]
    assert len(disc_arts) > 0
    written = [a for a in disc_arts if a.status is ArtifactStatus.WRITTEN]
    skipped = [a for a in disc_arts if a.status is ArtifactStatus.SKIPPED]
    assert len(written) > 0
    assert len(skipped) == 0


def test_scaffold_returns_flat_artifact_list(problem_def, tmp_path):
    from gemseo_gantry.generator import generate_scaffold
    from gemseo_gantry.generator.lib_generator import generate_lib

    generate_lib(problem_def, tmp_path)
    arts = generate_scaffold(
        problem_def,
        disciplines_into=tmp_path / "disciplines",
        lib_dir=tmp_path / "lib",
        executor_into=tmp_path / "scenarios",
        import_root=tmp_path,
    )
    kinds = {a.kind for a in arts}
    assert ArtifactKind.DISCIPLINE_SCAFFOLD in kinds
    assert all(
        a.status is ArtifactStatus.WRITTEN for a in arts
    )  # first run, nothing skipped
    # second run with force=False skips the discipline stubs
    arts2 = generate_scaffold(
        problem_def,
        disciplines_into=tmp_path / "disciplines",
        lib_dir=tmp_path / "lib",
        executor_into=tmp_path / "scenarios",
        import_root=tmp_path,
    )
    disc = [a for a in arts2 if a.kind is ArtifactKind.DISCIPLINE_SCAFFOLD]
    assert disc and all(a.status is ArtifactStatus.SKIPPED for a in disc)


# -- Filename builders -----------------------------------------------------


def test_scaffold_filename_builders():
    from gemseo_gantry.generator.scaffold_generator import (
        discipline_scaffold_filename,
        executor_filename,
        loader_filename,
    )

    assert discipline_scaffold_filename("Drag") == "Drag_scaffold.py"
    assert executor_filename("MyScenario") == "execute_MyScenario.py"
    assert loader_filename("MyScenario") == "load_MyScenario.py"


# -- lib-dir check -------------------------------------------------------------


def test_scaffold_missing_lib_dir_raises_before_writing(problem_def, tmp_path):
    from gemseo_gantry.generator import generate_scaffold

    with pytest.raises(FileNotFoundError, match="No generated lib found"):
        generate_scaffold(
            problem_def,
            disciplines_into=tmp_path / "disciplines",
            lib_dir=tmp_path / "lib",
            executor_into=tmp_path,
            import_root=tmp_path,
        )

    assert list(tmp_path.iterdir()) == []  # nothing written


def test_scaffold_stale_lib_lists_missing_modules(problem_def, tmp_path):
    from gemseo_gantry.generator import generate_scaffold
    from gemseo_gantry.generator.lib_generator import generate_lib

    generate_lib(problem_def, tmp_path)
    stale = tmp_path / "lib" / f"{DISCIPLINE_NAMES[0]}_io.py"
    stale.unlink()

    with pytest.raises(FileNotFoundError, match=f"is missing {stale.name};"):
        generate_scaffold(
            problem_def,
            disciplines_into=tmp_path / "disciplines",
            lib_dir=tmp_path / "lib",
            import_root=tmp_path,
        )

    assert not (tmp_path / "disciplines").exists()


def test_scaffold_loader_only_does_not_need_lib(problem_def, tmp_path):
    from gemseo_gantry.generator import generate_scaffold

    arts = generate_scaffold(
        problem_def,
        disciplines_into=tmp_path / "disciplines",
        lib_dir=tmp_path / "lib",
        executor_into=tmp_path,
        import_root=tmp_path,
        artifacts=frozenset({"loader"}),
    )

    assert {a.kind for a in arts} == {ArtifactKind.POSTPROCESSOR}


def test_scaffold_disciplines_only_ignores_scenario_modules(problem_def, tmp_path):
    from gemseo_gantry.generator import generate_scaffold
    from gemseo_gantry.generator.lib_generator import generate_lib

    generate_lib(problem_def, tmp_path)
    for scenario in problem_def.scenarios:
        (tmp_path / "lib" / f"{scenario.name}.py").unlink()

    arts = generate_scaffold(
        problem_def,
        disciplines_into=tmp_path / "disciplines",
        lib_dir=tmp_path / "lib",
        import_root=tmp_path,
        artifacts=frozenset({"disciplines"}),
    )

    assert {a.kind for a in arts} == {ArtifactKind.DISCIPLINE_SCAFFOLD}


def test_required_lib_modules_are_all_generated_by_build(problem_def, tmp_path):
    """Guards against drift between what build writes and what scaffold expects."""
    from gemseo_gantry.generator.lib_generator import generate_lib
    from gemseo_gantry.generator.scaffold_generator import (
        ALL_ARTIFACTS,
        required_lib_modules,
    )

    built = {a.path.name for a in generate_lib(problem_def, tmp_path)}

    required = required_lib_modules(problem_def, ALL_ARTIFACTS)
    assert required
    assert set(required) <= built
