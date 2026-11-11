from pathlib import Path

from gemseo_gantry.cli._artifacts import rel_to_cwd


def test_rel_to_cwd_inside_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    p = tmp_path / "lib" / "Drag_io.py"
    assert rel_to_cwd(p) == "lib/Drag_io.py"


def test_rel_to_cwd_outside_cwd_returns_posix(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    outside = Path("/somewhere/else/file.py")
    assert rel_to_cwd(outside) == "/somewhere/else/file.py"
