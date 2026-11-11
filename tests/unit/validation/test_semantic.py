from gemseo_gantry.parser.toml_data_model import (
    TomlConstraint,
    TomlDiscipline,
    TomlObjective,
    TomlProblemDefinition,
    TomlScenario,
    TomlVariable,
)
from gemseo_gantry.validation.semantic import (
    check_bound_dimensions,
    check_constraint_outputs,
    check_default_value_in_bounds,
    check_design_variable_bounds,
    check_design_variable_has_default,
    check_design_variable_not_output,
    check_dimension,
    check_discipline_inputs,
    check_discipline_outputs,
    check_double_outputs,
    check_duplicate_variable_names,
    check_has_disciplines,
    check_has_variables,
    check_missing_units,
    check_normalized_name_collisions,
    check_objective_is_output,
    check_objective_is_scalar,
    check_observable_outputs,
    check_orphan_variables,
    check_scenario_disciplines,
    check_variable_bounds,
    check_variable_refs,
    run_all,
)

# -- helpers -------------------------------------------------------------------


def _make(disciplines=None, variables=None, scenarios=None):
    # model_construct bypasses validators - lets us build invalid states for testing
    return TomlProblemDefinition.model_construct(
        disciplines=disciplines or {},
        variables=variables or [],
        scenarios=scenarios or {},
    )


def _disc(inputs=(), outputs=()):
    return TomlDiscipline(inputs=list(inputs), outputs=list(outputs))


def _var(
    name, unit="m", data_type="float", dimension=1, lower_bound=None, upper_bound=None
):
    return TomlVariable(
        name=name,
        unit=unit,
        data_type=data_type,
        dimension=dimension,
        lower_bound=lower_bound,
        upper_bound=upper_bound,
    )


def _var_with_default(name, default, lower=None, upper=None):
    return TomlVariable(
        name=name,
        unit="m",
        data_type="float",
        dimension=1,
        default_value=default,
        lower_bound=lower,
        upper_bound=upper,
    )


def _scenario(disciplines, objective_var="y"):
    return TomlScenario(
        design_variables=[],
        disciplines=list(disciplines),
        objective=TomlObjective(variable=objective_var),
    )


# -- check_has_disciplines -----------------------------------------------------


def test_has_disciplines_empty():
    parsed = _make(disciplines={})
    assert check_has_disciplines(parsed) == ["No disciplines defined."]


def test_has_disciplines_ok():
    parsed = _make(disciplines={"drag": _disc(outputs=["f"])})
    assert check_has_disciplines(parsed) == []


# -- check_has_variables -------------------------------------------------------


def test_has_variables_empty_list():
    parsed = _make(disciplines={"d": _disc(outputs=["f"])}, variables=[])
    assert check_has_variables(parsed) == [
        "The [[variables]] section is required and must be non-empty."
    ]


def test_has_variables_ok():
    parsed = _make(
        disciplines={"d": _disc(outputs=["f"])},
        variables=[_var("f")],
    )
    assert check_has_variables(parsed) == []


# -- check_duplicate_variable_names --------------------------------------------


def test_duplicate_variable_name_detected():
    parsed = _make(
        disciplines={"d": _disc(inputs=["x"], outputs=["y"])},
        variables=[_var("x"), _var("x")],  # duplicate
    )
    violations = check_duplicate_variable_names(parsed)
    assert any("x" in v for v in violations)
    assert any("duplicate" in v.lower() or "unique" in v.lower() for v in violations)


def test_no_duplicate_variable_names_ok():
    parsed = _make(
        disciplines={"d": _disc(inputs=["x"], outputs=["y"])},
        variables=[_var("x"), _var("y")],
    )
    assert check_duplicate_variable_names(parsed) == []


# -- check_double_outputs ------------------------------------------------------


def test_double_outputs_detected():
    parsed = _make(
        disciplines={
            "drag": _disc(inputs=["h"], outputs=["duty_cycle"]),
            "power": _disc(inputs=["h"], outputs=["duty_cycle"]),
        }
    )
    violations = check_double_outputs(parsed)
    assert len(violations) == 1
    assert "duty_cycle" in violations[0]
    assert "drag" in violations[0]
    assert "power" in violations[0]


def test_double_outputs_none():
    parsed = _make(
        disciplines={
            "drag": _disc(inputs=["h"], outputs=["duty_cycle"]),
            "power": _disc(inputs=["duty_cycle"], outputs=["power_margin"]),
        }
    )
    assert check_double_outputs(parsed) == []


# -- check_variable_refs -------------------------------------------------------


def test_variable_refs_unknown():
    parsed = _make(
        disciplines={"drag": _disc(inputs=["h"], outputs=["duty_cycle"])},
        variables=[_var("h")],  # duty_cycle missing
    )
    violations = check_variable_refs(parsed)
    assert any("duty_cycle" in v for v in violations)
    assert any("drag" in v for v in violations)


