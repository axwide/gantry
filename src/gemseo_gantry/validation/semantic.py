from __future__ import annotations

import difflib

from slugify import slugify

from ..model.data_model import BILEVEL_FORMULATIONS, FormulationType
from ..parser.toml_data_model import TomlProblemDefinition
from ..parser.utils import pascalify, sanitize_identifier


def check_has_disciplines(parsed: TomlProblemDefinition) -> list[str]:
    if not parsed.disciplines:
        return ["No disciplines defined."]
    return []


def check_has_variables(parsed: TomlProblemDefinition) -> list[str]:
    if not parsed.variables:
        return ["The [[variables]] section is required and must be non-empty."]
    return []


def check_duplicate_variable_names(parsed: TomlProblemDefinition) -> list[str]:
    seen: set[str] = set()
    violations = []
    for var in parsed.variables:
        if var.name in seen:
            violations.append(
                f"Duplicate variable name {var.name!r} in [[variables]] - "
                f"each variable name must be unique."
            )
        seen.add(var.name)
    return violations


def check_double_outputs(parsed: TomlProblemDefinition) -> list[str]:
    output_by: dict[str, list[str]] = {}
    for disc_name, disc in parsed.disciplines.items():
        for var in disc.outputs:
            output_by.setdefault(var, []).append(disc_name)
    return [
        f"Variable {var!r} is output by multiple disciplines: {', '.join(producers)}"
        for var, producers in output_by.items()
        if len(producers) > 1
    ]


def check_variable_refs(parsed: TomlProblemDefinition) -> list[str]:
    if not parsed.variables:
        return []
    known = {v.name for v in parsed.variables}
    violations = []

    def _check(name: str, context: str) -> None:
        if name not in known:
            suggestions = difflib.get_close_matches(name, known, n=1)
            msg = f"{context} references unknown variable {name!r}"
            if suggestions:
                msg += f" (did you mean {suggestions[0]!r}?)"
            violations.append(msg)

    for disc_name, disc in parsed.disciplines.items():
        for var in dict.fromkeys(disc.inputs + disc.outputs):
            _check(var, f"Discipline {disc_name!r}")

    for scenario_name, scenario in parsed.scenarios.items():
        ctx = f"Scenario {scenario_name!r}"
        for var in scenario.design_variables:
            _check(var, ctx)
        _check(scenario.objective.variable, ctx)
        for constraint in scenario.constraints:
            _check(constraint.variable, ctx)
        for var in scenario.observables:
            _check(var, ctx)

    return violations


def check_scenario_disciplines(parsed: TomlProblemDefinition) -> list[str]:
    # Build a set of known discipline/scenario names, including both raw and pascalified versions
    raw_known = set(parsed.disciplines.keys()) | set(parsed.scenarios.keys())
    pascalified_known = {sanitize_identifier(pascalify(k)) for k in raw_known}
    all_known = raw_known | pascalified_known

    violations = []
    for scenario_name, scenario in parsed.scenarios.items():
        for disc in scenario.disciplines:
            if disc not in all_known:
                violations.append(
                    f"Scenario {scenario_name!r} references unknown discipline {disc!r}"
                )
    return violations


def _broadcast(value: float | list[float] | None, dimension: int) -> list[float] | None:
    if value is None:
        return None
    if isinstance(value, list):
        return value
    return [value for _ in range(dimension)]


def check_variable_bounds(parsed: TomlProblemDefinition) -> list[str]:
    violations = []
    for var in parsed.variables:
        lowers = _broadcast(var.lower_bound, var.dimension)
        uppers = _broadcast(var.upper_bound, var.dimension)
        if lowers is None or uppers is None:
            continue
        for lower, upper in zip(lowers, uppers):
            if lower > upper:
                violations.append(
                    f"Variable {var.name!r}: lower_bound ({lower}) "
                    f"must be less than upper_bound ({upper})"
                )
                break
    return violations


def check_normalized_name_collisions(parsed: TomlProblemDefinition) -> list[str]:
    violations: list[str] = []

    def _check(names: list[str], normalize_fn, label: str) -> list[str]:
        seen: dict[str, str] = {}
        result = []
        for name in names:
            normalized = normalize_fn(name)
            if normalized in seen:
                result.append(
                    f"{label} names {seen[normalized]!r} and {name!r} "
                    f"both normalize to {normalized!r}"
                )
            else:
                seen[normalized] = name
        return result

    def _pascal(name: str) -> str:
        return sanitize_identifier(pascalify(name))

    def _slug(name: str) -> str:
        return sanitize_identifier(slugify(name, separator="_"))

    violations.extend(_check(list(parsed.disciplines), _pascal, "Discipline"))
    violations.extend(_check(list(parsed.scenarios), _pascal, "Scenario"))
    violations.extend(_check([v.name for v in parsed.variables], _slug, "Variable"))
    return violations


