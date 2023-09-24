from concurrent.futures import ThreadPoolExecutor

import numpy as np
from PIL import Image, ImageOps
import pytesseract

GRID_SIZE = 5
X_START = 230
Y_START = 615
SIZE = 240


def crop_image(image, x, y, w, h, buffer=0):
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
    cropped = crop_image(image, ROW, COL, SIZE, SIZE, buffer=25)

    cropped = convert_to_bw(cropped, threshold=100)
    cropped = auto_crop_number(cropped,
                               threshold=40,
                               left_padding=25, right_padding=25, top_padding=25, bottom_padding=25)
    cropped = extend_image(
        cropped,
        left=8, top=8, right=8, bottom=8,
        fillcolor=0
    )

    return (
        get_number(cropped),
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
    h1 = img1.histogram()
    h2 = img2.histogram()
    return sum(abs(i - j) for i, j in zip(h1, h2)) < threshold


def is_game_over(image, game_over):
    image_game_over = crop_image(image, 540, 450, 625, 100, 0)
    return fuzz_image_compare_color(image_game_over, game_over)


def board_is_ready(image, game_start):
    image_game_start = crop_image(image, 200, 500, 1300, 100)
    return images_match(image_game_start, game_start, threshold=315000)


def extend_image(img, left=10, top=10, right=10, bottom=0, fillcolor=150):
    return ImageOps.expand(img, border=(left, top, right, bottom), fill=fillcolor)


def convert_to_bw(image, threshold=128):
    return image.point(lambda p: 255 if p > threshold else 0, mode='1')


def get_current_called_number(image):
    health_bar = image.getpixel((1380, 440))
    if health_bar < 150:
        return ''
    right_edge_of_ball = image.getpixel((1280, 300))
    if right_edge_of_ball < 200:
        return ''
    cropped = crop_image(image, 1200, 260, 150, 160, 15)
    cropped = convert_to_bw(cropped, threshold=100)
    cropped = auto_crop_number(cropped,
                               threshold=40,
                               left_padding=25, right_padding=25, top_padding=25, bottom_padding=25)
    cropped = extend_image(
        cropped,
        left=8, top=8, right=8, bottom=8,
        fillcolor=0
    )
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


def fuzz_image_compare_color(image1, image2, threshold=40):
    # Compute average colors
    avg_color1 = average_color(image1)
    avg_color2 = average_color(image2)

    # Determine if the colors are close enough
    return color_difference(avg_color1, avg_color2) < threshold


def average_color(image):
    """Compute the average color of an image."""
    np_image = np.array(image)
    avg_color = np_image.mean(axis=(0, 1))
    return avg_color
