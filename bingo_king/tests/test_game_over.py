import pytest
from PIL import Image
from image_utils import is_game_over


@pytest.mark.parametrize(
    "filename, expected",
    [
        ('screenshots/game_over.png', True),
        ('screenshots/b_11_again.png', False),
        ('screenshots/another_game_over.png', True),
    ]
)
def test_is_game_over(filename, expected):
    game_over = Image.open('../assets/gameover.png')
    game_over.load()

    image = Image.open(filename)
    actual = is_game_over(image, game_over)

    assert actual == expected, f"Failed for {filename}"
