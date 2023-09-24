import pytest
from PIL import Image
from bingo_king.image_utils import is_game_over
from bingo_king.main import ROOT_DIR


@pytest.mark.parametrize(
    "filename, expected",
    [
        (f'{ROOT_DIR}/tests/screenshots/b_11_again.png', False),
        (f'{ROOT_DIR}/tests/screenshots/game_over_after_update.png', True),
    ]
)
def test_is_game_over(filename, expected):
    game_over = Image.open(f'{ROOT_DIR}/assets/gameover.png')
    game_over.load()

    image = Image.open(filename)
    actual = is_game_over(image, game_over)

    assert actual == expected, f"Failed for {filename}"
