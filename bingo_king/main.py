import base64
import concurrent.futures
import datetime
import json
import os
import requests
import sys
import threading
import time
import uuid

import cv2
import numpy as np
from PIL import Image
from io import BytesIO

from image_utils import (
    board_is_ready,
    crop_image,
    fuzz_image_compare_color,
    get_bingo_number_coords,
    get_current_called_number,
    get_number,
    is_game_over,
    to_5x5_matrix
)

# Change this to True to save gameplay videos
_SAVE_VIDEO = True

BINGO_KING_BUNDLE_ID = 'com.bingo.king.game.ios'
WDA_PORT = 8100
MJPEG_PORT = 9100
ROOT = sys.argv[1]
URL = f"{ROOT}:{WDA_PORT}"
MJPEG_URL = f"{ROOT}:{MJPEG_PORT}"

PW_STAR_IMG = Image.open('assets/powerups/star.png')
PW_3X_IMG = Image.open('assets/powerups/3x.png')
PW_TIME_IMG = Image.open('assets/powerups/extra-time.png')
PW_CROWN_IMG = Image.open('assets/powerups/crown.png')

GAME_OVER = Image.open('assets/gameover.png')
GAME_OVER.load()

PW_STAR_IMG.load()
PW_3X_IMG.load()
PW_TIME_IMG.load()
PW_CROWN_IMG.load()

PW_STAR = 'STAR'
PW_3X = '3X'
PW_TIME = 'TIME'
PW_CROWN = 'CROWN'

if not ROOT:
    print('You gotta put a URL!')
    exit()

print(f'URL = {URL}')

BOUNDARY = b"--BoundaryString"
FRAME_RATE = 10  # Assuming 20 FPS
BUFFER_SIZE = 10 * FRAME_RATE  # 10 seconds of frames


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
    print_log(f'TAP {label}')
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


# Coords of Power Up Bubbles
P1_X = 255
P1_Y = 1850
P1_W = P1_H = 170


def tap_power_1(label):
    x = P1_X / 2
    y = P1_Y / 2
    W = P1_W / 4
    tap_screen(URL, x + W, y + W, f'P1 {label}')


def tap_power_2(label):
    x = (P1_X + 187) / 2
    y = P1_Y / 2
    W = P1_W / 4
    tap_screen(URL, x + W, y + W, f'P2 {label}')


def tap_power_3(label):
    x = (P1_X + (187 * 2)) / 2
    y = P1_Y / 2
    W = P1_W / 4
    tap_screen(URL, x + W, y + W, f'P3 {label}')


def tap_bingo():
    BINGO_X = 1150 / 2
    BINGO_Y = 1950 / 2
    tap_screen(URL, BINGO_X, BINGO_Y, 'BINGO')


def get_powerup(image):
    if fuzz_image_compare_color(image, PW_STAR_IMG):
        return PW_STAR
    if fuzz_image_compare_color(image, PW_3X_IMG):
        return PW_3X
    if fuzz_image_compare_color(image, PW_TIME_IMG):
        return PW_TIME
    if fuzz_image_compare_color(image, PW_CROWN_IMG):
        return PW_CROWN
    return None


open_app_on_ipad(URL, BINGO_KING_BUNDLE_ID, MJPEG_PORT)


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


def tap_3x(has_3x):
    if has_3x == 'p1':
        tap_power_1(PW_3X)
    elif has_3x == 'p2':
        tap_power_2(PW_3X)
    elif has_3x == 'p3':
        tap_power_3(PW_3X)


def _translate_to_clickable_coord(num):
    return num / 2 + (255 / 2)


def fetch_star_picks_data(x, y, w, h, buffer, image):
    cropped = crop_image(image, x, y, w, h, buffer=buffer)
    return [get_number(cropped), _translate_to_clickable_coord(x), _translate_to_clickable_coord(y)]


def get_numbers_from_star_4_pick(image):
    coords = [
        (380, 810, 255, 255, 20),
        (1050, 810, 255, 255, 20),
        (375, 1330, 255, 255, 20),
        (1050, 1330, 255, 255, 20),
    ]

    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(lambda args: fetch_star_picks_data(*args, image=image), coords))

    return results


def get_numbers_from_star_3_pick(image):
    coords = [
        (710, 770, 255, 255, 20),
        (330, 1320, 255, 255, 20),
        (1050, 1320, 255, 255, 20),
    ]

    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(lambda args: fetch_star_picks_data(*args, image=image), coords))

    return results


def get_numbers_from_star_2_pick(image):
    coords = [
        (715, 1320, 255, 255, 20),
        (715, 1320, 255, 255, 20),
    ]

    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(lambda args: fetch_star_picks_data(*args, image=image), coords))

    return results


