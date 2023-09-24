import base64
import concurrent.futures
import datetime
import json
import os
import sys
import threading
import time
import uuid

import cv2
import numpy as np
import requests
from PIL import Image
from io import BytesIO

from image_utils import (
    auto_crop_number,
    board_is_ready,
    convert_to_bw,
    crop_image,
    fuzz_image_compare_color,
    get_bingo_number_coords,
    get_current_called_number,
    get_number,
    is_game_over,
    to_5x5_matrix,
)

# Set this to True to save gameplay videos
_SAVE_VIDEO = True

BINGO_CASH_BUNDLE_ID = 'com.papaya.bingocash'
WDA_PORT = 8100
MJPEG_PORT = 9100
ROOT = sys.argv[1]
URL = f"{ROOT}:{WDA_PORT}"
MJPEG_URL = f"{ROOT}:{MJPEG_PORT}"

# Power Up Constants
P1_X = 670
P1_Y = 1830
P1_W = P1_H = 180
P2_X = 820
P2_Y = 1830
P2_W = P2_H = 180

PW_STAR_IMG = Image.open('assets/powerups/star.png')
PW_2X_IMG = Image.open('assets/powerups/2x.png')
PW_TIME_IMG = Image.open('assets/powerups/extra-time.png')
PW_PICKA_IMG = Image.open('assets/powerups/picka.png')

PW_STAR_IMG.load()
PW_2X_IMG.load()
PW_TIME_IMG.load()
PW_PICKA_IMG.load()

PW_STAR = 'STAR'
PW_2X = '2X'
PW_TIME = 'TIME'
PW_PICKA = 'PICKA'

GAME_OVER = Image.open('assets/gameover.png')
GAME_OVER.load()

game_start = Image.open('assets/game_start.png')
game_start.load()

if not ROOT:
    print('You gotta put a URL!')
    exit()

print(f'URL = {URL}')

BOUNDARY = b"--BoundaryString"
FRAME_RATE = 10  # Assuming 20 FPS
BUFFER_SIZE = 10 * FRAME_RATE  # 10 seconds of frames

log_filename = None


class VideoRecorder:

    def __init__(self):
        self.recording = False
        self.video_out = None
        self.thread = None

    def _capture_video(self):
        response = requests.get(MJPEG_URL, stream=True)
        if response.status_code != 200:
            print(f"Failed to connect with error code: {response.status_code}")
            return

        buffer = b""
        current_game_frames = []

        for chunk in response.iter_content(chunk_size=1024):
            if not self.recording:
                break

            buffer += chunk
            if buffer.count(BOUNDARY) >= 2:
                parts = buffer.split(BOUNDARY)
                jpeg_data = parts[1].split(b'\r\n\r\n', 1)[-1]

                image_np = np.frombuffer(jpeg_data, dtype=np.uint8)
                frame = cv2.imdecode(image_np, 1)

                if frame is not None:
                    current_game_frames.append(frame)

                buffer = parts[-1]

        # Write buffered frames and the current game frames to the video file after recording stops
        for frame in current_game_frames:
            self.video_out.write(frame)

        self.video_out.release()
        print('Video released')

    def start_recording(self, video_file_name):
        self.recording = True
        self.video_out = cv2.VideoWriter(
            f'{video_file_name}',
            cv2.VideoWriter_fourcc(*'mp4v'),
            FRAME_RATE,
            (1668, 2224)
        )  # Change resolution if needed
        self.thread = threading.Thread(target=self._capture_video)
        self.thread.start()

    def stop_recording(self):
        self.recording = False
        self.thread.join()  # Wait for the recording thread to finish


log_filename = None


def print_log(message):
    global log_filename
    message = str(message)
    print(message)
    if log_filename is not None:
        os.makedirs(os.path.dirname(log_filename), exist_ok=True)
        with open(log_filename, 'a') as log_file:
            log_file.write(message + '\n')


