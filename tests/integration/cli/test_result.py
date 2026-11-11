import json

import pytest
from pydantic import ValidationError

from gemseo_gantry.cli._result import (
    Artifact,
    ArtifactKind,
    ArtifactStatus,
    CliResult,
    Diagnostic,
    Invocation,
)


def test_diagnostic_to_dict_no_loc():
    d = Diagnostic(type="validation", message="field required")
    assert d.to_dict() == {"type": "validation", "message": "field required"}


def test_diagnostic_to_dict_with_loc():
    d = Diagnostic(
        type="validation", message="field required", loc="disciplines.Drag.inputs.0"
    )
    assert d.to_dict() == {
        "type": "validation",
        "message": "field required",
        "loc": "disciplines.Drag.inputs.0",
    }


def test_cli_result_minimal_dump():
    r = CliResult(invocation=Invocation(command=["validate"]), success=True)
    assert json.loads(r.model_dump_json(exclude_none=True)) == {
        "invocation": {"command": ["validate"], "params": {}},
        "success": True,
        "artifacts": [],
        "warnings": [],
        "errors": [],
    }


def test_cli_result_invocation_records_path_and_params():
    r = CliResult(
        invocation=Invocation(
            command=["diagram", "n2"], params={"toml": "problem.toml"}
        ),
        success=True,
    )
    d = json.loads(r.model_dump_json(exclude_none=True))
    assert d["invocation"]["command"] == ["diagram", "n2"]
    assert d["invocation"]["params"]["toml"] == "problem.toml"


def test_cli_result_with_artifact_and_diagnostics():
    r = CliResult(
        invocation=Invocation(command=["scaffold"]),
        success=True,
        artifacts=[
            Artifact(
                path="disciplines/Drag_scaffold.py",
                kind=ArtifactKind.DISCIPLINE_SCAFFOLD,
                status=ArtifactStatus.WRITTEN,
            )
        ],
        warnings=[Diagnostic("validation", "heads up")],
    )
    d = json.loads(r.model_dump_json(exclude_none=True))
    assert d["invocation"]["command"] == ["scaffold"]
    assert d["artifacts"] == [
        {
            "path": "disciplines/Drag_scaffold.py",
            "kind": "discipline_scaffold",
            "status": "written",
        }
    ]
    assert d["warnings"] == [{"type": "validation", "message": "heads up"}]


def test_diagnostic_loc_omitted_when_none_in_envelope():
    r = CliResult(
        invocation=Invocation(command=["build"]),
        success=False,
        errors=[Diagnostic("usage", "bad")],
    )
    d = json.loads(r.model_dump_json(exclude_none=True))
    assert d["errors"] == [{"type": "usage", "message": "bad"}]
    assert "loc" not in d["errors"][0]


def test_artifact_rejects_unknown_kind():
    with pytest.raises(ValidationError):
        Artifact(path="x", kind="bogus", status="written")


def test_cli_result_forbids_extra_keys():
    with pytest.raises(ValidationError):
        CliResult(invocation=Invocation(command=["build"]), success=True, rogue="nope")


def test_cli_result_schema_generates():
    schema = CliResult.model_json_schema()
    assert schema["additionalProperties"] is False
    assert "invocation" in schema["properties"]
