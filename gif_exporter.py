#!/usr/bin/env python3
"""
PCCooler LCD Manager - GIF Exporter.

Render animated GIF frames using Qt geometry,
then encode them to H.264 MP4 using FFmpeg.

No USB communication.
"""

import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageSequence

from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import (
    QImage,
    QPainter,
    QTransform,
)


WIDTH = 240
HEIGHT = 320
FPS = 20
MAX_DURATION = 30.0


def pil_to_qimage(image):
    rgba = image.convert("RGBA")

    data = rgba.tobytes()

    result = QImage(
        data,
        rgba.width,
        rgba.height,
        rgba.width * 4,
        QImage.Format.Format_RGBA8888,
    )

    return result.copy()


def export_gif(
    source,
    destination,
    x,
    y,
    scale,
    rotation=0,
):
    source = Path(source)
    destination = Path(destination)

    if not source.is_file():
        raise FileNotFoundError(source)

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    frames_written = 0
    elapsed = 0.0

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)

        with Image.open(source) as gif:
            for frame in ImageSequence.Iterator(gif):
                duration_ms = frame.info.get(
                    "duration",
                    100,
                )

                duration = max(
                    float(duration_ms) / 1000.0,
                    0.02,
                )

                if elapsed >= MAX_DURATION:
                    break

                image = pil_to_qimage(frame)

                transform = QTransform()
                transform.rotate(rotation)

                image = image.transformed(
                    transform,
                    Qt.TransformationMode.SmoothTransformation,
                )

                canvas = QImage(
                    WIDTH,
                    HEIGHT,
                    QImage.Format.Format_RGB32,
                )

                canvas.fill(Qt.GlobalColor.black)

                painter = QPainter(canvas)
                painter.setRenderHint(
                    QPainter.RenderHint.SmoothPixmapTransform
                )

                painter.translate(x, y)
                painter.scale(scale, scale)
                painter.drawImage(0, 0, image)
                painter.end()

                repeats = max(
                    1,
                    round(duration * FPS),
                )

                for _ in range(repeats):
                    if frames_written >= FPS * MAX_DURATION:
                        break

                    filename = (
                        tmp / f"frame_{frames_written:06d}.png"
                    )

                    if not canvas.save(str(filename), "PNG"):
                        raise RuntimeError(
                            f"Cannot save frame: {filename}"
                        )

                    frames_written += 1

                elapsed += duration

        if frames_written == 0:
            raise RuntimeError("No GIF frames exported")

        command = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel", "error",
            "-y",
            "-framerate", str(FPS),
            "-i", str(tmp / "frame_%06d.png"),
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            "-an",
            str(destination),
        ]

        subprocess.run(
            command,
            check=True,
        )

    return destination