def open_app_on_ipad(url, bundle_id, mjpeg_port):
    session_url = f"{url}/session"
    headers = {'Content-Type': 'application/json'}
    payload = {
        "capabilities": {
            "alwaysMatch": {
                "bundleId": bundle_id,
            }
        }
    }
    if _SAVE_VIDEO:
        payload['capabilities']['alwaysMatch']['mjpegServerPort'] = mjpeg_port

    response = requests.post(session_url, headers=headers, data=json.dumps(payload))
    return response.json()


def get_screenshot_as_png(url, label=None):
    response = requests.get(f"{url}/screenshot")
    if label:
        print_log(f'📸 {label}')
    return base64.b64decode(response.json()['value'])


def tap_screen(url, x, y, label):
    print_log(f'TAP {label} ({x}, {y})')
    session_url = f"{url}/session"
    action_url = f"{url}/session/{requests.get(session_url).json()['sessionId']}/wda/touch/perform"
    action = {
        "actions": [{
            "action": "tap",
            "options": {
                "x": x,
                "y": y
            }
        }]
    }

    response = requests.post(action_url, data=json.dumps(action))
    return response.json()


def save_to_file(png_data, filename):
    with open(filename, 'wb') as file:
        file.write(png_data)


def tap_power_1(label):
    x = P1_X / 2
    y = P1_Y / 2
    W = P1_W / 4
    tap_screen(URL, x + W, y + W, f'P1 {label}')


def tap_power_2(label):
    x = P2_X / 2
    y = P2_Y / 2
    W = P2_W / 4
    tap_screen(URL, x + W, y + W, f'P2 {label}')


def tap_bingo():
    BINGO_X = 1220 / 2
    BINGO_Y = 1930 / 2
    tap_screen(URL, BINGO_X, BINGO_Y, 'BINGO')


def get_powerup(image):
    if fuzz_image_compare_color(image, PW_STAR_IMG):
        return PW_STAR
    if fuzz_image_compare_color(image, PW_2X_IMG):
        return PW_2X
    if fuzz_image_compare_color(image, PW_TIME_IMG):
        return PW_TIME
    if fuzz_image_compare_color(image, PW_PICKA_IMG):
        return PW_PICKA
    return None


open_app_on_ipad(URL, BINGO_CASH_BUNDLE_ID, MJPEG_PORT)


def check_bingo(board):
    n = len(board)

    def is_valid_bingo(line):
        return all(x > 0 for x in line) and any(x == 1 for x in line)

    # Check rows and columns
    for i in range(n):
        if is_valid_bingo(board[i]) or is_valid_bingo([row[i] for row in board]):
            return True

    # Check main diagonals
    diag1 = [board[i][i] for i in range(n)]
    diag2 = [board[i][n - 1 - i] for i in range(n)]
    if is_valid_bingo(diag1) or is_valid_bingo(diag2):
        return True

    # Check four corners
    corners = [board[0][0], board[0][n - 1], board[n - 1][0], board[n - 1][n - 1]]
    if is_valid_bingo(corners):
        return True

    return False


def potential_impact(spot, board):
    n = len(board)

    # Check how many in-progress bingos the spot is part of
    in_progress_count = sum(1 for line in BINGO_LINES if spot in line and sum(board[i][j] for i, j in line) == n - 1)

    # If the spot is part of an in-progress bingo
    if in_progress_count > 0:
        return in_progress_count + 0.5  # 0.5 is just to give it a slight edge over other criteria

    # Check how far along the spot is in its line
    progress = max(sum(board[i][j] for i, j in line) if spot in line else 0 for line in BINGO_LINES)

    # Check how many lines the spot is part of
    overlap_count = sum(1 for line in BINGO_LINES if spot in line)

    return progress + overlap_count * 0.01  # overlap_count is given a small weight (0.01) so it acts as a tiebreaker


def most_needed_spots(board):
    n = len(board)
    undaubed_spots = [(i, j) for i in range(n) for j in range(n) if board[i][j] == 0]

    # Sort undaubed spots based on their potential impact
    # Corners will be prioritized in case of ties.
    sorted_spots = sorted(undaubed_spots, key=lambda k: -potential_impact(k, board))

    return sorted_spots


def reverse_lookup(number_coords):
    reverse_dict = {}

    for number, (i, j) in number_coords.items():
        if i not in reverse_dict:
            reverse_dict[i] = {}
        reverse_dict[i][j] = number

    return reverse_dict