def test_variable_refs_suggests_close_match():
    parsed = _make(
        disciplines={"drag": _disc(inputs=["h"], outputs=["duty_cyclee"])},  # typo
        variables=[_var("h"), _var("duty_cycle")],
    )
    violations = check_variable_refs(parsed)
    assert any("duty_cyclee" in v for v in violations)
    assert any("duty_cycle" in v for v in violations)
    assert any("did you mean 'duty_cycle'?" in v for v in violations)


def test_variable_refs_skipped_when_no_explicit_variables():
    parsed = _make(
        disciplines={
            "drag": _disc(inputs=["h"], outputs=["duty_cycle"]),
            "power": _disc(inputs=["duty_cycle"], outputs=["power_margin"]),
        }
    )
    assert check_variable_refs(parsed) == []


def test_variable_refs_ok():
    parsed = _make(
        disciplines={"drag": _disc(inputs=["h"], outputs=["duty_cycle"])},
        variables=[_var("h"), _var("duty_cycle")],
    )
    assert check_variable_refs(parsed) == []


def test_variable_refs_scenario_design_variable_unknown():
    parsed = _make(
        disciplines={"d": _disc(inputs=["x"], outputs=["y"])},
        variables=[_var("x"), _var("y")],
        scenarios={
            "s": TomlScenario(
                design_variables=["z"],  # unknown
                disciplines=["d"],
                objective=TomlObjective(variable="y"),
            )
        },
    )
    violations = check_variable_refs(parsed)
    assert any("z" in v for v in violations)


def test_variable_refs_scenario_objective_unknown():
    parsed = _make(
        disciplines={"d": _disc(inputs=["x"], outputs=["y"])},
        variables=[_var("x"), _var("y")],
        scenarios={
            "s": TomlScenario(
                design_variables=["x"],
                disciplines=["d"],
                objective=TomlObjective(variable="obj"),  # unknown
            )
        },
    )
    violations = check_variable_refs(parsed)
    assert any("obj" in v for v in violations)


def test_variable_refs_scenario_constraint_unknown():
    parsed = _make(
        disciplines={"d": _disc(inputs=["x"], outputs=["y"])},
        variables=[_var("x"), _var("y")],
        scenarios={
            "s": TomlScenario(
                design_variables=["x"],
                disciplines=["d"],
                objective=TomlObjective(variable="y"),
                constraints=[TomlConstraint(variable="c")],  # unknown
            )
        },
    )
    violations = check_variable_refs(parsed)
    assert any("c" in v for v in violations)


def test_variable_refs_scenario_observable_unknown():
    parsed = _make(
        disciplines={"d": _disc(inputs=["x"], outputs=["y"])},
        variables=[_var("x"), _var("y")],
        scenarios={
            "s": TomlScenario(
                design_variables=["x"],
                disciplines=["d"],
                objective=TomlObjective(variable="y"),
                observables=["obs"],  # unknown
            )
        },
    )
    violations = check_variable_refs(parsed)
    assert any("obs" in v for v in violations)


def test_variable_refs_scenario_all_known():
    parsed = _make(
        disciplines={"d": _disc(inputs=["x"], outputs=["y", "c", "obs"])},
        variables=[_var("x"), _var("y"), _var("c"), _var("obs")],
        scenarios={
            "s": TomlScenario(
                design_variables=["x"],
                disciplines=["d"],
                objective=TomlObjective(variable="y"),
                constraints=[TomlConstraint(variable="c")],
                observables=["obs"],
            )
        },
    )
    assert check_variable_refs(parsed) == []


# -- check_scenario_disciplines ------------------------------------------------


def test_scenario_missing_discipline():
    parsed = _make(
        disciplines={"drag": _disc(outputs=["f"])},
        scenarios={"vleo": _scenario(["drag", "ghost"], "f")},
    )
    violations = check_scenario_disciplines(parsed)
    assert any("ghost" in v for v in violations)
    assert any("vleo" in v for v in violations)


def test_scenario_disciplines_ok():
    parsed = _make(
        disciplines={
            "drag": _disc(outputs=["f"]),
            "power": _disc(inputs=["f"], outputs=["g"]),
        },
        scenarios={"vleo": _scenario(["drag", "power"], "g")},
    )
    assert check_scenario_disciplines(parsed) == []


# -- check_variable_bounds -----------------------------------------------------


def test_variable_bounds_lower_exceeds_upper():
    parsed = _make(variables=[_var("x", lower_bound=10.0, upper_bound=1.0)])
    violations = check_variable_bounds(parsed)
    assert len(violations) == 1
    assert "x" in violations[0]
    assert "lower_bound" in violations[0]
    assert "upper_bound" in violations[0]


