from pathlib import Path
from unittest.mock import MagicMock, patch


def test_generate_coupling_diagrams_creates_folder_and_calls_gemseo(
    tmp_path: Path,
) -> None:
    from gemseo_gantry.generator.utils import generate_coupling_diagrams

    mock_scenario = MagicMock()
    save_folder = tmp_path / "diagrams"

    with (
        patch("gemseo_gantry.generator.utils.generate_n2_plot") as mock_n2,
        patch("gemseo_gantry.generator.utils.generate_xdsm") as mock_xdsm,
    ):
        generate_coupling_diagrams(mock_scenario, save_folder)

    assert save_folder.exists()
    mock_n2.assert_called_once_with(
        mock_scenario.disciplines,
        file_path=save_folder / "n2.png",
    )
    mock_xdsm.assert_called_once_with(mock_scenario, directory_path=save_folder)
