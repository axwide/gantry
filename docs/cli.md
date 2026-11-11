# CLI reference

Every command that reads a problem definition takes an optional path to the TOML file; without one, it auto-detects a problem TOML in the current directory. Run `gantry <command> --help` for the full, current option list.

## Common options

| Option | Description |
|---|---|
| `--quiet`, `-q` | Suppress output. |
| `--json`, `-j` | Emit a single-line, machine-readable JSON result envelope on stdout instead of rich output. Mutually exclusive with `--quiet`. |
| `--force`, `-f` | On write-once commands: overwrite existing files. |

## Commands

| Command | Overwrite semantics | What it does |
|---|---|---|
| [`init`](#init) | write-once | Create a starter problem definition and its JSON Schema. |
| [`validate`](#validate) | read-only | Parse and cross-validate the problem. |
| [`build`](#build) | **destructive** | Validate, then (re)build the disposable `lib/` package. |
| [`scaffold`](#scaffold) | **write-once** | Write user-owned discipline, executor, and loader seeds. |
| [`example`](#example) | write-once | Generate a complete, runnable example project. |
| [`schema`](#schema) | write-once | Write the JSON Schema for problem-definition TOML files. |
| [`diagram`](#diagram) | read-only | Draw N2 or XDSM diagrams of the coupling topology. |

### `init`

```bash
gantry init [PATH]
```

Writes an annotated starter problem definition (default `./problem.toml`) with a `#:schema` directive for editor validation, plus `schema/problem.schema.json` next to it.

### `validate`

```bash
gantry validate [TOML] [--watch]
```

Runs structural and semantic validation and reports any errors and warnings. `--watch`/`-w` re-validates on every save (q/Esc to stop).

### `build`

```bash
gantry build [TOML] [--out DIR] [--lib-name NAME] [--flat]
```

Validates, then rebuilds the generated package. Only the generated package directory is ever wiped.

| Option | Description |
|---|---|
| `--out`, `-o` | Directory to generate into (default: the TOML's directory). |
| `--lib-name` | Name of the generated lib package directory (default: `lib`). |
| `--flat` | Use when generating directly into a source root (e.g. `src/`). Prevents a spurious `__init__.py` that breaks type-checker import resolution. |

### `scaffold`

```bash
gantry scaffold [TOML] [--disciplines-into DIR] [--executor-into DIR] [--lib-dir DIR] [--import-root DIR] [--only ARTIFACTS] [--runnable]
```

Writes seed files that you own. Existing files are skipped unless `--force` is given.

| Option | Description |
|---|---|
| `--disciplines-into` | Directory for discipline stubs (default: `<toml-dir>/disciplines`). |
| `--executor-into` | Directory for the scenario executor (default: the TOML's directory). |
| `--lib-dir` | The `lib` directory produced by `gantry build` (default: `<toml-dir>/lib`). Set this when you built with `--out` or `--lib-name`. Scaffold fails without writing anything if this directory lacks a module the seeds import, e.g. because `build` hasn't been run or is out of date. |
| `--import-root` | The `sys.path` root used to compute the absolute import paths baked into the seeds (default: the current directory). |
| `--only` | Generate only some artifacts: `d`/`disciplines`, `e`/`executor`, `l`/`loader`. Repeat or comma-separate, e.g. `--only d,e`. |
| `--runnable` | Generate discipline stubs that return placeholder outputs, so the executor runs end to end before any physics is written. |

### `example`

```bash
gantry example {sellar|sobieski} [PATH] [--explain] [--dump-toml]
```

Generates a complete, runnable example project in a new `<name>/` directory under `PATH` (default: the current directory): Sellar, the canonical small MDO benchmark, or Sobieski's supersonic business jet, a larger bilevel problem.

| Option | Description |
|---|---|
| `--explain` | Narrate the generation workflow stage by stage. |
| `--dump-toml` | Write only the example's problem definition TOML. |

### `schema`

```bash
gantry schema [PATH]
```

Writes `schema/problem.schema.json` into `PATH` (default: the current directory). `init` and `build` already do this, so run it directly only to regenerate the schema alone.

### `diagram`

```bash
gantry diagram n2   [TOML] [--format pdf|png|svg] [--output-dir DIR]
gantry diagram xdsm [TOML] [--output-dir DIR]
```

Draws the coupling topology without touching your scaffold files. `n2` writes an interactive `n2.html` alongside a static file in the chosen format (default `pdf`) and requires at least two disciplines. Output goes to `<toml-dir>/diagrams` by default.