def test_variable_bounds_equal_not_caught_for_non_design_var():
    # Equal bounds on a plain variable is now allowed (only design-var equal-bounds is an error)
    parsed = _make(variables=[_var("x", lower_bound=5.0, upper_bound=5.0)])
    assert check_variable_bounds(parsed) == []


def test_variable_bounds_ok():
    parsed = _make(variables=[_var("x", lower_bound=0.0, upper_bound=10.0)])
    assert check_variable_bounds(parsed) == []


def test_variable_bounds_skipped_when_none():
    parsed = _make(variables=[_var("x")])  # no bounds set
    assert check_variable_bounds(parsed) == []


def test_variable_bounds_list_element_exceeds():
    parsed = _make(
        variables=[
            TomlVariable(
                name="x",
                data_type="float",
                dimension=2,
                lower_bound=[0.0, 10.0],
                upper_bound=[5.0, 1.0],  # second element: lower (10.0) > upper (1.0)
            )
        ]
    )
    violations = check_variable_bounds(parsed)
    assert len(violations) == 1
    assert "x" in violations[0]


def test_variable_bounds_list_all_elements_ok():
    parsed = _make(
        variables=[
            TomlVariable(
                name="x",
                data_type="float",
                dimension=2,
                lower_bound=[0.0, 1.0],
                upper_bound=[5.0, 10.0],
            )
        ]
    )
    assert check_variable_bounds(parsed) == []


def test_variable_bounds_scalar_lower_list_upper():
    parsed = _make(
        variables=[
            TomlVariable(
                name="x",
                data_type="float",
                dimension=2,
                lower_bound=20.0,  # broadcasts to [20.0, 20.0]
                upper_bound=[5.0, 30.0],  # first element: 20.0 > 5.0
            )
        ]
    )
    violations = check_variable_bounds(parsed)
    assert len(violations) == 1


# -- check_design_variable_bounds ---------------------------------------------


def _design_scenario(design_vars: list[str], disc_name: str = "d") -> dict:
    return {
        "s": TomlScenario(
            design_variables=design_vars,
            disciplines=[disc_name],
            objective=TomlObjective(variable="y"),
        )
    }


def test_design_var_missing_lower_bound_is_ok():
    # GEMSEO treats a missing lower_bound as -inf.
    parsed = _make(
        disciplines={"d": _disc(inputs=["x"], outputs=["y"])},
        variables=[_var("x", upper_bound=10.0)],  # lower_bound missing
        scenarios=_design_scenario(["x"]),
    )
    assert check_design_variable_bounds(parsed) == []


def test_design_var_missing_upper_bound_is_ok():
    # GEMSEO treats a missing upper_bound as +inf.
    parsed = _make(
        disciplines={"d": _disc(inputs=["x"], outputs=["y"])},
        variables=[_var("x", lower_bound=0.0)],  # upper_bound missing
        scenarios=_design_scenario(["x"]),
    )
    assert check_design_variable_bounds(parsed) == []


def test_design_var_missing_both_bounds_is_ok():
    # Fully unbounded design variable maps to (-inf, +inf) in GEMSEO.
    parsed = _make(
        disciplines={"d": _disc(inputs=["x"], outputs=["y"])},
        variables=[_var("x")],  # no bounds at all
        scenarios=_design_scenario(["x"]),
    )
    assert check_design_variable_bounds(parsed) == []


def test_design_var_equal_bounds_is_error():
    parsed = _make(
        disciplines={"d": _disc(inputs=["x"], outputs=["y"])},
        variables=[_var("x", lower_bound=5.0, upper_bound=5.0)],
        scenarios=_design_scenario(["x"]),
    )
    violations = check_design_variable_bounds(parsed)
    assert any("x" in v for v in violations)
    assert any("constant" in v or "equal" in v.lower() for v in violations)


def test_design_var_valid_bounds():
    parsed = _make(
        disciplines={"d": _disc(inputs=["x"], outputs=["y"])},
        variables=[_var("x", lower_bound=0.0, upper_bound=10.0)],
        scenarios=_design_scenario(["x"]),
    )
    assert check_design_variable_bounds(parsed) == []


def test_non_design_var_missing_bounds_is_ok():
    parsed = _make(
        disciplines={"d": _disc(inputs=["x"], outputs=["y"])},
        variables=[_var("x")],  # no bounds - not used as design variable
        scenarios=_design_scenario([]),  # x not a design variable
    )
    assert check_design_variable_bounds(parsed) == []


def test_design_var_missing_default_is_error():
    # A design variable needs a starting point (x0); GEMSEO has no current value
    # without one, so optimization cannot begin.
    parsed = _make(
        disciplines={"d": _disc(inputs=["x"], outputs=["y"])},
        variables=[_var("x", lower_bound=0.0, upper_bound=10.0)],  # no default_value
        scenarios=_design_scenario(["x"]),
    )
    violations = check_design_variable_has_default(parsed)
    assert any("x" in v for v in violations)
    assert any("default_value" in v for v in violations)