def _scenario_has_sub(parsed: TomlProblemDefinition, scenario) -> bool:
    """Check if a scenario contains any sub-scenarios.

    A scenario contains sub-scenarios if any of its disciplines references another
    scenario (by raw TOML key or pascalified form).
    """
    raw_scenario_names = set(parsed.scenarios)
    pascalified_scenario_names = {
        sanitize_identifier(pascalify(k)) for k in raw_scenario_names
    }
    all_scenario_names = raw_scenario_names | pascalified_scenario_names
    return any(disc in all_scenario_names for disc in scenario.disciplines)


def _resolve_formulation(parsed: TomlProblemDefinition, scenario) -> FormulationType:
    """Resolve the effective formulation type for a scenario.

    If the scenario explicitly specifies a formulation, use it. Otherwise, if it
    contains sub-scenarios, default to BiLevelBCD. Otherwise, default to MDF.
    """
    if scenario.formulation is not None:
        return scenario.formulation
    if _scenario_has_sub(parsed, scenario):
        return FormulationType.BILEVEL_BCD
    return FormulationType.MDF


def check_nesting_formulation(parsed: TomlProblemDefinition) -> list[str]:
    """Validate that nesting and formulation type are consistent.

    A scenario containing sub-scenarios must use a bilevel formulation.
    A scenario using a bilevel formulation must contain at least one sub-scenario.
    """
    violations: list[str] = []
    for name, scenario in parsed.scenarios.items():
        has_sub = _scenario_has_sub(parsed, scenario)
        formulation = _resolve_formulation(parsed, scenario)
        if has_sub and formulation not in BILEVEL_FORMULATIONS:
            violations.append(
                f"Scenario {name!r} contains sub-scenarios but uses formulation "
                f"{formulation.value!r}; nested scenarios require 'BiLevel' or "
                f"'BiLevelBCD'"
            )
        if not has_sub and formulation in BILEVEL_FORMULATIONS:
            violations.append(
                f"Scenario {name!r} uses bilevel formulation "
                f"{formulation.value!r} but has no sub-scenarios; "
                f"'BiLevel'/'BiLevelBCD' require at least one nested scenario"
            )
    return violations


def check_disjoint_discipline_scenario_names(
    parsed: TomlProblemDefinition,
) -> list[str]:
    """Discipline and scenario names must not collide after normalization.

    Nesting resolves a name in a scenario's ``disciplines`` against the union of
    discipline and scenario names, so a shared name would be ambiguous.
    """
    disc_by_norm = {
        sanitize_identifier(pascalify(name)): name for name in parsed.disciplines
    }
    violations: list[str] = []
    for scenario_name in parsed.scenarios:
        norm = sanitize_identifier(pascalify(scenario_name))
        if norm in disc_by_norm:
            violations.append(
                f"Scenario {scenario_name!r} and discipline "
                f"{disc_by_norm[norm]!r} both normalize to {norm!r}; "
                f"discipline and scenario names must be distinct"
            )
    return violations


def _sub_scenario_names(parsed: TomlProblemDefinition) -> set[str]:
    """Return the set of scenario names that are nested within other scenarios.

    A scenario name is considered nested if it appears in any scenario's disciplines
    list (accounting for case normalization via pascalify).
    """
    raw_scenario_names = set(parsed.scenarios)
    pascalified_scenario_names = {
        sanitize_identifier(pascalify(k)) for k in raw_scenario_names
    }
    all_scenario_names = raw_scenario_names | pascalified_scenario_names

    # Collect all scenario names that appear in disciplines (after normalization)
    nested_names: set[str] = set()
    for scenario in parsed.scenarios.values():
        for disc in scenario.disciplines:
            if disc in all_scenario_names:
                # Find which raw scenario name this refers to
                if disc in raw_scenario_names:
                    nested_names.add(disc)
                else:
                    # It's a pascalified form; find the raw name
                    for raw_name in raw_scenario_names:
                        if sanitize_identifier(pascalify(raw_name)) == disc:
                            nested_names.add(raw_name)
    return nested_names


