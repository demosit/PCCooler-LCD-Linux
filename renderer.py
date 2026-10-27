import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import (
    QColor, QFont, QImage, QPainter, QBrush
)
from PySide6.QtWidgets import (
    QApplication, QGraphicsScene, QGraphicsTextItem
)

from config import load_config
from sensors import read_temp

def render(output):
    cpu = read_temp("k10temp")
    gpu = read_temp("amdgpu")

    texts = {
        "clock": datetime.now().strftime("%H:%M"),
        "cpu_label": "CPU",
        "cpu_value": f"{cpu:.0f}°C" if cpu is not None else "--°C",
        "gpu_label": "GPU",
        "gpu_value": f"{gpu:.0f}°C" if gpu is not None else "--°C"
    }

    config = load_config()

    scene = QGraphicsScene()
    scene.setSceneRect(0, 0, 240, 320)

    for key, text in texts.items():
        cfg = config[key]

        item = QGraphicsTextItem(text)
        font = QFont("Liberation Sans", cfg["size"])
        font.setBold(True)

        item.setFont(font)
        item.setDefaultTextColor(QColor(cfg["color"]))
        item.setPos(cfg["x"], cfg["y"])

        scene.addItem(item)


    image = QImage(
        240, 320,
        QImage.Format.Format_ARGB32
    )
    image.fill(Qt.GlobalColor.transparent)

    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

    scene.render(
        painter,
        QRectF(0, 0, 240, 320),
        QRectF(0, 0, 240, 320)
    )

    painter.end()

    if not image.save(str(output), "PNG"):
        raise RuntimeError("Не удалось сохранить PNG")

    print("PNG создан:", output)
    print("CPU:", cpu)
    print("GPU:", gpu)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        default=str(Path(__file__).resolve().parent / "preview.png")
    )
    args = parser.parse_args()

    app = QApplication(sys.argv)
    render(Path(args.output))
