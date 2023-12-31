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

from PIL import Image
from io import BytesIO

from bingo_king.image_utils import (
    board_is_ready,
    crop_image,
    fuzz_image_compare_color,
    get_bingo_number_coords,
    get_current_called_number_alt,
    get_number,
    to_5x5_matrix,
    SIZE,
    is_game_over,
)
from utils.video_recorder import VideoRecorder

# Change this to True to save gameplay videos
_SAVE_VIDEO = True

BINGO_KING_BUNDLE_ID = 'com.bingo.king.game.ios'
WDA_PORT = 8100
MJPEG_PORT = 9100
ROOT = sys.argv[1]
URL = f"{ROOT}:{WDA_PORT}"
MJPEG_URL = f"{ROOT}:{MJPEG_PORT}"

if not ROOT:
    print('You gotta put a URL!')
    exit()

print(f'URL = {URL}')

# Get the directory of the current script
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
# Build the path to the asset relative to the root project directory
asset_path = os.path.join(ROOT_DIR, 'assets')
PW_STAR_IMG = Image.open(f'{asset_path}/powerups/star.png')
PW_3X_IMG = Image.open(f'{asset_path}/powerups/3x.png')
PW_TIME_IMG = Image.open(f'{asset_path}/powerups/extra-time.png')
PW_CROWN_IMG = Image.open(f'{asset_path}/powerups/crown.png')
GAME_OVER = Image.open(f'{asset_path}/gameover.png')
health_bar_missing_proof_seg = Image.open(f'{asset_path}/health_bar_missing_proof.png').convert('L')
post_star_bg_segment = Image.open(f'{asset_path}/post_star_bg_segment.png').convert('L')
bg_segment = Image.open(f'{asset_path}/new_bg_segment.png').convert('L')
game_start = Image.open(f'{asset_path}/updated_game_start.jpg')
GAME_OVER.load()
PW_STAR_IMG.load()
PW_3X_IMG.load()
PW_TIME_IMG.load()
PW_CROWN_IMG.load()
health_bar_missing_proof_seg.load()
post_star_bg_segment.load()
bg_segment.load()
game_start.load()

PW_STAR = 'STAR'
PW_3X = '3X'
PW_TIME = 'TIME'
PW_CROWN = 'CROWN'

# Coords of Power Up Bubbles
P1_X = 255
P1_Y = 1850
P1_W = P1_H = 170

BOUNDARY = b"--BoundaryString"
FRAME_RATE = 10  # Assuming 10 FPS

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
    global _SAVE_VIDEO
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


def reverse_lookup(number_coords):
    reverse_dict = {}

    for number, (i, j) in number_coords.items():
        if i not in reverse_dict:
            reverse_dict[i] = {}
        reverse_dict[i][j] = number

    return reverse_dict


def _translate_to_clickable_coord(num):
    return num / 2 + (SIZE / 2)


def fetch_star_picks_data(x, y, w, h, buffer, image):
    cropped = crop_image(image, x, y, w, h, buffer=buffer)
    return [get_number(cropped), _translate_to_clickable_coord(x), _translate_to_clickable_coord(y)]


def get_numbers_from_star_4_pick(image):
    coords = [
        (380, 810, SIZE, SIZE, 20),
        (1050, 810, SIZE, SIZE, 20),
        (375, 1330, SIZE, SIZE, 20),
        (375, 1330, SIZE, SIZE, 20),
        (1050, 1330, SIZE, SIZE, 20),
    ]

    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(lambda args: fetch_star_picks_data(*args, image=image), coords))

    return results


def get_numbers_from_star_3_pick(image):
    coords = [
        (710, 770, SIZE, SIZE, 20),
        (330, 1320, SIZE, SIZE, 20),
        (1050, 1320, SIZE, SIZE, 20),
    ]

    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(lambda args: fetch_star_picks_data(*args, image=image), coords))

    return results


def get_numbers_from_star_2_pick(image):
    coords = [
        (715, 1320, SIZE, SIZE, 20),
        (715, 1320, SIZE, SIZE, 20),
    ]

    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(lambda args: fetch_star_picks_data(*args, image=image), coords))

    return results


