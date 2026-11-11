# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**gemseo-gantry** is Python tooling that parses a problem-definition TOML file into an internal MDAO problem model and generates discipline glue code (stubs, IO dataclasses, grammars, design space, scenario scripts) for GEMSEO. TOML is the sole canonical input format.

- **Package manager:** `uv`
- **Git hosting CLI:** `gh` (GitHub)
- **Type checker:** `basedpyright`
- **Linter:** `ruff`

## Contributing conventions

Follow the contributor guide. All of it applies, including the docstring, lazy-import and idiomatic-by-default conventions and the branch/commit/PR workflow:

@CONTRIBUTING.md

When following "Idiomatic by default", apply minor divergences silently; flag the ones that touch intent or a requirement to the user.

## Writing style

Write in a natural, direct human voice. Lead with the point. Use plain words,
varied sentence length, and contractions where natural. Avoid corporate jargon,
hype, filler, and formulaic transitions. Do not use em dashes, "delve,"
"in today's world," "it's important to note," or neat three-item lists.
Never invent facts, anecdotes, or personal experiences. Ask me for missing
information instead of guessing.

## CLI JSON Output

All `gantry` subcommands support `--json`, which emits a single-line JSON envelope (`CliResult` in `src/gemseo_gantry/cli/_result.py`) instead of Rich output. Always use `--json` when invoking gantry programmatically. Leave it off only when the goal is human-readable output.

## GEMSEO docs lookup

If the Context7 MCP is available, use it (`resolve-library-id` / `query-docs`) to check GEMSEO's documented API and idioms. It's indexed as `/gemseo/gemseo`. Otherwise use the GEMSEO docs site or the installed source, as described in the contributor guide.