def get_numbers_from_star_1_pick(image):
    first = crop_image(image, 710, 1150, 255, 255, buffer=20)
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


def perform_crown_pw(p1, p2, p3, number_lookup, DAUB_TRACKER, has_3x):
    # Map of the powerups to their respective functions
    powerup_functions = {
        1: tap_power_1,
        2: tap_power_2,
        3: tap_power_3
    }

    # Initialize list of powerups
    powerups = [p1, p2, p3]

    # Count number of crowns available
    tapped_spots = []
    crowns_available = sum([p == PW_CROWN for p in powerups])
    if not crowns_available:
        return tapped_spots, has_3x

    # Iterate over potential bingo lines
    for line in BINGO_LINES:
        needed_spots = spots_needed_for_bingo(line, DAUB_TRACKER)

        # If we have enough crowns to achieve bingo
        if 0 < len(needed_spots) <= crowns_available:
            # Use the crowns
            for (mrow, mcol) in needed_spots:
                # Get the index of the next available crown powerup
                next_crown_idx = next((idx for idx, is_crown in enumerate(powerups) if is_crown == PW_CROWN), None)

                if next_crown_idx is not None:
                    # Use the crown powerup function
                    powerup_functions[next_crown_idx + 1](PW_CROWN)

                    # Mark the crown as used by setting it to a placeholder (e.g. None)
                    powerups[next_crown_idx] = None

                    # Log and tap the screen
                    num = number_lookup[mcol][mrow]
                    print_log(f'CROWN (BINGO) - Click spot = {num} -- ({mcol}, {mrow})')
                    x, y = game_board[num]
                    tapped_spots.append(num)
                    if has_3x:
                        tap_3x(has_3x)
                        has_3x = False
                    tap_screen(URL, x, y, num)

                    # Decrease the count of crowns available
                    crowns_available -= 1

            # Exit the loop after using the crowns for a line
            break

    return tapped_spots, has_3x


def check_powerups(image):
    coords = [
        (image, P1_X, P1_Y, P1_W, P1_H, 48),
        (image, P1_X + 187, P1_Y, P1_W, P1_H, 48),
        (image, P1_X + (187 * 2), P1_Y, P1_W, P1_H, 48)
    ]

    with concurrent.futures.ThreadPoolExecutor() as executor:
        p1, p2, p3 = list(executor.map(lambda args: get_powerup(crop_image(*args)), coords))

    valid_powerups = {PW_STAR, PW_3X, PW_TIME, PW_CROWN}
    num_powerups = sum(1 for p in [p1, p2, p3] if p in valid_powerups)

    return p1, p2, p3, num_powerups


def perform_star_pw(counter, has_star, most_needed_numbers):
    if has_star == 'p1':
        tap_power_1(PW_STAR)
    elif has_star == 'p2':
        tap_power_2(PW_STAR)
    elif has_star == 'p3':
        tap_power_3(PW_STAR)

    # Wait for bubbles to finish loading
    time.sleep(.3)
    print_log('SLEPT FOR .3')

    png_data = get_screenshot_as_png(URL, 'STAR PW Bubbles')
    threading.Thread(target=save_to_file, args=(png_data, f"{screenshots_dir}/{counter}-star-select.png")).start()
    image = Image.open(BytesIO(png_data))
    image.load()
    num_left = len(most_needed_numbers)

    if num_left == 1:
        options = [option for option in get_numbers_from_star_1_pick(image)]
    elif num_left == 3:
        options = [option for option in get_numbers_from_star_3_pick(image)]
    elif num_left == 2:
        options = [option for option in get_numbers_from_star_2_pick(image)]
    else:
        options = [option for option in get_numbers_from_star_4_pick(image)]

    for mnn in most_needed_numbers:
        for n, x, y in options:
            if n == mnn:
                # Click the first most needed number
                tap_screen(URL, x, y, f'star-select {n}')
                # wait for the balls to go away
                time.sleep(.3)
                print_log('SLEPT FOR .3')
                # send number back for clicking in main func
                return n


def perform_bingo(board, has_3x):
    is_bingo = check_bingo(board)
    if is_bingo:
        if has_3x:
            tap_3x(has_3x)
            has_3x = False
        tap_bingo()

        for row in range(5):
            for col in range(5):
                if board[row][col] == 1:
                    board[row][col] = 2
    return board, has_3x


post_star_bg_segment = Image.open('assets/post_star_bg_segment.png').convert('L')
post_star_bg_segment.load()
bg_segment = Image.open('assets/new_bg_segment.png').convert('L')
bg_segment.load()
health_bar_missing_proof_seg = Image.open('assets/health_bar_missing_proof.png').convert('L')
health_bar_missing_proof_seg.load()
game_start = Image.open('assets/game_start.png')
game_start.load()

