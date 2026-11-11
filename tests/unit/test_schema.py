from __future__ import annotations

import json

from gemseo_gantry.schema import (
    SCHEMA_DIRECTIVE,
    SCHEMA_DIRNAME,
    SCHEMA_FILENAME,
    build_schema,
    schema_json,
    write_schema,
)


def test_build_schema_has_expected_shape():
    schema = build_schema()
    # top-level tables of a problem definition
    assert set(schema["properties"]) == {"disciplines", "variables", "scenarios"}
    # only `disciplines` is structurally required (variables is enforced semantically)
    assert schema["required"] == ["disciplines"]
    # unknown keys are rejected -> editors flag typos
    assert schema["additionalProperties"] is False
    # enum carried through from the DataType StrEnum
    assert schema["$defs"]["DataType"]["enum"] == ["float", "integer"]


def test_build_schema_carries_do_not_edit_marker():
    assert "do not edit" in build_schema()["$comment"].lower()


def test_schema_json_is_deterministic_and_parses():
    text = schema_json()
    assert text.endswith("\n")
    assert json.loads(text) == build_schema()
    assert schema_json() == text  # stable across calls


def test_directive_matches_dir_and_filename():
    assert SCHEMA_DIRECTIVE == f"#:schema ./{SCHEMA_DIRNAME}/{SCHEMA_FILENAME}"


def test_write_schema_writes_under_schema_dir(tmp_path):
    written = write_schema(tmp_path)
    assert written == tmp_path / SCHEMA_DIRNAME / SCHEMA_FILENAME
    assert written.exists()
    assert json.loads(written.read_text(encoding="utf-8")) == build_schema()


def test_committed_repo_schema_is_current():
    from pathlib import Path

    repo_root = Path(__file__).parents[2]
    committed = repo_root / "schema" / "problem.schema.json"
    assert committed.exists(), "run `uv run gantry schema --force` to regenerate it"
    assert committed.read_text(encoding="utf-8") == schema_json(), (
        "Committed schema is stale. Regenerate with `uv run gantry schema --force`."
    )
