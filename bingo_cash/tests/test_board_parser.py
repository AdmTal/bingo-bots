import pytest
from PIL import Image
from image_utils import get_bingo_number_coords, to_5x5_matrix

TEST_DATA = [
    {
        'filename': 'screenshots/board_1.png',
        'expected': [
            ['7', '22', '34', '48', '64'],
            ['6', '18', '33', '57', '71'],
            ['9', '26', '-', '58', '68'],
            ['13', '17', '41', '59', '65'],
            ['4', '20', '42', '50', '73'],
        ],
    },
    {
        'filename': 'screenshots/board_2.png',
        'expected': [
            ['7', '16', '35', '46', '72'],
            ['11', '22', '34', '57', '68'],
            ['15', '30', '-', '49', '64'],
            ['9', '25', '36', '55', '65'],
            ['4', '17', '43', '54', '62'],
        ],
    },
    {
        'filename': 'screenshots/notha_board.png',
        'expected': [
            ['9', '23', '31', '59', '74'],
            ['15', '22', '37', '54', '64'],
            ['7', '27', '-', '50', '65'],
            ['4', '28', '36', '55', '70'],
            ['6', '30', '42', '51', '61'],
        ],
    },
    {
        'filename': 'screenshots/game_more_board_bad_name.png',
        'expected': [
            ['11', '20', '32', '52', '66'],
            ['15', '27', '38', '57', '74'],
            ['6', '16', '-', '58', '62'],
            ['3', '25', '40', '47', '72'],
            ['14', '30', '37', '53', '67'],
        ],
    },
]


@pytest.fixture(params=TEST_DATA, ids=lambda d: d['filename'])
def test_case(request):
    return request.param


def extract_board_from_image(filename):
    image = Image.open(filename).convert('L')
    number_pixel_coords, _ = get_bingo_number_coords(image)
    return to_5x5_matrix(list(number_pixel_coords.keys()))


def test_image_processing(test_case):
    actual_board = extract_board_from_image(test_case['filename'])
    expected_board = test_case['expected']

    for row in range(5):
        for col in range(5):
            assert actual_board[row][col] == expected_board[row][col], f"Mismatch at ({col}, {row})"