def tap_2x(has_2x):
    if has_2x == 'p1':
        tap_power_1(PW_2X)
    elif has_2x == 'p2':
        tap_power_2(PW_2X)


def _translate_to_clickable_coord(x):
    return x / 2 + (240 / 2)


def fetch_picka_picks_data(x, y, w, h, image):
    cropped = crop_image(image, x, y, w, h)
    cropped = convert_to_bw(cropped, threshold=60)
    cropped = auto_crop_number(
        cropped,
        left_padding=30,
        right_padding=30,
        top_padding=15,
        bottom_padding=15,
        threshold=100,
    )
    return [get_number(cropped), _translate_to_clickable_coord(x), _translate_to_clickable_coord(y)]


def get_numbers_from_picka_4_pick(image):
    coords = [
        (445, 860, 210, 210),
        (445 + 585, 860, 210, 210),
        (445, 860 + 530, 210, 210),
        (445 + 585, 860 + 530, 210, 210),
    ]

    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(lambda args: fetch_picka_picks_data(*args, image=image), coords))

    return results


def get_numbers_from_picka_3_pick(image):
    raise Exception('Pick 3 not implemented -- Did not happen to me, so I\'m missing a screenshot for it')
    coords = [
        (710, 770, 240, 240, 20),
        (330, 1320, 240, 240, 20),
        (1050, 1320, 240, 240, 20),
    ]

    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(lambda args: fetch_picka_picks_data(*args, image=image), coords))

    return results


def get_numbers_from_picka_2_pick(image):
    coords = [
        (445, 860, 210, 210),
        (445 + 585, 860, 210, 210),
    ]

    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(lambda args: fetch_picka_picks_data(*args, image=image), coords))

    return results


def get_numbers_from_picka_1_pick(image):
    raise Exception('Pick 1 not implemented -- Did not happen to me, so I\'m missing a screenshot for it')
    first = crop_image(image, 710, 1150, 240, 240, buffer=20)
    return [[get_number(first), _translate_to_clickable_coord(710), _translate_to_clickable_coord(1150)]]


def will_cause_bingo(selections, board):
    # Create a copy of the board to not modify the original board
    daubed_board = [row.copy() for row in board]

    # Daub the given spot
    for mrow, mcol in selections:
        daubed_board[mrow][mcol] = 1

    # Use the existing function to check for BINGO
    return check_bingo(daubed_board)


# Potential bingo lines
# Define the different BINGO patterns
DIAGONALS = [
    [(i, i) for i in range(5)],
    [(i, 4 - i) for i in range(5)]
]
ROWS = [
    [(i, j) for j in range(5)]
    for i in range(5)
]
COLUMNS = [
    [(j, i) for j in range(5)]
    for i in range(5)
]
CORNERS = [[(0, 0), (0, 4), (4, 0), (4, 4)]]

BINGO_LINES = DIAGONALS + CORNERS + ROWS + COLUMNS


def spots_needed_for_bingo(line, board):
    """Return the undaubed spots in the given line."""
    undaubed_spots = [(i, j) for i, j in line if board[i][j] == 0]

    n = len(board)
    # Sort undaubed spots based on their potential impact
    # Corners will be prioritized in case of ties.
    sorted_spots = sorted(undaubed_spots, key=lambda k: -potential_impact(k, board))

    return sorted_spots


