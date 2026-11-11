from __future__ import annotations

from pathlib import Path

from ..registry import Example

EXAMPLE = Example(
    name="sobieski",
    summary=(
        "Bilevel Sobieski SSBJ benchmark: three disciplinary sub-scenarios "
        "nested under a system scenario (BiLevelBCD)."
    ),
    root=Path(__file__).parent,
    intro=(
        "Sobieski's SSBJ is the canonical bilevel MDO benchmark: three "
        "disciplinary optimizations (structure, aerodynamics, propulsion) are "
        "nested as sub-scenarios inside a system-level scenario that also owns "
        "the mission discipline. GEMSEO's BiLevelBCD formulation coordinates "
        "the sub-scenarios to maximize the aircraft range."
    ),
    outro=(
        "You just generated, ran, and post-processed a nested bilevel MDO "
        "problem. Open sobieski.toml to see how the sub-scenarios are declared, "
        "and the disciplines/ files to see how each delegates to GEMSEO's "
        "reference SSBJ implementation."
    ),
    expected_objective=-4510.0,
    executor="execute_SystemScenario.py",
    objective_tolerance=100.0,
    physics_note=(
        "For this example each discipline delegates to GEMSEO's reference SSBJ "
        "implementation."
    ),
    run_note=(
        "This example ships a pre-configured executor: it builds the three "
        "disciplinary sub-scenarios with MDF and SLSQP, wraps them in a "
        "BiLevelBCD system scenario, runs COBYLA, and saves the optimization "
        "history to SystemScenario.h5 on completion."
    ),
)
