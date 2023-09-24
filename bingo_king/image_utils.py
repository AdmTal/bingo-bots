import numpy as np
from PIL import Image, ImageOps
import pytesseract
from concurrent.futures import ThreadPoolExecutor
import scipy
import cv2

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
    res = sum(abs(i - j) for i, j in zip(h1, h2))
    return res < threshold


def is_game_over(image, game_over):
    """Returns True if the image matches the Game Over state"""
    image_game_over = crop_image(image, 580, 300, 550, 250, 55)
    return fuzz_image_compare_color(image_game_over, game_over)


def board_is_ready(image, game_start):
    """Returns True if the image matches the Game Start state"""
    image_game_start = crop_image(image, 200, 500, 1300, 250, 55)
    return images_match(image_game_start, game_start, threshold=339650)


def extend_image(img, left=10, top=10, right=10, bottom=0, fillcolor=150):
    """Add a padded colored edge to the given image, helps OCR for some reason"""
    return ImageOps.expand(img, border=(left, top, right, bottom), fill=fillcolor)


def convert_to_bw(image, threshold=128):
    return image.point(lambda p: 255 if p > threshold else 0, mode='1')


def enhance_remaining_structure(data, enhance_thickness=5):
    structure = np.ones((enhance_thickness, enhance_thickness))
    eroded_data = scipy.ndimage.binary_erosion(data, structure=structure)
    enhanced_image_data = eroded_data * 255
    return Image.fromarray(enhanced_image_data.astype(np.uint8))


def is_middle_third_mostly_black(image, threshold=60):
    # Convert image to grayscale
    grayscale = image.convert("L")

    # Convert to numpy array for easy computation
    data = np.array(grayscale)

    # Compute indices for the middle third of the first row
    width = data.shape[1]
    start_idx = width // 3
    end_idx = 2 * width // 3

    # Get the middle third of the first row
    middle_third = data[0, start_idx:end_idx]

    # Count the number of black pixels (below threshold)
    black_pixel_count = np.sum(middle_third < threshold)

    # Check if the majority of the pixels are black
    return black_pixel_count > (middle_third.size / 3)


def crop_to_white_circle(image):
    # Convert the PIL image to OpenCV format
    open_cv_image = np.array(image)

    # Ensure the image is in grayscale
    if len(open_cv_image.shape) == 3:  # Check if the image has channels
        gray = cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2GRAY)
    else:
        gray = open_cv_image

    # Threshold to isolate the white region
    _, thresh = cv2.threshold(gray, 245, 255, cv2.THRESH_BINARY)

    # Apply Hough circle transform to detect the circle
    circles = cv2.HoughCircles(thresh, cv2.HOUGH_GRADIENT,
                               dp=1.2, minDist=30, param1=50, param2=30, minRadius=85, maxRadius=100)

    if circles is not None:
        # Convert the (x, y) coordinates and radius of the circle to integers
        circles = np.round(circles[0, :]).astype("int")

        for (x, y, r) in circles:
            # Crop to the detected circle
            cropped_image = open_cv_image[y - r:y + r, x - r:x + r]

            # Convert the OpenCV image back to PIL format and return
            return Image.fromarray(cropped_image)

    # If no circle is detected, return the original image
    return image


def cut_sides(img, padding=10):
    width, height = img.size
    left = padding
    top = padding
    right = width - padding
    bottom = height - padding

    return img.crop((left, top, right, bottom))


def get_current_called_number_alt(image, show=False):
    cropped = crop_image(image, 200, 150, 350, 400, 0)
    cropped = crop_to_white_circle(cropped).rotate(-3)
    cropped = convert_to_bw(cropped, threshold=29)
    cropped = enhance_remaining_structure(cropped, enhance_thickness=4)
    cropped = cut_sides(cropped, padding=20)

    if is_middle_third_mostly_black(cropped):
        return ''

    cropped = extend_image(cropped, left=20, top=20, right=25, bottom=20, fillcolor=240)
    cropped = extend_image(cropped, left=10, top=10, right=20, bottom=20, fillcolor=99)

    if show:
        cropped.show()

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