def perform_star_pw(p1, p2, number_lookup, DAUB_TRACKER, has_2x):
    # Map of the powerups to their respective functions
    powerup_functions = {
        1: tap_power_1,
        2: tap_power_2,
    }

    # Initialize list of powerups
    powerups = [p1, p2]

    # Count number of stars available
    tapped_spots = []
    stars_available = sum([p == PW_STAR for p in powerups])
    if not stars_available:
        return tapped_spots, has_2x

    most_needed = most_needed_spots(DAUB_TRACKER)

    while stars_available:
        # Use the stars
        for (mrow, mcol) in most_needed:
            # Get the index of the next available star powerup
            next_star_idx = next((idx for idx, is_star in enumerate(powerups) if is_star == PW_STAR), None)

            if next_star_idx is not None:
                # Use the star powerup function
                powerup_functions[next_star_idx + 1](PW_STAR)
                time.sleep(.3)
                print('SLEPT .3')

                # Mark the star as used by setting it to a placeholder (e.g. None)
                powerups[next_star_idx] = None

                # Log and tap the screen
                num = number_lookup[mcol][mrow]
                print_log(f'STAR {num} -- ({mcol}, {mrow})')
                x, y = game_board[num]
                tapped_spots.append(num)
                if has_2x:
                    tap_2x(has_2x)
                    has_2x = False
                tap_screen(URL, x, y, num)
                time.sleep(.3)
                print('SLEPT .3')

                # Decrease the count of stars available
                stars_available -= 1

    return tapped_spots, has_2x


def check_powerups(image):
    coords = [
        (image, P1_X, P1_Y, P1_W, P1_H, 48),
        (image, P2_X, P2_Y, P2_W, P2_H, 48),
    ]

    with concurrent.futures.ThreadPoolExecutor() as executor:
        p1, p2 = list(executor.map(lambda args: get_powerup(crop_image(*args)), coords))

    return p1, p2


def perform_picka_pw(counter, has_picka, most_needed_numbers):
    if has_picka == 'p1':
        tap_power_1(PW_PICKA)
    elif has_picka == 'p2':
        tap_power_2(PW_PICKA)

    # Wait for bubbles to finish loading
    time.sleep(.5)
    print_log('SLEPT FOR .5')

    png_data = get_screenshot_as_png(URL, 'PICKA PW Bubbles')
    threading.Thread(target=save_to_file, args=(png_data, f"{screenshots_dir}/{counter}-picka-select.png")).start()
    image = Image.open(BytesIO(png_data))
    image.load()
    image_bw = image.convert('L')
    image_bw.load()
    num_left = len(most_needed_numbers)

    if num_left == 1:
        options = [option for option in get_numbers_from_picka_1_pick(image_bw)]
    elif num_left == 3:
        options = [option for option in get_numbers_from_picka_3_pick(image_bw)]
    elif num_left == 2:
        options = [option for option in get_numbers_from_picka_2_pick(image_bw)]
    else:
        options = [option for option in get_numbers_from_picka_4_pick(image_bw)]

    for mnn in most_needed_numbers:
        for n, x, y in options:
            if n == mnn:
                # Click the first most needed number
                tap_screen(URL, x, y, f'picka-select {n}')
                # wait for the balls to go away
                time.sleep(.3)
                print_log('SLEPT FOR .3')
                # send number back for clicking in main func
                return n


def perform_bingo(board, has_2x):
    is_bingo = check_bingo(board)
    if is_bingo:
        if has_2x:
            tap_2x(has_2x)
            has_2x = False
        tap_bingo()

        for row in range(5):
            for col in range(5):
                if board[row][col] == 1:
                    board[row][col] = 2
    return board, has_2x


counter = 1
if _SAVE_VIDEO:
    recorder = VideoRecorder()

