import pytest
from PIL import Image
from bingo_king.image_utils import (
    get_bingo_number_coords,
)
from bingo_king.main import (
    BingoGameLogic,
    reverse_lookup,
    ROOT_DIR,
)

TEST_DATA = [
    {
        'filename': f'{ROOT_DIR}/tests/screenshots/crown_logic_1.png',
        'game_state': [
            [5, 0, 0, 0, 2],
            [0, 1, 1, 2, 0],
            [1, 1, 2, 0, 0],
            [1, 2, 0, 1, 1],
            [2, 1, 1, 0, 0],
        ]
    }
]


@pytest.fixture(params=TEST_DATA, ids=lambda d: d['filename'])
def test_case(request):
    return request.param


def test_image_processing(test_case):
    image = Image.open(test_case['filename']).convert('L')
    game_board, number_coords = get_bingo_number_coords(image)
    number_lookup = reverse_lookup(number_coords)
    game = BingoGameLogic(
        game_board,
        number_coords,
        test_case['game_state'],
        number_lookup
    )
    most_needed_spots = game.most_needed_spots()
    most_needed_numbers = [number_lookup[col][row] for row, col in most_needed_spots]
    assert most_needed_numbers[0] == '70'
    assert most_needed_numbers[1] == '6'
    assert most_needed_numbers[2] == '25'