def test_design_var_with_default_is_ok():
    parsed = _make(
        disciplines={"d": _disc(inputs=["x"], outputs=["y"])},
        variables=[_var_with_default("x", default=5.0, lower=0.0, upper=10.0)],
        scenarios=_design_scenario(["x"]),
    )
    assert check_design_variable_has_default(parsed) == []


def test_non_design_var_missing_default_is_ok():
    # Coupling / non-design variables do not need a default.
    parsed = _make(
        disciplines={"d": _disc(inputs=["x"], outputs=["y"])},
        variables=[_var("x")],  # no default, not a design variable
        scenarios=_design_scenario([]),
    )
    assert check_design_variable_has_default(parsed) == []


# -- check_normalized_name_collisions -----------------------------------------


def test_discipline_name_collision():
    # "my_disc" and "my disc" both pascalify to "MyDisc"
    parsed = _make(
        disciplines={
            "my_disc": _disc(outputs=["f"]),
            "my disc": _disc(outputs=["g"]),
        }
    )
    violations = check_normalized_name_collisions(parsed)
    assert any("Discipline" in v for v in violations)
    assert any("my_disc" in v or "my disc" in v for v in violations)


def test_variable_name_collision():
    # "my var" and "my_var" both slugify to "my_var"
    parsed = _make(
        disciplines={"d": _disc(outputs=["f"])},
        variables=[_var("my var"), _var("my_var")],
    )
    violations = check_normalized_name_collisions(parsed)
    assert any("Variable" in v for v in violations)


def test_no_name_collisions():
    parsed = _make(
        disciplines={
            "drag": _disc(outputs=["f"]),
            "power": _disc(inputs=["f"], outputs=["g"]),
        }
    )
    assert check_normalized_name_collisions(parsed) == []


# -- check_dimension ----------------------------------------------------------


def test_dimension_zero_is_invalid():
    parsed = _make(variables=[_var("x", dimension=0)])
    violations = check_dimension(parsed)
    assert any("x" in v for v in violations)
    assert any("dimension" in v.lower() or "1" in v for v in violations)


def test_dimension_negative_is_invalid():
    parsed = _make(variables=[_var("x", dimension=-3)])
    violations = check_dimension(parsed)
    assert any("x" in v for v in violations)


def test_dimension_greater_than_one_is_valid():
    parsed = _make(variables=[_var("x", dimension=2)])
    assert check_dimension(parsed) == []


def test_dimension_one_is_valid():
    parsed = _make(variables=[_var("x", dimension=1)])
    assert check_dimension(parsed) == []


# -- check_bound_dimensions ---------------------------------------------------


def test_bound_dimensions_lower_bound_wrong_length():
    parsed = _make(
        variables=[
            TomlVariable(
                name="x",
                data_type="float",
                dimension=3,
                lower_bound=[0.0, 1.0],  # only 2 elements, dimension is 3
            )
        ]
    )
    violations = check_bound_dimensions(parsed)
    assert any("x" in v for v in violations)
    assert any("lower_bound" in v for v in violations)


def test_bound_dimensions_upper_bound_wrong_length():
    parsed = _make(
        variables=[
            TomlVariable(
                name="x",
                data_type="float",
                dimension=2,
                upper_bound=[0.0, 1.0, 2.0],  # 3 elements, dimension is 2
            )
        ]
    )
    violations = check_bound_dimensions(parsed)
    assert any("x" in v for v in violations)
    assert any("upper_bound" in v for v in violations)


def test_bound_dimensions_default_value_wrong_length():
    parsed = _make(
        variables=[
            TomlVariable(
                name="x",
                data_type="float",
                dimension=3,
                default_value=[1.0, 2.0],
            )
        ]
    )
    violations = check_bound_dimensions(parsed)
    assert any("x" in v for v in violations)
    assert any("default_value" in v for v in violations)


def test_bound_dimensions_correct_length_list_ok():
    parsed = _make(
        variables=[
            TomlVariable(
                name="x",
                data_type="float",
                dimension=3,
                lower_bound=[0.0, 1.0, 2.0],
                upper_bound=[10.0, 11.0, 12.0],
                default_value=[1.0, 2.0, 3.0],
            )
        ]
    )
    assert check_bound_dimensions(parsed) == []


def test_bound_dimensions_scalar_always_ok():
    parsed = _make(
        variables=[
            TomlVariable(
                name="x",
                data_type="float",
                dimension=3,
                lower_bound=0.0,
                upper_bound=10.0,
                default_value=1.0,
            )
        ]
    )
    assert check_bound_dimensions(parsed) == []


def test_bound_dimensions_none_always_ok():
    parsed = _make(variables=[_var("x", dimension=3)])
    assert check_bound_dimensions(parsed) == []