def check_root_exists(parsed: TomlProblemDefinition) -> list[str]:
    """Check that at least one root scenario exists.

    A root scenario is one that is not nested under any other scenario. If all
    scenarios are nested (e.g., due to a cycle), there is no root and the
    problem definition is invalid.
    """
    if not parsed.scenarios:
        return []
    subs = _sub_scenario_names(parsed)
    roots = [name for name in parsed.scenarios if name not in subs]
    if not roots:
        return [
            "No root scenario found: every scenario is nested under another "
            "(a cycle); exactly one top-level scenario is required"
        ]
    return []


def assert_supported(parsed: TomlProblemDefinition) -> None:
    """Raise NotImplementedError for recognized-but-unsupported features.

    This runs in the semantic step, before generation. IDF and multi-root are
    valid, recognized inputs that are not yet implemented.
    """
    for name, scenario in parsed.scenarios.items():
        if _resolve_formulation(parsed, scenario) == FormulationType.IDF:
            raise NotImplementedError(
                f"Scenario {name!r}: IDF formulation is not yet supported"
            )

    subs = _sub_scenario_names(parsed)
    roots = sorted(name for name in parsed.scenarios if name not in subs)
    if len(roots) > 1:
        raise NotImplementedError(
            f"Multiple root scenarios are not yet supported: found {roots}; "
            f"define a single top-level scenario"
        )

    # A discipline may currently be instantiated only once across the whole
    # problem: the same discipline appearing in more than one scenario (or
    # twice in a single scenario) is not yet supported. Scenario references
    # (sub-scenarios) are excluded, in either raw or pascalified form.
    scenario_name_forms = set(parsed.scenarios) | {
        sanitize_identifier(pascalify(name)) for name in parsed.scenarios
    }
    used_by: dict[str, list[str]] = {}
    display: dict[str, str] = {}
    for scenario_name, scenario in parsed.scenarios.items():
        for disc in scenario.disciplines:
            if disc in scenario_name_forms:
                continue
            key = sanitize_identifier(pascalify(disc))
            used_by.setdefault(key, []).append(scenario_name)
            display.setdefault(key, disc)
    for key, scenarios in used_by.items():
        if len(scenarios) > 1:
            raise NotImplementedError(
                f"Discipline {display[key]!r} is instantiated multiple times "
                f"(used by scenarios {sorted(set(scenarios))}); a discipline may "
                f"only be used once per problem"
            )


def check_dimension(parsed: TomlProblemDefinition) -> list[str]:
    violations = []
    for var in parsed.variables:
        if var.dimension < 1:
            violations.append(
                f"Variable {var.name!r}: dimension must be at least 1 (got {var.dimension})"
            )
    return violations


def check_bound_dimensions(parsed: TomlProblemDefinition) -> list[str]:
    violations = []
    for var in parsed.variables:
        for field_name in ("lower_bound", "upper_bound", "default_value"):
            value = getattr(var, field_name)
            if isinstance(value, list) and len(value) != var.dimension:
                violations.append(
                    f"Variable {var.name!r}: {field_name} has {len(value)} "
                    f"element(s) but dimension is {var.dimension}"
                )
    return violations


def _design_variables(parsed: TomlProblemDefinition):
    """Yield (name, Variable) for each variable used as a design variable."""
    design_var_names: set[str] = set()
    for scenario in parsed.scenarios.values():
        design_var_names.update(scenario.design_variables)

    var_map = {v.name: v for v in parsed.variables}
    for name in design_var_names:
        var = var_map.get(name)
        if var is None:
            continue  # caught by check_variable_refs
        yield name, var


def check_design_variable_bounds(parsed: TomlProblemDefinition) -> list[str]:
    # Missing bounds are allowed: GEMSEO maps an absent lower/upper bound to
    # -inf/+inf respectively. Only an explicit, equal pair of
    # bounds is invalid, as it would pin the variable to a constant.
    violations = []
    for name, var in _design_variables(parsed):
        if (
            var.lower_bound is not None
            and var.upper_bound is not None
            and var.lower_bound == var.upper_bound
        ):
            violations.append(
                f"Design variable {name!r}: lower_bound equals upper_bound "
                f"({var.lower_bound}) - a design variable cannot be a constant."
            )
    return violations


