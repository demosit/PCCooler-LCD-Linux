#!/usr/bin/env python3
"""
PCCooler LCD Manager - MP4 Preview.

Decode MP4 using FFmpeg in a dedicated Qt thread.

No Qt Multimedia dependency.
No USB communication.
"""

import subprocess
import threading
import time
from pathlib import Path

from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage


WIDTH = 240
HEIGHT = 320
FPS = 20

FRAME_SIZE = WIDTH * HEIGHT * 3


class VideoPreview(QThread):
    frame_ready = Signal(QImage)
    error = Signal(str)

    def __init__(self, filename, parent=None):
        super().__init__(parent)

        self.filename = Path(filename)
        self._stop_event = threading.Event()
        self._process = None
        self._process_lock = threading.Lock()

    def stop(self):
        self._stop_event.set()

        with self._process_lock:
            process = self._process

        if process is not None and process.poll() is None:
            try:
                process.terminate()
            except ProcessLookupError:
                pass

    def run(self):
        if not self.filename.is_file():
            self.error.emit(
                f"Video not found: {self.filename}"
            )
            return

        command = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel", "error",
            "-stream_loop", "-1",
            "-i", str(self.filename),
            "-an",
            "-vf",
            f"fps={FPS},scale={WIDTH}:{HEIGHT}",
            "-pix_fmt", "rgb24",
            "-f", "rawvideo",
            "pipe:1",
        ]

        process = None

        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                bufsize=FRAME_SIZE * 2,
            )

            with self._process_lock:
                self._process = process

            frame_interval = 1.0 / FPS
            next_frame = time.monotonic()

            while not self._stop_event.is_set():
                frame = bytearray()

                while len(frame) < FRAME_SIZE:
                    if self._stop_event.is_set():
                        break

                    chunk = process.stdout.read(
                        FRAME_SIZE - len(frame)
                    )

                    if not chunk:
                        break

                    frame.extend(chunk)

                if len(frame) != FRAME_SIZE:
                    if not self._stop_event.is_set():
                        self.error.emit(
                            "FFmpeg stopped producing video frames."
                        )
                    break

                image = QImage(
                    bytes(frame),
                    WIDTH,
                    HEIGHT,
                    WIDTH * 3,
                    QImage.Format.Format_RGB888,
                ).copy()

                self.frame_ready.emit(image)

                next_frame += frame_interval

                delay = next_frame - time.monotonic()

                if delay > 0:
                    self._stop_event.wait(delay)
                elif delay < -1.0:
                    next_frame = time.monotonic()

        except Exception as exc:
            if not self._stop_event.is_set():
                self.error.emit(str(exc))

        finally:
            self._stop_event.set()

            if process is not None:
                if process.poll() is None:
                    process.terminate()

                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()

                if process.stdout is not None:
                    process.stdout.close()

            with self._process_lock:
                self._process = None
