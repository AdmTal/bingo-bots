import numpy as np
from PIL import Image, ImageOps
import pytesseract
from concurrent.futures import ThreadPoolExecutor

GRID_SIZE = 5
X_START = 270
Y_START = 665
SIZE = 225


def crop_image(image, x, y, w, h, buffer):
    return image.crop((x + buffer, y + buffer, x + w - buffer, y + h - buffer))


def get_number(image):
    """Get number from image of a Bingo Ball"""
    return pytesseract.image_to_string(
        image,
        config=f'--psm 8 --oem 1 -c tessedit_char_whitelist=0123456789',
        lang='eng',
    ).strip()


def to_5x5_matrix(flat_list):
    """Convert a flat list of numbers to a Bingo Grid"""
    columns = [flat_list[i:i + 5] for i in range(0, len(flat_list), 5)]
    return [[columns[j][i] for j in range(5)] for i in range(5)]


def auto_crop_number_orig(image, threshold, left_padding=3, right_padding=4):
    """This works for board parsing so I'm keeping it"""
    grayscale = image.convert("L")
    thresholded = grayscale.point(lambda p: 255 if p < threshold else 0)
    bbox = thresholded.getbbox()

    if bbox:
        new_left = max(bbox[0] - left_padding, 0)
        new_right = min(bbox[2] + right_padding, image.width + 1)
        bbox = (new_left, 0, new_right, image.height + 1)
        return image.crop(bbox)
    else:
        return image


def auto_crop_number(image, threshold, left_padding=3, right_padding=4, top_padding=0, bottom_padding=0):
    # Convert the image to grayscale
    grayscale = image.convert("L")

    # Threshold the grayscale image
    thresholded = grayscale.point(lambda p: 255 if p < threshold else 0)
    bbox = thresholded.getbbox()

    # Crop the image
    if bbox:
        cropped = image.crop(bbox)
    else:
        return image

    # Create a new white image large enough to add padding on all sides
    new_width = cropped.width + left_padding + right_padding
    new_height = cropped.height + top_padding + bottom_padding
    new_image = Image.new("L", (new_width, new_height), "white")

    # Center the cropped image on the new white image
    paste_x = left_padding
    paste_y = top_padding
    new_image.paste(cropped, (paste_x, paste_y))

    # Return new image
    return new_image


def process_cell(image, i, j):
    if i == 2 and j == 2:
        return ('-', None, None, None, None)
    ROW = X_START + (i * SIZE)
    COL = Y_START + (j * SIZE)
    buffer = 48 if j == 0 else 55
    cropped = crop_image(
        image,
        ROW,
        COL,
        SIZE,
        SIZE,
        buffer=buffer,
    )

    cropped = auto_crop_number_orig(cropped, threshold=200)

    number = get_number(cropped)

    # B9 is not working
    if not number and i == 0:
        number = '9'

    return (
        number,
        int(ROW + (SIZE / 2)) / 2,
        int(COL + (SIZE / 2)) / 2,
        i,
        j
    )


def get_bingo_number_coords(image):
    number_pixel_coords = {}
    number_coords = {}
    with ThreadPoolExecutor() as executor:
        tasks = [(image, i, j) for i in range(GRID_SIZE) for j in range(GRID_SIZE)]
        results = list(executor.map(lambda args: process_cell(*args), tasks))
    for number, x, y, i, j in results:
        number_pixel_coords[number] = (x, y)
        number_coords[number] = (i, j)

    return number_pixel_coords, number_coords


def images_match(img1, img2, threshold=10):
    """Returns True if the images match enough"""
    h1 = img1.histogram()
    h2 = img2.histogram()
    return sum(abs(i - j) for i, j in zip(h1, h2)) < threshold


def is_game_over(image, game_over):
    """Returns True if the image matches the Game Over state"""
    image_game_over = crop_image(image, 580, 300, 550, 250, 55)
    return fuzz_image_compare_color(image_game_over, game_over)


def board_is_ready(image, game_start):
    """Returns True if the image matches the Game Start state"""
    image_game_start = crop_image(image, 200, 500, 1300, 250, 55)
    return images_match(image_game_start, game_start, threshold=315000)


def extend_image(img, left=10, top=10, right=10, bottom=0, fillcolor=150):
    """Add a padded colored edge to the given image, helps OCR for some reason"""
    return ImageOps.expand(img, border=(left, top, right, bottom), fill=fillcolor)


def convert_to_bw(image, threshold=128):
    return image.point(lambda p: 255 if p > threshold else 0, mode='1')


def get_current_called_number(image, bg_segment, star_was_used, post_star_bg_segment, health_bar_missing_proof_seg):
    """Return the number on the current Bingo Ball that is being called"""
    health_bar_missing = crop_image(image, 0, 325, 315, 200, 0)
    if images_match(health_bar_missing_proof_seg, health_bar_missing, threshold=10):
        return ''

    background_segment = crop_image(image, 310, 450, 160, 200, 55)
    if images_match(bg_segment, background_segment):
        return ''

    # Bingo King has a bug, the entire board shifts after a "STAR" power up is used
    if star_was_used:
        psbgs = crop_image(image, 310, 500, 160, 100, 0)
        if images_match(post_star_bg_segment, psbgs):
            return ''
        cropped = crop_image(image, 300, 300, 175, 165, 0)
        cropped = auto_crop_number(
            cropped, threshold=28, left_padding=15, right_padding=15, top_padding=30, bottom_padding=15)
        cropped = convert_to_bw(cropped, threshold=30).rotate(-4)
        cropped = extend_image(cropped, left=5, top=5, right=5, bottom=5, fillcolor=0)
    else:
        cropped = crop_image(image, 320, 320, 150, 155, 0)
        cropped = auto_crop_number(
            cropped, threshold=28, left_padding=50, right_padding=50, top_padding=25, bottom_padding=10)
        cropped = extend_image(cropped, left=10, top=30, right=10, bottom=25, fillcolor=0)

    # cropped.show()
    return get_number(cropped)


def color_difference(color1, color2):
    # Handle the case where colors are grayscale (floats)
    if isinstance(color1, (float, int)):
        color1 = (color1, color1, color1, 255)
    elif len(color1) == 3:
        color1 = (*color1, 255)

    if isinstance(color2, (float, int)):
        color2 = (color2, color2, color2, 255)
    elif len(color2) == 3:
        color2 = (*color2, 255)

    return np.linalg.norm(np.array(color1) - np.array(color2))


def average_color(image):
    """Compute the average color of an image."""
    np_image = np.array(image)
    avg_color = np_image.mean(axis=(0, 1))
    return avg_color


def fuzz_image_compare_color(image1, image2, threshold=40):
    # Compute average colors
    avg_color1 = average_color(image1)
    avg_color2 = average_color(image2)

    # Determine if the colors are close enough
    return color_difference(avg_color1, avg_color2) < threshold
