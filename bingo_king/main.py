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

from image_utils import (
    board_is_ready,
    crop_image,
    fuzz_image_compare_color,
    get_bingo_number_coords,
    get_current_called_number,
    get_number,
    to_5x5_matrix
)
from utils.video_recorder import VideoRecorder

# Change this to True to save gameplay videos
_SAVE_VIDEO = False

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


def reverse_lookup(number_coords):
    reverse_dict = {}

    for number, (i, j) in number_coords.items():
        if i not in reverse_dict:
            reverse_dict[i] = {}
        reverse_dict[i][j] = number

    return reverse_dict


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


class GameState:
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
        self._last_tapped_time = 0
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

    def match(self, number):
        if number not in self._game_board:
            return False

        dcol, drow = self._number_coords[number]
        return self._daub_tracker[drow][dcol] == 0

    def daub_number(self, current_number):
        if not current_number:
            return

        if not self.match(current_number):
            print_log(f'NUM = {current_number} - not needed')
            return

        x, y = self._game_board[current_number]
        dcol, drow = self._number_coords[current_number]
        if self._daub_tracker[drow][dcol] != 0:
            print_log(f'NUM = {current_number} - already daubed')
            return

        print_log(f'NUM = {current_number} - ✅')
        self._daub_tracker[drow][dcol] = 1
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
        corners = [self._daub_tracker[0][0], self._daub_tracker[0][n - 1], self._daub_tracker[n - 1][0],
                   self._daub_tracker[n - 1][n - 1]]
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

    def tap_3x(self, is_bingo):
        current_time = time.time()
        time_since_last_tap = current_time - self._last_tapped_time

        if time_since_last_tap < 9:
            return

        available_3x = [self._p1, self._p2, self._p3].count(PW_3X)

        # Check conditions for tapping 3x
        if (is_bingo or available_3x >= 2 or (available_3x == 3 and not is_bingo)):

            if self._p1 == PW_3X:
                tap_power_1(PW_3X)
                self._p1 = None
                self._last_tapped_time = current_time
                time.sleep(.1)
                return

            if self._p2 == PW_3X:
                tap_power_2(PW_3X)
                self._p2 = None
                self._last_tapped_time = current_time
                time.sleep(.1)
                return

            if self._p3 == PW_3X:
                tap_power_3(PW_3X)
                self._p3 = None
                self._last_tapped_time = current_time
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

    def perform_crown_pw(self, current_number):
        powerup_functions = {
            1: tap_power_1,
            2: tap_power_2,
            3: tap_power_3
        }

        powerups = [self._p1, self._p2, self._p3]
        crowns_available = powerups.count(PW_CROWN)

        if not crowns_available:
            return

        if crowns_available < 3 and current_number and (
                game_state.match(current_number) or current_number == self._last_num):
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
                self.daub_number(num)

                # Decrease the count of crowns available
                crowns_available -= 1

            if crowns_available == 0:
                break

    # def perform_crown_pw(self):
    #     # Map of the powerups to their respective functions
    #     powerup_functions = {
    #         1: tap_power_1,
    #         2: tap_power_2,
    #         3: tap_power_3
    #     }
    #
    #     # Initialize list of powerups
    #     powerups = [self._p1, self._p2, self._p3]
    #
    #     # Count number of crowns available
    #     tapped_spots = []
    #     crowns_available = sum([p == PW_CROWN for p in powerups])
    #     if not crowns_available:
    #         return
    #
    #     # Iterate over potential bingo lines
    #     for line in BINGO_LINES:
    #         needed_spots = self.spots_needed_for_bingo(line)
    #
    #         # If we have enough crowns to achieve bingo
    #         if 0 < len(needed_spots) <= crowns_available:
    #             # Use the crowns
    #             for (mrow, mcol) in needed_spots:
    #                 # Get the index of the next available crown powerup
    #                 next_crown_idx = next((idx for idx, is_crown in enumerate(powerups) if is_crown == PW_CROWN), None)
    #
    #                 if next_crown_idx is not None:
    #                     # Use the crown powerup function
    #                     powerup_functions[next_crown_idx + 1](PW_CROWN)
    #
    #                     # Mark the crown as used by setting it to a placeholder (e.g. None)
    #                     powerups[next_crown_idx] = None
    #
    #                     # Log and tap the screen
    #                     num = self._number_lookup[mcol][mrow]
    #                     print_log(f'CROWN (BINGO) - Click spot = {num} -- ({mcol}, {mrow})')
    #                     self.daub_number(num)
    #
    #                     # Decrease the count of crowns available
    #                     crowns_available -= 1
    #
    #             # Exit the loop after using the crowns for a line
    #             break

    def most_needed_spots(self):
        n = len(self._daub_tracker)
        undaubed_spots = [(i, j) for i in range(n) for j in range(n) if self._daub_tracker[i][j] == 0]

        # Sort undaubed spots based on their potential impact
        # Corners will be prioritized in case of ties.
        sorted_spots = sorted(undaubed_spots, key=lambda k: -self.potential_impact(k))

        return sorted_spots

    def perform_star_pw(self, current_number):
        available_stars = [self._p1, self._p2, self._p3].count(PW_STAR)

        if not available_stars:
            return

        if available_stars < 3 and current_number and (
                game_state.match(current_number) or current_number == self._last_num):
            return

        if self._p1 == PW_STAR:
            tap_power_1(PW_STAR)
        elif self._p2 == PW_STAR:
            tap_power_2(PW_STAR)
        else:
            tap_power_3(PW_STAR)

        most_needed = self.most_needed_spots()
        most_needed_numbers = [self._number_lookup[col][row] for row, col in most_needed]

        # Wait for bubbles to finish loading
        time.sleep(.3)
        print_log('SLEPT FOR .3')

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
                    time.sleep(.3)
                    print_log('SLEPT FOR .3')
                    # send number back for clicking in main func
                    self.daub_number(n)
                    self.star_was_used = True
                    return

    def potential_impact(self, spot):
        n = len(self._daub_tracker)

        # Check how many in-progress bingos the spot is part of
        in_progress_count = sum(
            1 for line in BINGO_LINES if spot in line and sum(self._daub_tracker[i][j] for i, j in line) == n - 1)

        # If the spot is part of an in-progress bingo
        if in_progress_count > 0:
            return in_progress_count + 0.5  # 0.5 is just to give it a slight edge over other criteria

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


