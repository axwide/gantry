from gemseo_gantry.model.data_model import (
    Discipline,
    FormulationType,
    Objective,
    ProblemDefinition,
    Scenario,
    Variable,
)


def _scenario(
    name, disciplines, design_variables=("x",), objective="obj", formulation=None
):
    return Scenario(
        name=name,
        design_variables=list(design_variables),
        disciplines=list(disciplines),
        formulation_type="MDO",
        formulation=formulation,
        objective=Objective(variable=objective),
        constraints=[],
    )


def _problem(scenarios):
    return ProblemDefinition(
        variables=[Variable(name="x", data_type="float", dimension=1)],
        disciplines=[Discipline(name="DiscA", inputs=["x"], outputs=["obj"])],
        scenarios=scenarios,
    )


def test_leaf_scenario_defaults_to_mdf():
    leaf = _scenario("Leaf", ["DiscA"])
    problem = _problem([leaf])
    assert problem.resolve_formulation(leaf) == FormulationType.MDF


def test_nesting_scenario_defaults_to_bilevel_bcd():
    sub = _scenario("Sub", ["DiscA"])
    root = _scenario("Root", ["DiscA", "Sub"])
    problem = _problem([sub, root])
    assert problem.resolve_formulation(root) == FormulationType.BILEVEL_BCD
    assert problem.resolve_formulation(sub) == FormulationType.MDF


def test_explicit_formulation_wins():
    leaf = _scenario("Leaf", ["DiscA"], formulation=FormulationType.IDF)
    problem = _problem([leaf])
    assert problem.resolve_formulation(leaf) == FormulationType.IDF


def test_sub_and_plain_partition():
    sub = _scenario("Sub", ["DiscA"])
    root = _scenario("Root", ["DiscA", "Sub"])
    problem = _problem([sub, root])
    assert problem.sub_scenario_names_of(root) == ["Sub"]
    assert problem.plain_discipline_names_of(root) == ["DiscA"]
    assert problem.sub_scenario_names == {"Sub"}


def test_root_detection():
    sub = _scenario("Sub", ["DiscA"])
    root = _scenario("Root", ["DiscA", "Sub"])
    problem = _problem([sub, root])
    assert [s.name for s in problem.root_scenarios] == ["Root"]
