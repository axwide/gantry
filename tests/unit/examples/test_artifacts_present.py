from gemseo_gantry.examples.registry import get_example


def test_shipped_tree_is_complete():
    root = get_example("sellar").root
    assert (root / "sellar.toml").is_file()
    assert (root / "postprocess.py").is_file()
    assert (root / "execute_Sellar.py").is_file()
    discs = {
        p.name for p in (root / "disciplines").glob("*.py") if p.name != "__init__.py"
    }
    assert discs == {
        "Sellar1.py",
        "Sellar2.py",
        "SellarSystem.py",
    }


def test_executor_is_tuned_not_placeholder():
    root = get_example("sellar").root
    text = (root / "execute_Sellar.py").read_text(encoding="utf-8")
    assert "max_iter=3)" not in text


def test_postprocess_emits_parseable_objective():
    root = get_example("sellar").root
    text = (root / "postprocess.py").read_text(encoding="utf-8")
    assert "OPTIMUM_OBJECTIVE:" in text
