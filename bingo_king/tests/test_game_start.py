import pytest
from PIL import Image
from image_utils import board_is_ready


@pytest.fixture(scope="module")
def game_start_image():
    game_start = Image.open('../assets/game_start_segment.png')
    game_start.load()
    return game_start


@pytest.mark.parametrize(
    "filename, expected",
    [
        ('screenshots/game_Start.png', True),
        ('screenshots/game_start_early.png', False),
        ('screenshots/game_start_early.png', False),
        ('screenshots/home.png', False),
    ]
)
def test_board_is_ready(filename, expected, game_start_image):
    image = Image.open(filename)
    actual = board_is_ready(image, game_start_image)
    assert actual == expected, f"Failed for {filename}"
