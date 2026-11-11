from __future__ import annotations

from pathlib import Path

from ..registry import Example

EXAMPLE = Example(
    name="sellar",
    summary="Canonical Sellar MDO benchmark (feedback coupling, MDA + optimization).",
    root=Path(__file__).parent,
    intro=(
        "Sellar is the canonical multidisciplinary optimization benchmark: two "
        "coupled analysis disciplines (sellar_1 and sellar_2 feed each other "
        "through the coupling variables y_1 and y_2) plus a system discipline "
        "that computes the objective and two constraints. GEMSEO resolves the "
        "feedback coupling with an MDA (multi-disciplinary analysis), then optimizes."
    ),
    outro=(
        "You just generated, ran, and post-processed a complete MDO problem. "
        "Open sellar.toml and the discipline files to see how the physics "
        "maps to the generated plumbing, then try `gantry init` in a new directory to start your own."
    ),
    expected_objective=3.18,
    executor="execute_Sellar.py",
    objective_tolerance=0.3,
    physics_note="For this example we've filled in the Sellar physics.",
    run_note=(
        "This example ships a pre-configured executor that overwrites the "
        "scaffold default; it uses MDF formulation with COBYLA and saves the "
        "optimization history to Sellar.h5 on completion."
    ),
)