def get_numbers_from_star_1_pick(image):
    first = crop_image(image, 710, 1150, SIZE, SIZE, buffer=20)
    return [[get_number(first), _translate_to_clickable_coord(710), _translate_to_clickable_coord(1150)]]


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


class BingoGameLogic:
    def __init__(
            self,
            game_board,
            number_coords,
            daub_tracker,
            number_lookup,
            p1=None,
            p2=None,
            p3=None,
    ):
        self._game_board = game_board
        self._number_coords = number_coords
        self._daub_tracker = daub_tracker
        self._number_lookup = number_lookup
        self._p1 = p1
        self._p2 = p2
        self._p3 = p3
        self.star_was_used = False
        self._last_tapped_time = time.time()
        self._game_start = time.time()
        self._last_num = 0

    def check_powerups(self, image):
        coords = [
            (image, P1_X, P1_Y, P1_W, P1_H, 48),
            (image, P1_X + 187, P1_Y, P1_W, P1_H, 48),
            (image, P1_X + (187 * 2), P1_Y, P1_W, P1_H, 48)
        ]

        with concurrent.futures.ThreadPoolExecutor() as executor:
            p1, p2, p3 = list(executor.map(lambda args: get_powerup(crop_image(*args)), coords))

        self._p1 = p1
        self._p2 = p2
        self._p3 = p3

    def needed(self, number):
        if number not in self._game_board:
            return False

        dcol, drow = self._number_coords[number]
        return self._daub_tracker[drow][dcol] == 0

    def daub_number(self, current_number, suppress_3x=False):
        if not current_number:
            return

        if not self.needed(current_number):
            print_log(f'NUM = {current_number} - not needed')
            return

        x, y = self._game_board[current_number]
        dcol, drow = self._number_coords[current_number]
        if self._daub_tracker[drow][dcol] != 0:
            print_log(f'NUM = {current_number} - already daubed')
            return

        print_log(f'NUM = {current_number} - ✅')
        self._daub_tracker[drow][dcol] = 1
        if not suppress_3x:
            self.tap_3x(is_bingo=self.check_bingo())
        tap_screen(URL, x, y, current_number)
        self._last_num = current_number
        self.perform_bingo()

    def check_bingo(self):
        n = len(self._daub_tracker)

        def is_valid_bingo(line):
            return all(x > 0 for x in line) and any(x == 1 for x in line)

        # Check rows and columns
        for i in range(n):
            if is_valid_bingo(self._daub_tracker[i]) or is_valid_bingo([row[i] for row in self._daub_tracker]):
                return True

        # Check main diagonals
        diag1 = [self._daub_tracker[i][i] for i in range(n)]
        diag2 = [self._daub_tracker[i][n - 1 - i] for i in range(n)]
        if is_valid_bingo(diag1) or is_valid_bingo(diag2):
            return True

        # Check four corners
        corners = [
            self._daub_tracker[0][0],
            self._daub_tracker[0][n - 1],
            self._daub_tracker[n - 1][0],
            self._daub_tracker[n - 1][n - 1]
        ]
        if is_valid_bingo(corners):
            return True

        return False

    def perform_bingo(self):
        if not self.check_bingo():
            return

        self.tap_3x(is_bingo=True)
        tap_bingo()

        for row in range(5):
            for col in range(5):
                if self._daub_tracker[row][col] == 1:
                    self._daub_tracker[row][col] = 2

    def is_3x_in_progress(self):
        time_since_last_tap = int(time.time() - self._last_tapped_time)
        print_log(f'\t\tTime since last 3x: {time_since_last_tap}')
        return time_since_last_tap <= 7

    def is_end_game(self):
        """Return true if we're in the last few seconds of the game"""
        time_since_game_start = int(time.time() - self._game_start)
        return time_since_game_start >= 80

    def tap_3x(self, is_bingo):
        if self.is_3x_in_progress():
            return

        # Check conditions for tapping 3x
        available_3x = [self._p1, self._p2, self._p3].count(PW_3X)
        if not available_3x:
            return

        full_bubbles = all([self._p1, self._p2, self._p3])

        # 3X is only for BINGO if there is only 1
        # But we break that rule if all the bubbles are full, we want to make room
        def x(x):
            return 't' if x else 'f'

        if not self.is_end_game():
            if available_3x == 1:
                if not is_bingo and not full_bubbles:
                    return

        if self._p1 == PW_3X:
            tap_power_1(PW_3X)
            self._p1 = None
            self._last_tapped_time = time.time()
            time.sleep(.1)
            return

        if self._p2 == PW_3X:
            tap_power_2(PW_3X)
            self._p2 = None
            self._last_tapped_time = time.time()
            time.sleep(.1)
            return

        if self._p3 == PW_3X:
            tap_power_3(PW_3X)
            self._p3 = None
            self._last_tapped_time = time.time()
            time.sleep(.1)
            return

    def tap_time(self):
        if self._p1 == PW_TIME:
            tap_power_1(PW_TIME)
            self._p1 = None
            return

        if self._p2 == PW_TIME:
            tap_power_2(PW_TIME)
            self._p2 = None
            return

        if self._p3 == PW_TIME:
            tap_power_3(PW_TIME)
            self._p3 = None
            return

    def perform_crown_pw(self):
        powerup_functions = {
            1: tap_power_1,
            2: tap_power_2,
            3: tap_power_3
        }

        powerups = [self._p1, self._p2, self._p3]
        crowns_available = powerups.count(PW_CROWN)

        if not crowns_available:
            return

        most_needed = self.most_needed_spots()

        # Use the crown immediately on the most needed spot
        for (mrow, mcol) in most_needed:
            # Get the index of the next available crown powerup
            next_crown_idx = next((idx for idx, is_crown in enumerate(powerups) if is_crown == PW_CROWN), None)

            if next_crown_idx is not None:
                # Use the crown powerup function
                powerup_functions[next_crown_idx + 1](PW_CROWN)

                # Mark the crown as used by setting it to a placeholder (e.g. None)
                powerups[next_crown_idx] = None

                # Log and tap the screen
                num = self._number_lookup[mcol][mrow]
                print_log(f'CROWN - Clicked spot = {num} -- ({mcol}, {mrow})')
                self.daub_number(num, suppress_3x=True)

                # Decrease the count of crowns available
                crowns_available -= 1

            if crowns_available == 0:
                break

    def most_needed_spots(self):
        n = len(self._daub_tracker)
        undaubed_spots = [(i, j) for i in range(n) for j in range(n) if self._daub_tracker[i][j] == 0]

        # Sort undaubed spots based on their potential impact
        # Corners will be prioritized in case of ties.
        sorted_spots = sorted(undaubed_spots, key=lambda k: -self.potential_impact(k))

        return sorted_spots

    def perform_star_pw(self, screenshots_dir, counter):
        # THE PROBLEM WITH 3X is that - the 3x button is not available to press after the bubbles go away
        # you need to make the choice to press it BEFORE activating the star...
        available_stars = [self._p1, self._p2, self._p3].count(PW_STAR)

        if not available_stars:
            return

        if self._p1 == PW_STAR:
            tap_power_1(PW_STAR)
        elif self._p2 == PW_STAR:
            tap_power_2(PW_STAR)
        else:
            tap_power_3(PW_STAR)

        most_needed = self.most_needed_spots()
        most_needed_numbers = [self._number_lookup[col][row] for row, col in most_needed]

        # if we have 4 or less spots, bingo is guaranteed, press 3x
        # 4 is guaranteed - but 13 is half the board, prob worth just clicking 3x
        if len(most_needed_numbers) <= 12:
            self.tap_3x(is_bingo=True)

        # Wait for bubbles to finish loading
        time.sleep(.3)

        png_data = get_screenshot_as_png(URL, 'STAR PW Bubbles')
        threading.Thread(target=save_to_file, args=(png_data, f"{screenshots_dir}/{counter}-star-select.png")).start()
        image = Image.open(BytesIO(png_data))
        image.load()
        num_left = len(most_needed_numbers[:4])

        options = {
            1: [option for option in get_numbers_from_star_1_pick(image)],
            2: [option for option in get_numbers_from_star_2_pick(image)],
            3: [option for option in get_numbers_from_star_3_pick(image)],
            4: [option for option in get_numbers_from_star_4_pick(image)],
        }[num_left]

        for mnn in most_needed_numbers:
            for n, x, y in options:
                if n == mnn:
                    # Click the first most needed number
                    tap_screen(URL, x, y, f'star-select {n}')
                    # wait for the balls to go away
                    time.sleep(.4)
                    # send number back for clicking in main func
                    self.daub_number(n, suppress_3x=True)
                    self.star_was_used = True
                    return

    def potential_impact(self, spot):
        n = len(self._daub_tracker)

        # Check how far along the spot is in its line
        progress = max(sum(self._daub_tracker[i][j] for i, j in line) if spot in line else 0 for line in BINGO_LINES)

        # Check how many lines the spot is part of
        overlap_count = sum(1 for line in BINGO_LINES if spot in line)

        return progress + overlap_count * 0.01  # overlap_count is given a small weight (0.01) so it acts as a tiebreaker

    def spots_needed_for_bingo(self, line):
        """Return the undaubed spots in the given line."""
        undaubed_spots = [(i, j) for i, j in line if self._daub_tracker[i][j] == 0]

        # Sort undaubed spots based on their potential impact
        # Corners will be prioritized in case of ties.
        sorted_spots = sorted(undaubed_spots, key=lambda k: -self.potential_impact(k))

        return sorted_spots


