import typer

from .build import build
from .diagram import diagram_app
from .example import example
from .init import init
from .scaffold import scaffold
from .schema import schema
from .validate import validate

app = typer.Typer(
    no_args_is_help=True,
    help="Generate GEMSEO glue code for MDAO problems from a TOML problem definition.",
    context_settings={"help_option_names": ["-h", "--help"]},
)

app.command("init")(init)
app.command("build")(build)
app.command("scaffold")(scaffold)
app.command("example")(example)
app.command("schema")(schema)
app.command("validate")(validate)
app.add_typer(
    diagram_app,
    name="diagram",
    no_args_is_help=True,
    help="Generate N2 or XDSM diagrams from a problem definition TOML.",
)
