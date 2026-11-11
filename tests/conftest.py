import sys
import tempfile
from pathlib import Path

import pytest

# Suppression rules shared by all basedpyright invocations in the test suite.
# These silence known false-positives caused by upstream libraries (gemseo, pydantic)
# that ship incomplete or no type stubs. They are NOT silencing real type errors.
PYRIGHT_SUPPRESS_RULES: dict[str, str] = {
    "reportMissingTypeStubs": "none",
    "reportUnknownVariableType": "none",
    "reportUnknownLambdaType": "none",
    "reportUnknownMemberType": "none",
    "reportUnknownParameterType": "none",
    "reportUnknownArgumentType": "none",
    "reportAny": "none",
    "reportExplicitAny": "none",
    "reportMissingTypeArgument": "none",
    "reportAssignmentType": "none",
    "reportUnannotatedClassAttribute": "none",
    "reportUnusedImport": "none",
    "reportUnusedParameter": "none",
}

TOML_PATH = Path(__file__).parent / "fixtures" / "vleo.toml"
FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def _deterministic_console_width(monkeypatch):
    """Pin the terminal width Rich sees so panel rendering is identical everywhere.

    Rich's Console reads COLUMNS when stdout is not a TTY (as under Typer's
    CliRunner). An interactive shell exports a wide COLUMNS while CI leaves it
    unset and defaults to 80, so an assertion on rendered panel text could pass
    locally yet fail in CI when a long line is truncated with an ellipsis.
    Forcing 80 - CI's value - makes any such width-fragility reproduce locally.
    """
    monkeypatch.setenv("COLUMNS", "80")


@pytest.fixture(scope="module")
def problem_def():
    from gemseo_gantry.parser.toml_parser import parse_toml

    return parse_toml(TOML_PATH)


@pytest.fixture(
    params=sorted(FIXTURES_DIR.glob("*.toml")),
    ids=lambda p: p.stem,
)
def all_problem_defs(request):
    from gemseo_gantry.parser.toml_parser import parse_toml

    return parse_toml(request.param)


@pytest.fixture(scope="function")
def temp_generated_dir():
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        gen_dir = temp_path / "generated"
        gen_dir.mkdir()
        (gen_dir / "__init__.py").write_text("", encoding="utf-8")
        sys.path.insert(0, str(temp_path))
        try:
            yield gen_dir
        finally:
            for key in list(sys.modules.keys()):
                if key == "generated" or key.startswith("generated."):
                    sys.modules.pop(key, None)
            sys.path.remove(str(temp_path))