def check_design_variable_has_default(parsed: TomlProblemDefinition) -> list[str]:
    # A design variable needs a starting point (x0). GEMSEO has no current value
    # for it without a default, so a scenario cannot begin optimizing. Coupling
    # and other non-design variables may omit their default.
    violations = []
    for name, var in _design_variables(parsed):
        if var.default_value is None:
            violations.append(
                f"Design variable {name!r}: default_value is required - it is the "
                f"optimization starting point (x0); GEMSEO has no current value for "
                f"the variable without it."
            )
    return violations


def check_default_value_in_bounds(parsed: TomlProblemDefinition) -> list[str]:
    violations = []
    for var in parsed.variables:
        defaults = _broadcast(var.default_value, var.dimension)
        if defaults is None:
            continue
        lowers = _broadcast(var.lower_bound, var.dimension)
        uppers = _broadcast(var.upper_bound, var.dimension)
        for i, d in enumerate(defaults):
            lower = lowers[i] if lowers is not None and i < len(lowers) else None
            upper = uppers[i] if uppers is not None and i < len(uppers) else None
            if lower is not None and d < lower:
                violations.append(
                    f"Variable {var.name!r}: default_value ({d}) is below "
                    f"lower_bound ({lower})"
                )
            elif upper is not None and d > upper:
                violations.append(
                    f"Variable {var.name!r}: default_value ({d}) exceeds "
                    f"upper_bound ({upper})"
                )
    return violations


def _disc_outputs_for_scenario(
    parsed: TomlProblemDefinition, scenario_disciplines: list[str]
) -> set[str]:
    """Collect outputs from disciplines (not sub-scenarios) listed in a scenario."""
    outputs: set[str] = set()
    for disc_name in scenario_disciplines:
        if disc_name in parsed.disciplines:
            outputs.update(parsed.disciplines[disc_name].outputs)
    return outputs


def check_objective_is_output(parsed: TomlProblemDefinition) -> list[str]:
    violations = []
    for scenario_name, scenario in parsed.scenarios.items():
        outputs = _disc_outputs_for_scenario(parsed, scenario.disciplines)
        if not outputs:
            continue  # all disciplines are sub-scenarios - skip
        obj = scenario.objective.variable
        if obj not in outputs:
            suggestions = difflib.get_close_matches(obj, outputs, n=1)
            msg = (
                f"Scenario {scenario_name!r}: objective variable {obj!r} "
                f"is not an output of any discipline"
            )
            if suggestions:
                msg += f" (did you mean {suggestions[0]!r}?)"
            violations.append(msg)
    return violations


def check_objective_is_scalar(parsed: TomlProblemDefinition) -> list[str]:
    var_map = {v.name: v for v in parsed.variables}
    violations = []
    for scenario_name, scenario in parsed.scenarios.items():
        var = var_map.get(scenario.objective.variable)
        if var is None:
            continue  # caught by check_variable_refs
        if var.dimension > 1:
            violations.append(
                f"Scenario {scenario_name!r}: objective variable "
                f"{scenario.objective.variable!r} has dimension {var.dimension}; "
                f"a single-objective scenario requires a scalar objective. "
                f"Vector (multi-objective) objectives are not yet supported."
            )
    return violations


def check_constraint_outputs(parsed: TomlProblemDefinition) -> list[str]:
    violations = []
    for scenario_name, scenario in parsed.scenarios.items():
        outputs = _disc_outputs_for_scenario(parsed, scenario.disciplines)
        if not outputs:
            continue
        for constraint in scenario.constraints:
            var = constraint.variable
            if var not in outputs:
                suggestions = difflib.get_close_matches(var, outputs, n=1)
                msg = (
                    f"Scenario {scenario_name!r}: constraint variable {var!r} "
                    f"is not an output of any discipline"
                )
                if suggestions:
                    msg += f" (did you mean {suggestions[0]!r}?)"
                violations.append(msg)
    return violations


def check_observable_outputs(parsed: TomlProblemDefinition) -> list[str]:
    violations = []
    for scenario_name, scenario in parsed.scenarios.items():
        outputs = _disc_outputs_for_scenario(parsed, scenario.disciplines)
        if not outputs:
            continue
        for var in scenario.observables:
            if var not in outputs:
                suggestions = difflib.get_close_matches(var, outputs, n=1)
                msg = (
                    f"Scenario {scenario_name!r}: observable {var!r} "
                    f"is not an output of any discipline"
                )
                if suggestions:
                    msg += f" (did you mean {suggestions[0]!r}?)"
                violations.append(msg)
    return violations