post_star_bg_segment = Image.open('assets/post_star_bg_segment.png').convert('L')
post_star_bg_segment.load()
bg_segment = Image.open('assets/new_bg_segment.png').convert('L')
bg_segment.load()
health_bar_missing_proof_seg = Image.open('assets/health_bar_missing_proof.png').convert('L')
health_bar_missing_proof_seg.load()
game_start = Image.open('assets/game_start.png')
game_start.load()

if _SAVE_VIDEO:
    recorder = VideoRecorder(MJPEG_URL, BOUNDARY, FRAME_RATE)

game_state = None
start_time = time.time()
counter = 1
while True:

    try:

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
            game_state = GameState(game_board, number_coords, DAUB_TRACKER, number_lookup)
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
        game_state.check_powerups(image)

        # Second, check which number is being called
        current_number = get_current_called_number(
            image_just_called_number,
            bg_segment,
            game_state.star_was_used,
            post_star_bg_segment,
            health_bar_missing_proof_seg,
        )

        # Third, Daub the called number (using 2X powerup if it's available)
        game_state.daub_number(current_number)

        # Forth, use Crown power ups if they are available
        game_state.perform_crown_pw(current_number)

        # Fifth, use Star power ups if they are available
        game_state.perform_star_pw(current_number)

        # Lastly, if the Extra Time powerup is available, always click it
        game_state.tap_time()

        counter += 1
    except KeyboardInterrupt:
        if counter == 1:
            print('BYE!')
            exit()
        print('Press enter to save video and start over > ')
        counter = 1
        if _SAVE_VIDEO:
            print_log('Sleeping 10 seconds so we capture the final screen on video')
            time.sleep(10)
            print_log(f"Saving Video to {video_file}...")
            recorder.stop_recording()
        continue
