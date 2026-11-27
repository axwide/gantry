from __future__ import annotations

import subprocess
import sys


def test_module_runs_as_main():
    result = subprocess.run(
        [sys.executable, "-m", "gemseo_gantry", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "Usage" in result.stdout
    assert "scaffold" in result.stdout
