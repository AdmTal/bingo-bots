import pytest
from PIL import Image
from bingo_king.image_utils import (
    get_current_called_number_alt,
    crop_image,
)

TEST_CASES = [
    ['screenshots/a_board_that_failed_to_parse.png', ''],
    ['screenshots/number_not_loaded_yet.png', '19'],
    ['screenshots/49_early_call.png', '49'],
    ['screenshots/runaway_20.png', '20'],
    ['screenshots/i_20.png', '29'],
    ['screenshots/13_yet_another_b11.png', '11'],
    ['screenshots/early_64.png', '64'],
    ['screenshots/early_8.png', '8'],
    ['screenshots/72-1.png', '72'],
    ['screenshots/72-2.png', '72'],
    ['screenshots/72-3.png', '72'],
    ['screenshots/72-3.png', '72'],
    ['screenshots/a_50_why.png', '50'],
    ['screenshots/46_1.png', '46'],
    ['screenshots/46_2.png', '46'],
    ['screenshots/46_3.png', '46'],
    ['screenshots/caea5d31_1.png', ''],
    ['screenshots/caea5d31_2.png', ''],
    ['screenshots/caea5d31_3.png', ''],
    ['screenshots/late_50.png', '50'],
    ['screenshots/caea5d31_6.png', '54'],
    ['screenshots/caea5d31_8.png', '22'],
    ['screenshots/caea5d31_9.png', '22'],
    ['screenshots/caea5d31_10.png', '29'],
    ['screenshots/caea5d31_11.png', '29'],
    ['screenshots/caea5d31_12.png', '29'],
    ['screenshots/caea5d31_13.png', '45'],
    ['screenshots/caea5d31_14.png', '45'],
    ['screenshots/caea5d31_15.png', '45'],
    ['screenshots/caea5d31_16.png', '58'],
    ['screenshots/bad_b13.png', '13'],
    ['screenshots/o74_too_early.png', '74'],
    ['screenshots/early3.png', '3'],
    ['screenshots/bad_38_1.png', '38'],
    ['screenshots/bad_38_2.png', '38'],
    ['screenshots/bad_38_3.png', '38'],
    ['screenshots/bad_31_1.png', '30'],
    ['screenshots/bad_31_2.png', '30'],
    ['screenshots/bad_31_3.png', '30'],
    ['screenshots/bad_31_4.png', '30'],
    ['screenshots/b3ontime.png', '3'],
    ['screenshots/bad_71_2.png', '71'],
    ['screenshots/bad_71_3.png', '71'],
    ['screenshots/bad_35_1.png', '35'],
    ['screenshots/bad_18_again.png', '18'],
    ['screenshots/caea5d31_19.png', '58'],
    ['screenshots/caea5d31_17.png', '58'],
    ['screenshots/caea5d31_18.png', '58'],
    ['screenshots/bad_35_2.png', '35'],
    ['screenshots/bad_35_3.png', '35'],
    ['screenshots/bad_35_4.png', '35'],
    ['screenshots/bad_43.png', '43'],
    ['screenshots/33_post_star.png', '33'],
    ['screenshots/g57.png', '57'],
    ['screenshots/bad_5_next_frame.png', '5'],
    ['screenshots/bad_44_1.png', '44'],
    ['screenshots/bad_44_2.png', '44'],
    ['screenshots/bad_34_1.png', '34'],
    ['screenshots/bad_34_2.png', '34'],
    ['screenshots/bad_34_3.png', '34'],
    ['screenshots/4dcd3956_11_2.png', '11'],
    ['screenshots/4dcd3956_11_3.png', '11'],
    ['screenshots/g56.png', '56'],
    ['screenshots/bad_59_1.png', '59'],
    ['screenshots/bad_59_2.png', '59'],
    ['screenshots/bad_59_3.png', '59'],
    ['screenshots/bad_59_4.png', '59'],
    ['screenshots/bad_b8_1.png', '8'],
    ['screenshots/bad_b8_2.png', '8'],
    ['screenshots/bad_b8_3.png', '8'],
    ['screenshots/bad_64_2.png', '64'],
    ['screenshots/bad_64_3.png', '64'],
    ['screenshots/bad_17_2.png', '17'],
    ['screenshots/bad_17_3.png', '17'],
    ['screenshots/b3_1.png', '3'],
    ['screenshots/b3_2.png', '3'],
    ['screenshots/bad_53_1.png', '53'],
    ['screenshots/bad_53_2.png', '53'],
    ['screenshots/bad_53_3.png', '53'],
    ['screenshots/bad_53_4.png', '53'],
    ['screenshots/94_14_too_far_right.png', '14'],
    ['screenshots/bad_b5.png', '5'],
    ['screenshots/bad_49_2.png', '49'],
    ['screenshots/bad_49_1.png', '49'],
    ['screenshots/bad_21.png', '21'],
    ['screenshots/caea5d31_7.png', '22'],
    ['screenshots/caea5d31_20.png', '19'],
    ['screenshots/bad_71_2.png', '71'],
    ['screenshots/bad_71_3.png', '71'],
    ['screenshots/abadb9.png', '9'],
    ['screenshots/bad_17_1.png', '17'],
    ['screenshots/bad_17_again.png', '17'],
    ['screenshots/bad_71_1.png', '71'],
    ['screenshots/bad_32.png', '32'],
    ['screenshots/4dcd3956_11_1.png', '11'],
    ['screenshots/b_11_again.png', '11'],
    ['screenshots/an_early_25.png', '25'],
    ['screenshots/n_34.png', '34'],
    ['screenshots/bad31-1.png', '31'],
    ['screenshots/bad31-2.png', '31'],
    ['screenshots/bad_64_1.png', '64'],
    ['screenshots/bad_b9.png', '9'],
    ['screenshots/bad_66.png', ''],
    ['screenshots/caea5d31_4.png', '54'],
    ['screenshots/bad_75.png', '75'],
]


@pytest.fixture(scope="module")
def bg_segment_image():
    return Image.open('../assets/new_bg_segment.png').convert('L')


@pytest.fixture(scope="module")
def post_star_bg_segment_image():
    return Image.open('../assets/post_star_bg_segment.png').convert('L')


@pytest.fixture(scope="module")
def health_bar_missing_proof_seg_image():
    return Image.open('../assets/health_bar_missing_proof.png').convert('L')


@pytest.mark.parametrize("filename, expected", TEST_CASES)
def test_get_current_called_number(
        filename,
        expected,
):
    image = Image.open(filename).convert('L')
    image = crop_image(image, 0, 0, image.width, image.height / 3, buffer=0)

    current_number = get_current_called_number_alt(image)

    if current_number != expected:
        current_number = get_current_called_number_alt(image, show=True)

    assert current_number == expected, f"Failed for {filename}. Expected {expected}, got {current_number}."