# -- check_default_value_in_bounds ---------------------------------------------


def test_default_below_lower_bound():
    parsed = _make(variables=[_var_with_default("x", default=-1.0, lower=0.0)])
    violations = check_default_value_in_bounds(parsed)
    assert any("x" in v for v in violations)
    assert any("default_value" in v or "lower_bound" in v for v in violations)


def test_default_above_upper_bound():
    parsed = _make(variables=[_var_with_default("x", default=15.0, upper=10.0)])
    violations = check_default_value_in_bounds(parsed)
    assert any("x" in v for v in violations)


def test_default_at_lower_bound_is_valid():
    parsed = _make(
        variables=[_var_with_default("x", default=0.0, lower=0.0, upper=10.0)]
    )
    assert check_default_value_in_bounds(parsed) == []


def test_default_at_upper_bound_is_valid():
    parsed = _make(
        variables=[_var_with_default("x", default=10.0, lower=0.0, upper=10.0)]
    )
    assert check_default_value_in_bounds(parsed) == []


def test_default_within_bounds_is_valid():
    parsed = _make(
        variables=[_var_with_default("x", default=5.0, lower=0.0, upper=10.0)]
    )
    assert check_default_value_in_bounds(parsed) == []


def test_no_default_skipped():
    parsed = _make(variables=[_var("x", lower_bound=0.0, upper_bound=10.0)])
    assert check_default_value_in_bounds(parsed) == []


def test_default_list_element_below_lower_bound():
    parsed = _make(
        variables=[
            TomlVariable(
                name="x",
                data_type="float",
                dimension=2,
                default_value=[5.0, -1.0],
                lower_bound=0.0,
            )
        ]
    )
    violations = check_default_value_in_bounds(parsed)
    assert any("x" in v for v in violations)


def test_default_list_all_elements_within_bounds():
    parsed = _make(
        variables=[
            TomlVariable(
                name="x",
                data_type="float",
                dimension=2,
                default_value=[1.0, 2.0],
                lower_bound=0.0,
                upper_bound=10.0,
            )
        ]
    )
    assert check_default_value_in_bounds(parsed) == []


def test_default_value_in_bounds_does_not_crash_on_length_mismatch():
    """A too-short lower_bound list must not crash check_default_value_in_bounds
    with IndexError -- check_bound_dimensions is responsible for reporting the
    length mismatch itself."""
    parsed = _make(
        variables=[
            TomlVariable(
                name="x",
                data_type="float",
                dimension=3,
                default_value=[1.0, 2.0, 3.0],
                lower_bound=[0.0, 0.0],  # only 2 elements, dimension is 3
            )
        ]
    )
    # Must not raise IndexError.
    check_default_value_in_bounds(parsed)


# -- check_objective_is_output -------------------------------------------------


def test_objective_not_a_discipline_output():
    parsed = _make(
        disciplines={"d": _disc(inputs=["x"], outputs=["y"])},
        scenarios={
            "s": TomlScenario(
                design_variables=["x"],
                disciplines=["d"],
                objective=TomlObjective(variable="z"),  # not an output
            )
        },
    )
    violations = check_objective_is_output(parsed)
    assert any("z" in v for v in violations)
    assert any("s" in v for v in violations)


def test_objective_suggests_close_match():
    parsed = _make(
        disciplines={"d": _disc(inputs=["x"], outputs=["drag"])},
        scenarios={
            "s": TomlScenario(
                design_variables=["x"],
                disciplines=["d"],
                objective=TomlObjective(variable="dragg"),  # near-miss typo
            )
        },
    )
    violations = check_objective_is_output(parsed)
    assert any("did you mean 'drag'?" in v for v in violations)


def test_objective_is_discipline_output_ok():
    parsed = _make(
        disciplines={"d": _disc(inputs=["x"], outputs=["y"])},
        scenarios={
            "s": TomlScenario(
                design_variables=["x"],
                disciplines=["d"],
                objective=TomlObjective(variable="y"),
            )
        },
    )
    assert check_objective_is_output(parsed) == []


# -- check_objective_is_scalar -------------------------------------------------


def test_objective_with_dimension_greater_than_one_is_invalid():
    parsed = _make(
        disciplines={"d": _disc(inputs=["x"], outputs=["y"])},
        variables=[_var("x"), _var("y", dimension=3)],
        scenarios={
            "s": TomlScenario(
                design_variables=["x"],
                disciplines=["d"],
                objective=TomlObjective(variable="y"),
            )
        },
    )
    violations = check_objective_is_scalar(parsed)
    assert any("y" in v for v in violations)
    assert any("s" in v for v in violations)
    assert any("not yet supported" in v for v in violations)