if _SAVE_VIDEO:
    recorder = VideoRecorder()

star_was_used = False
start_time = time.time()
counter = 1
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

        print('Waiting for game to start... ')
        png_data = get_screenshot_as_png(URL)
        image = Image.open(BytesIO(png_data))
        while not board_is_ready(image, game_start):
            png_data = get_screenshot_as_png(URL)
            image = Image.open(BytesIO(png_data))
        threading.Thread(target=save_to_file, args=(png_data, f"{screenshots_dir}/{counter}.png")).start()
        image = Image.open(BytesIO(png_data))
        star_was_used = False
        if _SAVE_VIDEO:
            recorder.start_recording(video_file)

    else:
        end_time = time.time()
        duration = end_time - start_time
        start_time = time.time()
        print_log(f"\n[{counter}] - ({duration:.2f} sec)")

    png_data = get_screenshot_as_png(URL, 'top of loop')
    threading.Thread(target=save_to_file, args=(png_data, f"{screenshots_dir}/{counter}.png")).start()
    image = Image.open(BytesIO(png_data))
    image.load()
    image_just_called_number = crop_image(image, 0, 0, image.width, image.height / 3, buffer=0).convert('L')

    if counter == 1:
        print_log('getting game board...')
        image = image.convert('L')
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
    p1, p2, p3, num_powerups = check_powerups(image)

    has_3x = False
    if p1 == PW_3X:
        has_3x = 'p1'
    elif p2 == PW_3X:
        has_3x = 'p2'
    elif p3 == PW_3X:
        has_3x = 'p3'

    has_star = False
    if p1 == PW_STAR:
        has_star = 'p1'
    elif p2 == PW_STAR:
        has_star = 'p2'
    elif p3 == PW_STAR:
        has_star = 'p3'

    # Second, check which number is being called
    current_number = get_current_called_number(
        image_just_called_number,
        bg_segment,
        star_was_used,
        post_star_bg_segment,
        health_bar_missing_proof_seg,
    )

    # Third, Daub the called number (using 2X powerup if it's available)
    if current_number:
        if current_number in game_board:
            x, y = game_board[current_number]
            dcol, drow = number_coords[current_number]
            if DAUB_TRACKER[drow][dcol] == 0:
                print_log(f'NUM = {current_number} - ✅')
                if has_3x:
                    tap_3x(has_3x)
                    has_3x = False
                DAUB_TRACKER[drow][dcol] = 1
                tap_screen(URL, x, y, current_number)
                DAUB_TRACKER, has_3x = perform_bingo(DAUB_TRACKER, has_3x)
            else:
                print_log(f'NUM = {current_number} - already daubed')
        else:
            print_log(f'NUM = {current_number} - not needed')

    # Forth, use Crown power ups if they are available
    tapped_numbers, has_3x = perform_crown_pw(p1, p2, p3, number_lookup, DAUB_TRACKER, has_3x)
    if tapped_numbers:
        has_3x = False
        for tapped_number in tapped_numbers:
            dcol, drow = number_coords[tapped_number]
            DAUB_TRACKER[drow][dcol] = 1
        DAUB_TRACKER, has_3x = perform_bingo(DAUB_TRACKER, has_3x)

    # Fifth, use Star power ups if they are available
    if has_star:
        most_needed = most_needed_spots(DAUB_TRACKER)
        lookup = reverse_lookup(number_coords)
        most_needed_numbers = [lookup[col][row] for row, col in most_needed]
        try:
            current_number = perform_star_pw(counter, has_star, most_needed_numbers)
            star_was_used = True
            x, y = game_board[current_number]
            dcol, drow = number_coords[current_number]
        except Exception as err:
            # Sometimes we click "Star" at the end of the game, and there is not enough time to finish
            print_log(f'ERROR: perform_star_pw -- {err} -- end of game?')

        # DAUB
        if has_3x:
            tap_3x(has_3x)
            has_3x = False
        DAUB_TRACKER[drow][dcol] = 1
        tap_screen(URL, x, y, current_number)
        DAUB_TRACKER, has_3x = perform_bingo(DAUB_TRACKER, has_3x)

    # Lastly, if the Extra Time powerup is available, always click it
    if p1 == PW_TIME:
        tap_power_1(PW_TIME)
        num_powerups -= 1
    if p2 == PW_TIME:
        tap_power_2(PW_TIME)
        num_powerups -= 1
    if p3 == PW_TIME:
        tap_power_3(PW_TIME)
        num_powerups -= 1

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
