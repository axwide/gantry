from __future__ import annotations

from dataclasses import dataclass, field

from .registry import Example


@dataclass
class NarrationStep:
    title: str
    body: str
    command: str | None = None
    artifacts: list[str] = field(default_factory=list)


def _workflow_steps(example: Example) -> list[NarrationStep]:
    """The 8-step gantry workflow, narrated generically (reused by every example)."""
    return [
        NarrationStep(
            title="1. Problem definition",
            body=(
                "Everything starts from one annotated TOML configuration file that "
                "defines the problem. It has three kinds of sections:\n\n"
                "[cyan]\\[disciplines.<name>][/cyan]: each discipline's inputs and outputs\n"
                "[cyan]\\[scenarios.<name>][/cyan]: each scenario's design variables, objective and constraints\n"
                "[cyan]\\[\\[variables]][/cyan]: bounds, defaults, units and dimension for each variable\n\n"
                "You don't write any boilerplate, only this description of the problem."
            ),
            command=None,
        ),
        NarrationStep(
            title="2. gantry validate",
            body=(
                "`gantry validate` checks the TOML against the GEMSEO-Gantry schema "
                "and reports any syntax, structural, or semantic errors before you run anything.\n\n"
                "Run it with `--watch` to re-validate every time you save, which helps "
                "while you're working on a new problem definition. We won't use `--watch` here."
            ),
            command=f"gantry validate {example.name}.toml",
        ),
        NarrationStep(
            title="3. gantry build",
            body=(
                "`gantry build` generates the mechanical lib/ package: grammars, "
                "IO dataclasses, base classes and the design space. You never "
                "edit lib/; you make your changes to the problem's TOML and regenerate lib/ by re-running `gantry build`.\n\n"
                "It also writes a JSON Schema file for the TOML format so your IDE can "
                "validate and auto-complete the problem definition as you type, though it won't catch all the semantic errors that `gantry validate` does."
            ),
            command=f"gantry build {example.name}.toml",
        ),
        NarrationStep(
            title="4. Diagrams",
            body=(
                "`gantry diagram` renders the problem structure: an N2 chart of the "
                "disciplines and their coupling variables, and an XDSM of the "
                "optimization process. Both are written to diagrams/. Open them in a "
                "browser or PDF viewer to check the coupling before you fill in "
                "the physics."
            ),
            command=None,
        ),
        NarrationStep(
            title="5. gantry scaffold",
            body=(
                "`gantry scaffold` generates the files you own, which are discipline stubs, "
                "an executor script and a loader. The plumbing is already wired up: "
                "imports, IO dataclasses, base class, and a _run method with a "
                "marked region in the discipline for your computation. The bodies are placeholders."
            ),
            command=f"gantry scaffold {example.name}.toml",
        ),
        NarrationStep(
            title="6. Fill in the physics",
            body=(
                "This is the one step gantry can't do for you: replace the "
                "placeholder in each discipline's marked region with the real "
                "equations. " + example.physics_note
            ),
            command=None,
        ),
        NarrationStep(
            title="7. Run",
            body=(
                "The executor script created by `gantry scaffold` wires your "
                "disciplines into a GEMSEO scenario, instantiates it and runs "
                "it. Edit this file and set the formulation, optimizer, and any "
                "scenario settings you want before running. " + example.run_note
            ),
            command=f"uv run {example.executor}",
        ),
        NarrationStep(
            title="8. Post-process",
            body=(
                "`gantry scaffold` also creates a placeholder postprocessor. It doesn't do "
                "any real analysis. It shows how a post-processing script would start, "
                "by loading the saved history file and printing some of the data."
            ),
            command="uv run postprocess.py",
        ),
    ]


def build_narration(
    example: Example,
    *,
    artifacts_by_step: dict[int, list[str]] | None = None,
) -> list[NarrationStep]:
    """Intro + the 8 workflow steps + outro, as NarrationStep objects.

    artifacts_by_step maps a 1-based workflow step index (1..8) to files produced
    during that step; they are attached to that step's ``artifacts`` list.
    """
    artifacts_by_step = artifacts_by_step or {}
    workflow = _workflow_steps(example)
    for idx, step in enumerate(workflow, start=1):
        step.artifacts = list(artifacts_by_step.get(idx, []))

    intro = NarrationStep(title=f"Example: {example.name}", body=example.intro)
    outro = NarrationStep(title="Next steps", body=example.outro, command="gantry init")
    return [intro, *workflow, outro]