def test_objective_with_dimension_one_is_valid():
    parsed = _make(
        disciplines={"d": _disc(inputs=["x"], outputs=["y"])},
        variables=[_var("x"), _var("y", dimension=1)],
        scenarios={
            "s": TomlScenario(
                design_variables=["x"],
                disciplines=["d"],
                objective=TomlObjective(variable="y"),
            )
        },
    )
    assert check_objective_is_scalar(parsed) == []


def test_objective_scalar_check_skips_unknown_variable():
    """Unknown objective variable is caught by check_variable_refs, not here."""
    parsed = _make(
        disciplines={"d": _disc(inputs=["x"], outputs=["y"])},
        variables=[_var("x"), _var("y")],
        scenarios={
            "s": TomlScenario(
                design_variables=["x"],
                disciplines=["d"],
                objective=TomlObjective(variable="unknown"),
            )
        },
    )
    assert check_objective_is_scalar(parsed) == []


# -- check_constraint_outputs --------------------------------------------------


def test_constraint_not_a_discipline_output():
    parsed = _make(
        disciplines={"d": _disc(inputs=["x"], outputs=["y"])},
        scenarios={
            "s": TomlScenario(
                design_variables=["x"],
                disciplines=["d"],
                objective=TomlObjective(variable="y"),
                constraints=[TomlConstraint(variable="c")],  # not an output
            )
        },
    )
    violations = check_constraint_outputs(parsed)
    assert any("c" in v for v in violations)


def test_constraint_suggests_close_match():
    parsed = _make(
        disciplines={"d": _disc(inputs=["x"], outputs=["drag"])},
        scenarios={
            "s": TomlScenario(
                design_variables=["x"],
                disciplines=["d"],
                objective=TomlObjective(variable="drag"),
                constraints=[TomlConstraint(variable="dragg")],  # near-miss typo
            )
        },
    )
    violations = check_constraint_outputs(parsed)
    assert any("did you mean 'drag'?" in v for v in violations)


def test_constraint_is_discipline_output_ok():
    parsed = _make(
        disciplines={"d": _disc(inputs=["x"], outputs=["y", "c"])},
        scenarios={
            "s": TomlScenario(
                design_variables=["x"],
                disciplines=["d"],
                objective=TomlObjective(variable="y"),
                constraints=[TomlConstraint(variable="c")],
            )
        },
    )
    assert check_constraint_outputs(parsed) == []


# -- check_orphan_variables ---------------------------------------------------


def test_orphan_variable_detected():
    parsed = _make(
        disciplines={"d": _disc(inputs=["x"], outputs=["y"])},
        variables=[_var("x"), _var("y"), _var("orphan")],
    )
    violations = check_orphan_variables(parsed)
    assert any("orphan" in v for v in violations)


def test_no_orphan_when_used_as_design_var():
    parsed = _make(
        disciplines={"d": _disc(inputs=["x"], outputs=["y"])},
        variables=[_var("x"), _var("y"), _var("dv")],
        scenarios={
            "s": TomlScenario(
                design_variables=["dv"],
                disciplines=["d"],
                objective=TomlObjective(variable="y"),
            )
        },
    )
    assert check_orphan_variables(parsed) == []


def test_no_orphan_when_used_as_objective():
    parsed = _make(
        disciplines={"d": _disc(inputs=["x"], outputs=["y"])},
        variables=[_var("x"), _var("y")],
        scenarios={
            "s": TomlScenario(
                design_variables=["x"],
                disciplines=["d"],
                objective=TomlObjective(variable="y"),
            )
        },
    )
    assert check_orphan_variables(parsed) == []


def test_no_orphan_when_used_as_constraint():
    parsed = _make(
        disciplines={"d": _disc(inputs=["x"], outputs=["y", "c"])},
        variables=[_var("x"), _var("y"), _var("c")],
        scenarios={
            "s": TomlScenario(
                design_variables=["x"],
                disciplines=["d"],
                objective=TomlObjective(variable="y"),
                constraints=[TomlConstraint(variable="c")],  # c only referenced here
            )
        },
    )
    assert check_orphan_variables(parsed) == []


def test_no_orphan_when_used_as_observable():
    parsed = _make(
        disciplines={"d": _disc(inputs=["x"], outputs=["y", "obs"])},
        variables=[_var("x"), _var("y"), _var("obs")],
        scenarios={
            "s": TomlScenario(
                design_variables=["x"],
                disciplines=["d"],
                objective=TomlObjective(variable="y"),
                observables=["obs"],  # obs only referenced here
            )
        },
    )
    assert check_orphan_variables(parsed) == []


def test_no_orphans_when_all_referenced():
    parsed = _make(
        disciplines={"d": _disc(inputs=["x"], outputs=["y"])},
        variables=[_var("x"), _var("y")],
    )
    assert check_orphan_variables(parsed) == []


# -- check_observable_outputs --------------------------------------------------


