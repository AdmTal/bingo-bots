from PIL import Image
from bingo_king.main import get_powerup, PW_CROWN
from bingo_king.image_utils import crop_image
import concurrent.futures
from bingo_king.main import P1_X, P1_Y, P1_H, P1_W, ROOT_DIR


def test_it():
    filename = f'{ROOT_DIR}/tests/screenshots/4dcd3956_11_3.png'

    image = Image.open(filename)
    image.load()

    coords = [
        (image, P1_X, P1_Y, P1_W, P1_H, 48),
        (image, P1_X + 187, P1_Y, P1_W, P1_H, 48),
        (image, P1_X + (187 * 2), P1_Y, P1_W, P1_H, 48)
    ]

    with concurrent.futures.ThreadPoolExecutor() as executor:
        p1, p2, p3 = list(executor.map(lambda args: get_powerup(crop_image(*args)), coords))

    assert p1 == PW_CROWN
