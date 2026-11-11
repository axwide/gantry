from pathlib import Path

from gemseo_gantry.generator.lib_generator import generate_lib
from gemseo_gantry.generator.scaffold_generator import (
    generate_disciplines,
    generate_scenario_executor,
)
from gemseo_gantry.validation.pipeline import validate_toml

SOBIESKI = (
    Path(__file__).parents[3] / "src/gemseo_gantry/examples/sobieski/sobieski.toml"
)


def test_nested_lib_emits_subscenarios_dataclass(tmp_path: Path):
    problem = validate_toml(SOBIESKI).problem
    generate_lib(problem, tmp_path)
    system_src = (tmp_path / "lib" / "SystemScenario.py").read_text()
    assert "class SystemScenarioSubScenarios:" in system_src
    assert "StructureScenario: BaseScenario" in system_src
    assert "AerodynamicsScenario: BaseScenario" in system_src
    assert "PropulsionScenario: BaseScenario" in system_src
    assert "Mission: Discipline" in system_src


def test_nested_emits_single_root_executor(tmp_path: Path):
    problem = validate_toml(SOBIESKI).problem
    generate_disciplines(
        problem, tmp_path / "lib", lib_dir=tmp_path / "lib", import_root=tmp_path
    )
    out = generate_scenario_executor(
        problem,
        tmp_path,
        lib_dir=tmp_path / "lib",
        disciplines_dir=tmp_path / "lib",
        import_root=tmp_path,
    )
    written = {p.path.name for p in out if p.path.name.startswith("execute_")}
    assert written == {"execute_SystemScenario.py"}
