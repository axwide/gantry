"""Shared helper: assert CLI -j output validates against the envelope schema."""

from __future__ import annotations

import json

import jsonschema

from gemseo_gantry.cli._result import CliResult

_SCHEMA = CliResult.model_json_schema()


def assert_valid_envelope(output: str) -> dict:
    """Parse `output` as JSON, validate it against the CliResult schema, return it."""
    data = json.loads(output)
    jsonschema.validate(instance=data, schema=_SCHEMA)
    return data
