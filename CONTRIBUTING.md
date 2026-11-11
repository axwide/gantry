# Contributing to gemseo-gantry

Thanks for helping out. This guide explains how to set up a development environment, which checks a change has to pass, and the conventions the code follows.

## Development setup

The project uses [`uv`](https://docs.astral.sh/uv/) for environment and dependency management, and [`prek`](https://github.com/j178/prek) for git hooks.

```bash
uv sync                # create the virtual environment and install dev dependencies
uv run prek install    # install the pre-commit and commit-msg hooks
```

## Checks

Every change must pass the same checks CI runs:

```bash
uv run ruff check --extend-select I .   # lint (including import sorting)
uv run ruff format --check .            # formatting
uv run basedpyright src/                # type check
uv run pytest                           # tests (with a 90% coverage floor)
```

The pre-commit hooks run ruff, basedpyright and the unit tests (`tests/unit/`) on every commit. Generated-code output is covered by snapshot tests ([syrupy](https://github.com/syrupy-project/syrupy)); after an intentional change to a template, update the snapshots with `uv run pytest --snapshot-update` and review the diff.

## Conventions

### Docstrings

Use **Google style** docstrings for all Python modules, classes, and functions.

### Lazy imports

- **Internal modules:** use `lazy.attach` in the package's `__init__.py` (exposes submodules/symbols lazily via `__getattr__`).
- **External packages:** use `lazy.load("package")` at module level in the importing file.
- Never `lazy.load("pkg.subpkg")`. Loading a subpackage eagerly imports its parent.

### Idiomatic by default

Prefer a library's idiomatic, "with-the-grain" approach over a custom one, even if it slightly diverges from the original ask. Mention the divergence in the PR description when it touches intent or a requirement, or when our own idiom conflicts with the library's (we can change ours, not theirs).

For GEMSEO, check the [documented API](https://gemseo.readthedocs.io/) first, and fall back to the installed source (`uv run python -c "import gemseo; print(gemseo.__file__)"`) for version-exact or internal-API behaviour.

### Code quality

Write for maintainability and refactorability. Assume some future change you can't predict yet will build on what you write now. Clear boundaries and well-named seams make that change cheap.

## Branches, commits and pull requests

- **Branches** follow the [Conventional Branch](https://conventional-branch.github.io/) naming convention, including the issue number when there is one, e.g. `feat/42-vector-objectives` or `fix/17-dry-run-output`.
- **Commits** follow [Conventional Commits](https://www.conventionalcommits.org/) (enforced by the `commit-msg` hook), e.g. `feat: support vector objectives`.
- **Pull requests** are opened as **drafts** until the change is complete; CI runs once a PR is marked ready for review. When the linked issue belongs to a milestone, add the PR to the same milestone.

## Reporting bugs and vulnerabilities

Report bugs and feature requests as [GitHub issues](https://github.com/axwide/gantry/issues). Do **not** report security vulnerabilities in public issues; report them privately via the repository's [Security tab](https://github.com/axwide/gantry/security/advisories/new).