def test_observable_not_a_discipline_output():
    parsed = _make(
        disciplines={"d": _disc(inputs=["x"], outputs=["y"])},
        scenarios={
            "s": TomlScenario(
                design_variables=["x"],
                disciplines=["d"],
                objective=TomlObjective(variable="y"),
                observables=["obs"],  # not an output
            )
        },
    )
    violations = check_observable_outputs(parsed)
    assert any("obs" in v for v in violations)


def test_observable_suggests_close_match():
    parsed = _make(
        disciplines={"d": _disc(inputs=["x"], outputs=["drag"])},
        scenarios={
            "s": TomlScenario(
                design_variables=["x"],
                disciplines=["d"],
                objective=TomlObjective(variable="drag"),
                observables=["dragg"],  # near-miss typo
            )
        },
    )
    violations = check_observable_outputs(parsed)
    assert any("did you mean 'drag'?" in v for v in violations)


def test_observable_is_discipline_output_ok():
    parsed = _make(
        disciplines={"d": _disc(inputs=["x"], outputs=["y", "obs"])},
        scenarios={
            "s": TomlScenario(
                design_variables=["x"],
                disciplines=["d"],
                objective=TomlObjective(variable="y"),
                observables=["obs"],
            )
        },
    )
    assert check_observable_outputs(parsed) == []


# -- check_discipline_inputs ---------------------------------------------------


def test_discipline_no_inputs_is_error():
    parsed = _make(disciplines={"sink": _disc(inputs=[], outputs=["f"])})
    violations = check_discipline_inputs(parsed)
    assert any("sink" in v for v in violations)
    assert any("input" in v.lower() for v in violations)


def test_discipline_with_inputs_ok():
    parsed = _make(disciplines={"d": _disc(inputs=["x"], outputs=["y"])})
    assert check_discipline_inputs(parsed) == []


# -- check_discipline_outputs --------------------------------------------------


def test_discipline_no_outputs_is_warning():
    parsed = _make(disciplines={"source": _disc(inputs=["x"], outputs=[])})
    warnings = check_discipline_outputs(parsed)
    assert any("source" in w for w in warnings)
    assert any("output" in w.lower() for w in warnings)


def test_discipline_with_outputs_no_warning():
    parsed = _make(disciplines={"d": _disc(inputs=["x"], outputs=["y"])})
    assert check_discipline_outputs(parsed) == []


def test_run_all_discipline_no_outputs_is_warning_not_error():
    parsed = _make(
        disciplines={
            "d": _disc(inputs=["x"], outputs=["y"]),
            "sink": _disc(inputs=["y"], outputs=[]),
        }
    )
    errors, warnings = run_all(parsed)
    assert not any("sink" in e for e in errors)
    assert any("sink" in w for w in warnings)


def test_valid_toml_with_warning_returns_non_empty_warnings(tmp_path):
    """A discipline with no outputs produces a warning, not an error (pipeline-level)."""
    p = tmp_path / "problem.toml"
    p.write_text(
        '[disciplines.drag]\ninputs = ["h"]\noutputs = ["duty_cycle"]\n'
        '[disciplines.sink]\ninputs = ["duty_cycle"]\noutputs = []\n\n'
        '[[variables]]\nname = "h"\nunit = "m"\ndata_type = "float"\ndimension = 1\n\n'
        '[[variables]]\nname = "duty_cycle"\nunit = "-"\ndata_type = "float"\ndimension = 1\n'
    )
    from gemseo_gantry.validation import ValidationResult, validate_toml

    result = validate_toml(p)
    assert isinstance(result, ValidationResult)
    assert result.problem is not None
    assert any("sink" in w for w in result.warnings)


# -- check_design_variable_not_output -----------------------------------------


def test_design_var_is_discipline_output_error():
    parsed = _make(
        disciplines={
            "d": _disc(inputs=["u"], outputs=["x", "y"]),
        },
        variables=[_var("x"), _var("y"), _var("u")],
        scenarios={
            "s": TomlScenario(
                design_variables=["x"],  # x is also an output of d
                disciplines=["d"],
                objective=TomlObjective(variable="y"),
            )
        },
    )
    violations = check_design_variable_not_output(parsed)
    assert any("x" in v for v in violations)
    assert any("d" in v for v in violations)
    assert any("s" in v for v in violations)


def test_design_var_not_discipline_output_ok():
    parsed = _make(
        disciplines={"d": _disc(inputs=["x"], outputs=["y"])},
        variables=[_var("x"), _var("y")],
        scenarios={
            "s": TomlScenario(
                design_variables=["x"],
                disciplines=["d"],
                objective=TomlObjective(variable="y"),
            )
        },
    )
    assert check_design_variable_not_output(parsed) == []


# -- run_all -------------------------------------------------------------------