def main():
    open_app_on_ipad(URL, BINGO_KING_BUNDLE_ID, MJPEG_PORT)
    global log_filename
    if _SAVE_VIDEO:
        recorder = VideoRecorder(MJPEG_URL, BOUNDARY, FRAME_RATE)

    game = None
    start_time = time.time()
    counter = 1

    while True:
        try:
            if counter == 1:
                os.system('clear')
                game_uuid = uuid.uuid4()
                game_logs_dir = datetime.datetime.now().strftime(f"games/{game_uuid}")
                os.makedirs(game_logs_dir, exist_ok=True)
                log_filename = f'{game_logs_dir}/game.log'
                video_file = f'{game_logs_dir}/video.mp4'
                screenshots_dir = f'{game_logs_dir}/screenshots'
                os.makedirs(screenshots_dir, exist_ok=True)

                print(f'Waiting for game to start... {game_uuid}')
                png_data = get_screenshot_as_png(URL)
                image = Image.open(BytesIO(png_data))
                while not board_is_ready(image, game_start):
                    png_data = get_screenshot_as_png(URL)
                    image = Image.open(BytesIO(png_data))
                threading.Thread(target=save_to_file, args=(png_data, f"{screenshots_dir}/{counter}.png")).start()
                if _SAVE_VIDEO:
                    recorder.start_recording(video_file)

            else:
                end_time = time.time()
                duration = end_time - start_time
                start_time = time.time()
                print_log(f"\n[{counter}] - ({duration:.2f} sec)")

            png_data = get_screenshot_as_png(URL)
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
                game = BingoGameLogic(game_board, number_coords, DAUB_TRACKER, number_lookup)
                board = to_5x5_matrix(list(game_board.keys()))
                print_log(f'Game UUID: {game_uuid}')
                for row in range(5):
                    row_str = ''
                    for col in range(5):
                        actual = board[row][col]
                        row_str += f'{actual}\t'
                    print_log(row_str)
                counter += 1
                continue

            # MAIN GAME LOOP LOGIC

            # First, check which powerups are available
            game.check_powerups(image)

            # Second, check which number is being called
            current_number = get_current_called_number_alt(
                image_just_called_number,
            )

            # Third, Daub the called number (using 3X powerup if it's available)
            game.daub_number(current_number)

            # Forth, use Crown power ups if they are available
            game.perform_crown_pw()

            # Fifth, use Star power ups if they are available
            game.perform_star_pw(screenshots_dir, counter)

            # Lastly, if the Extra Time powerup is available, always click it
            game.tap_time()

            if is_game_over(image, GAME_OVER):
                raise KeyboardInterrupt()

            counter += 1
        except KeyboardInterrupt:
            if counter == 1:
                print('\nBYE!')
                exit()
            counter = 1
            if _SAVE_VIDEO:
                print_log('Sleeping 10 seconds so we capture the final screen on video')
                time.sleep(10)
                print_log(f"Saving Video to {video_file}...")
                recorder.stop_recording()
            continue


if __name__ == '__main__':
    main()
