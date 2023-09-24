import pytest
from PIL import Image
from bingo_king.image_utils import board_is_ready
from bingo_king.main import ROOT_DIR


@pytest.fixture(scope="module")
def game_start_image():
    game_start = Image.open(f'{ROOT_DIR}/assets/updated_game_start.jpg')
    game_start.load()
    return game_start


@pytest.mark.parametrize(
    "filename, expected",
    [
        (f'{ROOT_DIR}/tests/screenshots/game_Start.png', True),
        (f'{ROOT_DIR}/tests/screenshots/game_start_early.png', True),
        (f'{ROOT_DIR}/tests/screenshots/home.png', False),
    ]
)
def test_board_is_ready(filename, expected, game_start_image):
    image = Image.open(filename)
    actual = board_is_ready(image, game_start_image)
    assert actual == expected, f"Failed for {filename}"