def test_run_all_returns_errors_and_warnings():
    parsed = _make(
        disciplines={
            "drag": _disc(inputs=["h"], outputs=["duty_cycle"]),
            "power": _disc(inputs=["h"], outputs=["duty_cycle"]),  # double output
        },
        scenarios={
            "vleo": _scenario(["drag", "power", "ghost"], "duty_cycle")
        },  # ghost missing
    )
    errors, _ = run_all(parsed)
    assert any("duty_cycle" in v for v in errors)
    assert any("ghost" in v for v in errors)


def test_run_all_includes_bound_dimension_violations():
    parsed = _make(
        disciplines={"d": _disc(inputs=["x"], outputs=["y"])},
        variables=[
            TomlVariable(
                name="x",
                data_type="float",
                dimension=3,
                lower_bound=[0.0, 1.0],  # wrong length
            ),
            _var("y"),
        ],
    )
    errors, _ = run_all(parsed)
    assert any("lower_bound" in e and "x" in e for e in errors)


def test_run_all_includes_objective_scalar_violations():
    parsed = _make(
        disciplines={"d": _disc(inputs=["x"], outputs=["y"])},
        variables=[_var("x"), _var("y", dimension=2)],
        scenarios={
            "s": TomlScenario(
                design_variables=["x"],
                disciplines=["d"],
                objective=TomlObjective(variable="y"),
            )
        },
    )
    errors, _ = run_all(parsed)
    assert any("not yet supported" in e for e in errors)


# -- sub-scenario continue branches --------------------------------------------


def _sub_scenario_parsed():
    """A TomlProblemDefinition where 'top' scenario lists only a sub-scenario."""
    from gemseo_gantry.parser.toml_data_model import TomlProblemDefinition

    raw = {
        "disciplines": {"drag": {"inputs": ["x"], "outputs": ["y"]}},
        "scenarios": {
            "sub1": {
                "disciplines": ["drag"],
                "design_variables": ["x"],
                "objective": {"variable": "y"},
            },
            "top": {
                # "sub1" is a scenario name, not a discipline -> outputs will be empty
                "disciplines": ["sub1"],
                "design_variables": ["x"],
                "objective": {"variable": "y"},
                "constraints": [{"variable": "y", "operator": "<", "value": 0.0}],
                "observables": ["y"],
            },
        },
    }
    return TomlProblemDefinition.model_validate(raw)


def test_check_objective_skips_all_subscenario_disciplines() -> None:
    """check_objective_is_output continues (no error) when all disciplines are
    sub-scenarios -- covers line 226."""
    from gemseo_gantry.validation.semantic import check_objective_is_output

    parsed = _sub_scenario_parsed()
    errors = check_objective_is_output(parsed)
    assert errors == []


def test_check_constraints_skips_all_subscenario_disciplines() -> None:
    """check_constraint_outputs continues when all disciplines are sub-scenarios
    -- covers line 245."""
    from gemseo_gantry.validation.semantic import check_constraint_outputs

    parsed = _sub_scenario_parsed()
    errors = check_constraint_outputs(parsed)
    assert errors == []


def test_check_observables_skips_all_subscenario_disciplines() -> None:
    """check_observable_outputs continues when all disciplines are sub-scenarios
    -- covers line 265."""
    from gemseo_gantry.validation.semantic import check_observable_outputs

    parsed = _sub_scenario_parsed()
    errors = check_observable_outputs(parsed)
    assert errors == []


# -- check_missing_units ------------------------------------------------------


def test_check_missing_units_no_warning_when_unit_set():
    parsed = _make(
        disciplines={"d": _disc(inputs=["x"], outputs=["y"])},
        variables=[_var("x", unit="m"), _var("y", unit="km")],
    )
    assert check_missing_units(parsed) == []


def test_check_missing_units_warns_when_unit_is_none():
    v = TomlVariable(name="x", data_type="float", dimension=1)  # unit=None
    parsed = _make(
        disciplines={"d": _disc(inputs=["x"])},
        variables=[v],
    )
    warnings = check_missing_units(parsed)
    assert len(warnings) == 1
    assert "x" in warnings[0]
    assert "unit" in warnings[0]


def test_check_missing_units_empty_string_suppresses_warning():
    v = TomlVariable(name="x", unit="", data_type="float", dimension=1)
    parsed = _make(
        disciplines={"d": _disc(inputs=["x"])},
        variables=[v],
    )
    assert check_missing_units(parsed) == []


def test_run_all_missing_unit_goes_to_warnings_not_errors():
    v = TomlVariable(name="x", data_type="float", dimension=1)  # unit=None
    parsed = _make(
        disciplines={"d": _disc(inputs=["x"], outputs=["y"])},
        variables=[v, _var("y")],
    )
    errors, warnings = run_all(parsed)
    assert not any("unit" in e for e in errors)
    assert any("unit" in w for w in warnings)