start_time = time.time()
prev_number = None
while True:
    current_number = None
    if counter == 1:
        os.system('clear')
        game_uuid = uuid.uuid4()
        game_logs_dir = datetime.datetime.now().strftime(f"games/{game_uuid}")
        os.makedirs(game_logs_dir, exist_ok=True)
        log_filename = f'{game_logs_dir}/game.log'
        video_file = f'{game_logs_dir}/video.mp4'
        screenshots_dir = f'{game_logs_dir}/screenshots'
        os.makedirs(screenshots_dir, exist_ok=True)

        print('Waiting for game to start...')
        png_data = get_screenshot_as_png(URL, )
        image = Image.open(BytesIO(png_data))
        while not board_is_ready(image, game_start):
            png_data = get_screenshot_as_png(URL, )
            image = Image.open(BytesIO(png_data))
        threading.Thread(target=save_to_file, args=(png_data, f"{screenshots_dir}/{counter}.png")).start()
        image = Image.open(BytesIO(png_data))

        if _SAVE_VIDEO:
            recorder.start_recording(video_file)

    else:
        end_time = time.time()
        duration = end_time - start_time
        start_time = time.time()
        print_log(f"\n[{counter}] - ({duration:.2f} sec)")
        print_log(f"\n[{counter}]")

    png_data = get_screenshot_as_png(URL, 'top of loop')
    image = Image.open(BytesIO(png_data))
    image.load()
    image_just_called_number = crop_image(image, 0, 0, image.width, image.height / 5, buffer=0).convert('L')

    if counter == 1:
        print_log('getting game board...')
        # This is the first one - set up the board
        image = image.convert('L')  # Convert to grayscale
        game_board, number_coords = get_bingo_number_coords(image)
        number_lookup = reverse_lookup(number_coords)
        DAUB_TRACKER = [
            [0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0],
            [0, 0, 1, 0, 0],
            [0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0],
        ]
        try:
            board = to_5x5_matrix(list(game_board.keys()))
            print_log(f'Game UUID: {game_uuid}')
            for row in range(5):
                row_str = ''
                for col in range(5):
                    actual = board[row][col]
                    row_str += f'{actual}\t'
                print_log(row_str)
        except:
            pass
        counter += 1
        continue

    # MAIN GAME LOOP LOGIC

    # First, check which powerups are available
    p1, p2 = check_powerups(image)

    has_2x = False
    if p1 == PW_2X:
        has_2x = 'p1'
    elif p2 == PW_2X:
        has_2x = 'p2'

    has_picka = False
    if p1 == PW_PICKA:
        has_picka = 'p1'
    elif p2 == PW_PICKA:
        has_picka = 'p2'

    # Second, check which number is being called
    current_number = get_current_called_number(image_just_called_number)
    threading.Thread(target=save_to_file, args=(png_data, f"{screenshots_dir}/{counter}.png")).start()

    # Third, Daub the called number (using 2X powerup if it's available)
    if current_number:
        if current_number in game_board:
            x, y = game_board[current_number]
            dcol, drow = number_coords[current_number]
            if DAUB_TRACKER[drow][dcol] == 0:
                if prev_number != current_number:
                    print_log(f'NUM = {current_number} - ✅')
                prev_number = current_number
                if has_2x:
                    tap_2x(has_2x)
                    has_2x = False
                DAUB_TRACKER[drow][dcol] = 1
                tap_screen(URL, x, y, current_number)
                DAUB_TRACKER, has_2x = perform_bingo(DAUB_TRACKER, has_2x)
            else:
                print_log(f'NUM = {current_number}')
        else:
            print_log(f'NUM = {current_number}')

    # Forth, use STAR powerups if they are available
    tapped_numbers, has_2x = perform_star_pw(p1, p2, number_lookup, DAUB_TRACKER, has_2x)
    if tapped_numbers:
        has_2x = False
        for tapped_number in tapped_numbers:
            dcol, drow = number_coords[tapped_number]
            DAUB_TRACKER[drow][dcol] = 1
        DAUB_TRACKER, has_2x = perform_bingo(DAUB_TRACKER, has_2x)

    # Fifth, use PICKA powerups if they are available
    if has_picka:
        # If powerups are full, use a PICKA
        most_needed = most_needed_spots(DAUB_TRACKER)
        lookup = reverse_lookup(number_coords)
        most_needed_numbers = [lookup[col][row] for row, col in most_needed]
        current_number = perform_picka_pw(counter, has_picka, most_needed_numbers)

    # Lastly, if the Extra Time powerup is available, always click it
    if p1 == PW_TIME:
        tap_power_1(PW_TIME)
    if p2 == PW_TIME:
        tap_power_2(PW_TIME)

    # If there is no current number, check if the game has ended
    if not current_number:
        # Check for Game Over
        if is_game_over(image, GAME_OVER):
            print_log(f'GAME OVER\n\n -- {game_uuid}')
            counter = 1
            if _SAVE_VIDEO:
                print_log('Sleeping 10 seconds so we capture the final screen on video')
                time.sleep(10)
                print_log(f"Saving Video to {video_file}...")
                recorder.stop_recording()
            continue

    counter += 1
