import pytest
from PIL import Image
from bingo_king.image_utils import get_bingo_number_coords, to_5x5_matrix

TEST_DATA = [
    {
        'filename': 'screenshots/3_more_numbers_called.png',
        'expected': [
            ['8', '25', '34', '58', '61'],
            ['15', '26', '41', '57', '71'],
            ['9', '24', '-', '50', '73'],
            ['2', '18', '43', '55', '65'],
            ['5', '28', '36', '48', '70'],
        ],
    },
    {
        'filename': 'screenshots/8_first_call.png',
        'expected': [
            ['14', '22', '39', '52', '68'],
            ['6', '29', '37', '55', '74'],
            ['12', '17', '-', '50', '75'],
            ['10', '23', '32', '53', '65'],
            ['7', '26', '34', '48', '61'],
        ],
    },
    {
        'filename': 'screenshots/b1_board.png',
        'expected': [
            ['11', '24', '42', '54', '71'],
            ['5', '19', '31', '51', '61'],
            ['6', '21', '-', '59', '64'],
            ['14', '29', '44', '58', '73'],
            ['7', '23', '41', '52', '65'],
        ],
    },
    {
        'filename': 'screenshots/another_b1_board.png',
        'expected': [
            ['11', '27', '45', '58', '63'],
            ['7', '21', '31', '46', '70'],
            ['1', '18', '-', '51', '61'],
            ['10', '16', '34', '54', '75'],
            ['4', '22', '41', '56', '71'],
        ],
    },
    {
        'filename': 'screenshots/bad_b_col.png',
        'expected': [
            ['8', '25', '41', '57', '75'],
            ['9', '17', '37', '46', '74'],
            ['12', '20', '-', '55', '65'],
            ['4', '23', '33', '49', '67'],
            ['14', '22', '40', '56', '72'],
        ],
    },
    {
        'filename': 'screenshots/another_b_11.png',
        'expected': [
            ['12', '16', '41', '58', '66'],
            ['14', '20', '38', '53', '70'],
            ['5', '24', '-', '50', '68'],
            ['11', '23', '33', '49', '72'],
            ['6', '29', '42', '48', '63'],
        ],
    },
    {
        'filename': 'screenshots/b_9_not_working.png',
        'expected': [
            ['8', '19', '37', '53', '65'],
            ['9', '29', '41', '58', '70'],
            ['3', '26', '-', '49', '66'],
            ['2', '17', '38', '57', '61'],
            ['5', '18', '45', '48', '72'],
        ],
    },
    {
        'filename': 'screenshots/initial_72.png',
        'expected': [
            ['13', '19', '33', '48', '72'],
            ['14', '28', '32', '59', '71'],
            ['15', '30', '-', '55', '66'],
            ['3', '21', '45', '51', '64'],
            ['1', '22', '42', '52', '67'],
        ],
    },
    {
        'filename': 'screenshots/a_board_that_failed_to_parse.png',
        'expected': [
            ['13', '17', '31', '49', '66'],
            ['4', '21', '42', '48', '68'],
            ['15', '25', '-', '60', '65'],
            ['8', '24', '43', '47', '67'],
            ['2', '20', '41', '55', '74'],
        ],
    },
    {
        'filename': 'screenshots/crown_logic_1.png',
        'expected': [
            ['5', '25', '43', '59', '67'],
            ['6', '28', '45', '48', '63'],
            ['12', '29', '-', '54', '61'],
            ['8', '21', '40', '51', '69'],
            ['15', '27', '31', '47', '70'],
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
            # TODO - add debug logic for ROW,COL to see what is going on - it's all messed up now
            assert actual_board[row][col] == expected_board[row][col], f"Mismatch at ({col}, {row})"
