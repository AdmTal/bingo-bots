import pytest
from PIL import Image
from image_utils import get_current_called_number, crop_image

TEST_CASES = [
    ['screenshots/b_15_should_be_blank.png', ''],
    ['screenshots/full_powerups.png', '23'],
    ['screenshots/the_2X_screenshot.png', '52'],
    ['screenshots/the_A_PW.png', '16'],
    ['screenshots/the_CLOCK_PW.png', '50'],
    ['screenshots/the_STAR_PW.png', '36'],
    ['screenshots/b_31.png', '31'],
    ['screenshots/11_1.png', ''],
    ['screenshots/11_2.png', '11'],
    ['screenshots/11_3.png', '11'],
    ['screenshots/11_4.png', '11'],
    ['screenshots/11_5.png', '11'],
    ['screenshots/11_6.png', ''],
    ['screenshots/11_7.png', '11'],
    ['screenshots/b9.png', ''],
    ['screenshots/5_1.png', ''],
    ['screenshots/5_2.png', '5'],
    ['screenshots/5_3.png', '5'],
    ['screenshots/5_4.png', '5'],
    ['screenshots/5_5.png', '5'],
    ['screenshots/11_bad.png', '1'],
    ['screenshots/n36.png', '36'],
    ['screenshots/n36_covered.png', ''],
    ['screenshots/3_1.png', '3'],
    ['screenshots/3_2.png', '3'],
    ['screenshots/3_3.png', '3'],
    ['screenshots/3_4.png', '3'],
    ['screenshots/48_1.png', ''],
    ['screenshots/48_2.png', '48'],
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
        bg_segment_image,
        post_star_bg_segment_image,
        health_bar_missing_proof_seg_image
):
    image = Image.open(filename).convert('L')
    image = crop_image(image, 0, 0, image.width, image.height / 5, buffer=0)

    current_number = get_current_called_number(image)

    assert current_number == expected, f"Failed for {filename}. Expected {expected}, got {current_number}."
