from __future__ import annotations

from pathlib import Path


def rel_to_cwd(path: Path) -> str:
    """Path relative to CWD when possible, else unchanged; always POSIX slashes."""
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return path.as_posix()
