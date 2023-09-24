import pytest
from PIL import Image
from image_utils import get_current_called_number, crop_image

TEST_CASES = [
    [False, 'screenshots/a_board_that_failed_to_parse.png', ''],
    [False, 'screenshots/b_11_again.png', '11'],
    [False, 'screenshots/number_not_loaded_yet.png', ''],
    [False, 'screenshots/49_early_call.png', '49'],
    [False, 'screenshots/runaway_20.png', ''],
    [False, 'screenshots/i_20.png', '29'],
    [False, 'screenshots/13_yet_another_b11.png', '11'],
    [False, 'screenshots/early_64.png', '64'],
    [False, 'screenshots/early_8.png', '8'],
    [False, 'screenshots/72-1.png', '72'],
    [False, 'screenshots/72-2.png', '72'],
    [False, 'screenshots/72-3.png', '72'],
    [False, 'screenshots/72-3.png', '72'],
    [False, 'screenshots/a_50_why.png', '50'],
    [False, 'screenshots/46_1.png', '46'],
    [False, 'screenshots/46_2.png', '46'],
    [False, 'screenshots/46_3.png', '46'],
    [False, 'screenshots/caea5d31_1.png', ''],
    [False, 'screenshots/caea5d31_2.png', ''],
    [False, 'screenshots/caea5d31_3.png', ''],
    [False, 'screenshots/caea5d31_19.png', '58'],
    [False, 'screenshots/late_50.png', '50'],
    [False, 'screenshots/caea5d31_6.png', '54'],
    [False, 'screenshots/caea5d31_7.png', '22'],
    [False, 'screenshots/caea5d31_8.png', '22'],
    [False, 'screenshots/caea5d31_9.png', '22'],
    [False, 'screenshots/caea5d31_10.png', '29'],
    [False, 'screenshots/caea5d31_11.png', '29'],
    [False, 'screenshots/caea5d31_12.png', '29'],
    [False, 'screenshots/caea5d31_13.png', '45'],
    [False, 'screenshots/caea5d31_14.png', '45'],
    [False, 'screenshots/caea5d31_15.png', '45'],
    [False, 'screenshots/caea5d31_16.png', '58'],
    [False, 'screenshots/caea5d31_17.png', '58'],
    [False, 'screenshots/caea5d31_18.png', '58'],
    [False, 'screenshots/caea5d31_20.png', '19'],
    [False, 'screenshots/bad_b13.png', '13'],
    [False, 'screenshots/o74_too_early.png', '74'],
    [False, 'screenshots/early3.png', ''],
    [False, 'screenshots/caea5d31_4.png', ''],
    [False, 'screenshots/an_early_25.png', ''],
    [False, 'screenshots/bad_38_1.png', '38'],
    [False, 'screenshots/bad_38_2.png', '38'],
    [False, 'screenshots/bad_38_3.png', '38'],
    [False, 'screenshots/bad_31_1.png', ''],
    [False, 'screenshots/bad_31_2.png', '30'],
    [False, 'screenshots/bad_31_3.png', '30'],
    [False, 'screenshots/bad_31_4.png', '30'],
    [False, 'screenshots/b3ontime.png', '3'],
    [False, 'screenshots/n_34.png', '34'],
    [False, 'screenshots/bad_71_1.png', '71'],
    [False, 'screenshots/bad_71_2.png', '71'],
    [False, 'screenshots/bad_71_3.png', '71'],
    [False, 'screenshots/bad_35_1.png', '35'],
    [False, 'screenshots/bad_35_2.png', '35'],
    [False, 'screenshots/bad_35_3.png', '35'],
    [False, 'screenshots/bad_35_4.png', '35'],
    [True, 'screenshots/bad_43.png', '43'],
    [True, 'screenshots/33_post_star.png', '33'],
    [True, 'screenshots/g57.png', '57'],
    [True, 'screenshots/bad_b5.png', ''],
    [True, 'screenshots/bad_5_next_frame.png', '5'],
    [True, 'screenshots/94_14_too_far_right.png', ''],
    [True, 'screenshots/bad_44_1.png', '44'],
    [True, 'screenshots/bad_44_2.png', '44'],
    [True, 'screenshots/bad31-1.png', '31'],
    [True, 'screenshots/bad31-2.png', '31'],
    [True, 'screenshots/bad_49_2.png', '49'],
    [True, 'screenshots/bad_34_1.png', '34'],
    [True, 'screenshots/bad_34_2.png', '34'],
    [True, 'screenshots/bad_34_3.png', '34'],
    [True, 'screenshots/4dcd3956_11_1.png', '11'],
    [True, 'screenshots/4dcd3956_11_2.png', '11'],
    [True, 'screenshots/4dcd3956_11_3.png', '11'],
    [True, 'screenshots/g56.png', '56'],
    [True, 'screenshots/bad_21.png', '21'],
    [True, 'screenshots/bad_32.png', '32'],
    [True, 'screenshots/bad_59_1.png', '59'],
    [True, 'screenshots/bad_59_2.png', '59'],
    [True, 'screenshots/bad_59_3.png', '59'],
    [True, 'screenshots/bad_59_4.png', '59'],
    [True, 'screenshots/bad_b8_1.png', '8'],
    [True, 'screenshots/bad_b8_2.png', '8'],
    [True, 'screenshots/bad_b8_3.png', '8'],
    [True, 'screenshots/bad_64_1.png', '64'],
    [True, 'screenshots/bad_64_2.png', '64'],
    [True, 'screenshots/bad_64_3.png', '64'],
    [True, 'screenshots/bad_17_1.png', '17'],
    [True, 'screenshots/abadb9.png', '9'],
    [True, 'screenshots/bad_49_1.png', '49'],
    [True, 'screenshots/bad_17_2.png', '17'],
    [True, 'screenshots/bad_17_3.png', '17'],
    [True, 'screenshots/b3_1.png', '3'],
    [True, 'screenshots/b3_2.png', '3'],
    [True, 'screenshots/bad_53_1.png', '53'],
    [True, 'screenshots/bad_53_2.png', '53'],
    [True, 'screenshots/bad_53_3.png', '53'],
    [True, 'screenshots/bad_53_4.png', '53'],
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


@pytest.mark.parametrize("star_was_used, filename, expected", TEST_CASES)
def test_get_current_called_number(
        star_was_used,
        filename,
        expected,
        bg_segment_image,
        post_star_bg_segment_image,
        health_bar_missing_proof_seg_image
):
    image = Image.open(filename).convert('L')
    image = crop_image(image, 0, 0, image.width, image.height / 3, buffer=0)

    current_number = get_current_called_number(
        image,
        bg_segment_image,
        star_was_used,
        post_star_bg_segment_image,
        health_bar_missing_proof_seg_image
    )

    assert current_number == expected, f"Failed for {filename}. Expected {expected}, got {current_number}."