def check_orphan_variables(parsed: TomlProblemDefinition) -> list[str]:
    referenced: set[str] = set()
    for disc in parsed.disciplines.values():
        referenced.update(disc.inputs)
        referenced.update(disc.outputs)
    for scenario in parsed.scenarios.values():
        referenced.update(scenario.design_variables)
        referenced.add(scenario.objective.variable)
        for constraint in scenario.constraints:
            referenced.add(constraint.variable)
        referenced.update(scenario.observables)

    violations = []
    for var in parsed.variables:
        if var.name not in referenced:
            violations.append(
                f"Variable {var.name!r} is declared in [[variables]] but never referenced "
                f"by any discipline or scenario."
            )
    return violations


def check_discipline_inputs(parsed: TomlProblemDefinition) -> list[str]:
    violations = []
    for disc_name, disc in parsed.disciplines.items():
        if not disc.inputs:
            violations.append(
                f"Discipline {disc_name!r} has no inputs - "
                f"a discipline must declare at least one input."
            )
    return violations


def check_discipline_outputs(parsed: TomlProblemDefinition) -> list[str]:
    warnings = []
    for disc_name, disc in parsed.disciplines.items():
        if not disc.outputs:
            warnings.append(
                f"Discipline {disc_name!r} has no outputs - it produces nothing "
                f"that other disciplines or the scenario can consume. This may be a mistake."
            )
    return warnings


def check_missing_units(parsed: TomlProblemDefinition) -> list[str]:
    return [
        f"Variable {var.name!r} has no unit defined - units improve the "
        f"generated documentation. Set unit to an empty string to suppress "
        f"this warning."
        for var in parsed.variables
        if var.unit is None
    ]


def check_design_variable_not_output(parsed: TomlProblemDefinition) -> list[str]:
    violations = []
    for scenario_name, scenario in parsed.scenarios.items():
        for disc_name in scenario.disciplines:
            if disc_name not in parsed.disciplines:
                continue
            disc_outputs = set(parsed.disciplines[disc_name].outputs)
            for dv in scenario.design_variables:
                if dv in disc_outputs:
                    violations.append(
                        f"Scenario {scenario_name!r}: design variable {dv!r} is also "
                        f"an output of discipline {disc_name!r} - a design variable "
                        f"cannot be computed by a discipline."
                    )
    return violations


def run_all(parsed: TomlProblemDefinition) -> tuple[list[str], list[str]]:
    assert_supported(parsed)
    errors: list[str] = []
    warnings: list[str] = []
    errors.extend(check_has_disciplines(parsed))
    errors.extend(check_has_variables(parsed))
    errors.extend(check_duplicate_variable_names(parsed))
    errors.extend(check_double_outputs(parsed))
    errors.extend(check_variable_refs(parsed))
    errors.extend(check_scenario_disciplines(parsed))
    errors.extend(check_variable_bounds(parsed))
    errors.extend(check_design_variable_bounds(parsed))
    errors.extend(check_design_variable_has_default(parsed))
    errors.extend(check_default_value_in_bounds(parsed))
    errors.extend(check_normalized_name_collisions(parsed))
    errors.extend(check_disjoint_discipline_scenario_names(parsed))
    errors.extend(check_nesting_formulation(parsed))
    errors.extend(check_root_exists(parsed))
    errors.extend(check_dimension(parsed))
    errors.extend(check_bound_dimensions(parsed))
    errors.extend(check_objective_is_output(parsed))
    errors.extend(check_objective_is_scalar(parsed))
    errors.extend(check_constraint_outputs(parsed))
    errors.extend(check_observable_outputs(parsed))
    errors.extend(check_orphan_variables(parsed))
    errors.extend(check_discipline_inputs(parsed))
    errors.extend(check_design_variable_not_output(parsed))
    warnings.extend(check_discipline_outputs(parsed))
    warnings.extend(check_missing_units(parsed))
    return errors, warnings


# TODO: consider warning/error for scenario with no design_variables - may be valid
# as pure MDA, investigate GEMSEO behaviour first

# TODO: consider coupling graph connectivity check - investigate GEMSEO's own
# handling, revisit alongside nested scenarios

# TODO: consider objective traceability check (design vars -> disciplines -> objective)
# - investigate GEMSEO behaviour first

# TODO: consider warning for variables missing default_value - investigate impact
# before adding
