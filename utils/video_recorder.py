import requests
import threading

import cv2
import numpy as np


class VideoRecorder:
    def __init__(self, mjpeg_url, boundary, frame_rate):
        self.recording = False
        self.video_out = None
        self.thread = None
        self.mjpeg_url = mjpeg_url
        self.boundary = boundary
        self.frame_rate = frame_rate

    def _capture_video(self):
        response = requests.get(self.mjpeg_url, stream=True)
        if response.status_code != 200:
            print(f"Failed to connect with error code: {response.status_code}")
            return

        buffer = b""
        current_game_frames = []

        for chunk in response.iter_content(chunk_size=1024):
            if not self.recording:
                break

            buffer += chunk
            if buffer.count(self.boundary) >= 2:
                parts = buffer.split(self.boundary)
                jpeg_data = parts[1].split(b'\r\n\r\n', 1)[-1]

                image_np = np.frombuffer(jpeg_data, dtype=np.uint8)
                frame = cv2.imdecode(image_np, 1)

                if frame is not None:
                    current_game_frames.append(frame)

                buffer = parts[-1]

        for frame in current_game_frames:
            self.video_out.write(frame)

        self.video_out.release()
        print('Video released')

    def start_recording(self, video_file_name):
        self.recording = True
        self.video_out = cv2.VideoWriter(
            f'{video_file_name}',
            cv2.VideoWriter_fourcc(*'mp4v'),
            self.frame_rate,
            (1668, 2224)
        )  # Change resolution if needed
        self.thread = threading.Thread(target=self._capture_video)
        self.thread.start()

    def stop_recording(self):
        self.recording = False
        self.thread.join()  # Wait for the recording thread to finish
