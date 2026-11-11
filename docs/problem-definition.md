# Problem definition

A problem is defined in a single TOML file with three kinds of table: `[disciplines.*]`, `[scenarios.*]`, and `[[variables]]`. Run `gantry init` for an annotated starter file.

Variable roles are **inferred**, not declared: a variable is a coupling if one discipline outputs it and another consumes it, and a design variable if a scenario lists it under `design_variables`.

```toml
[disciplines.sellar_1]
inputs  = ["x_1", "z", "y_2"]
outputs = ["y_1"]

[scenarios.sellar]
design_variables = ["x_1", "z"]
disciplines      = ["sellar_1", "sellar_2", "sellar_system"]
scenario_type    = "MDO"

[scenarios.sellar.objective]
variable = "obj"
maximize = false

[[scenarios.sellar.constraints]]
variable = "c_1"
operator = "<"
value    = 0.0

[[variables]]
name          = "x_1"
unit          = "-"
data_type     = "float"
dimension     = 1
description   = "Local design variable"
lower_bound   = 0.0
upper_bound   = 10.0
default_value = 1.0
```

Discipline and scenario names become Python identifiers: `sellar_1` generates a `Sellar1` discipline class.

## Disciplines

| Key | Required | Description |
|---|---|---|
| `inputs` | yes | Names of the variables the discipline consumes. |
| `outputs` | yes | Names of the variables the discipline produces. |

## Scenarios

| Key | Required | Description |
|---|---|---|
| `design_variables` | yes | Variables the scenario optimizes over. |
| `disciplines` | yes | Disciplines in the scenario. List other scenarios here to nest them (see below). |
| `objective` | yes | Table with `variable` and optional `maximize` (default `false`). The objective must be a scalar output. |
| `scenario_type` | no | `"MDO"` (optimization, default) or `"DOE"` (design of experiments). |
| `formulation` | no | `MDF`, `IDF`, `BiLevel`, or `BiLevelBCD`. Defaults to `MDF`, or `BiLevelBCD` for a scenario with sub-scenarios. |
| `constraints` | no | Array of tables with `variable`, `operator` (`"<"`, `">"`, or `"="`; default `"<"`), and `value` (default `0.0`). |
| `observables` | no | Discipline outputs to record during the run for post-processing. |

### Nested scenarios

A scenario can list other scenarios in its `disciplines` to build a multi-level (bilevel) problem. A scenario with sub-scenarios must use a bilevel formulation:

```toml
[scenarios.system]
design_variables = ["x"]
disciplines      = ["aero", "structure"]   # both are scenarios
formulation      = "BiLevelBCD"
# ...objective and constraints as usual
```

## Variables

Every variable referenced by a discipline or scenario must be declared.

| Key | Required | Description |
|---|---|---|
| `name` | yes | Variable name, used in grammars and the `Var` enum. |
| `data_type` | yes | `"float"` or `"integer"`. |
| `dimension` | yes | Number of components. |
| `unit` | no | Physical unit (a warning is reported if missing). |
| `description` | no | Human-readable description, carried into generated docstrings. |
| `lower_bound`, `upper_bound` | no | Bounds for design variables. Omitted bounds mean -inf / +inf. |
| `default_value` | for design variables | Starting point. Required for design variables; optional for everything else. |

Bounds and defaults take a scalar, which is broadcast across the variable's `dimension`, or a list giving per-component values.

## Editor validation

`gantry init` writes a JSON Schema next to your problem TOML and adds a `#:schema ./schema/problem.schema.json` directive to the file's first line. Open the TOML in any [taplo](https://taplo.tamasfe.dev/)-backed editor (VS Code "Even Better TOML", Zed, Neovim, Helix, JetBrains, Emacs) to get live autocomplete and structural validation. That catches missing required fields, wrong value types, invalid `data_type` and operator values, and misspelled keys.

The schema is a **generated artifact**: regenerate it with `gantry schema` rather than editing it by hand. It only checks structure. Identifier rules and cross-table semantic checks (duplicate names, dangling references, ...) come from the full validation pipeline, so keep `gantry validate --watch` running in a terminal for live semantic feedback.
