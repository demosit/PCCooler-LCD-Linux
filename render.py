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

CONFIG = Path.home() / ".config/pccooler-lcd/config.json"

DEFAULT = {
    "clock": {"x": 85, "y": 28, "size": 32, "color": "#b4dcff"},
    "cpu_label": {"x": 35, "y": 255, "size": 19, "color": "#64beff"},
    "cpu_value": {"x": 20, "y": 280, "size": 32, "color": "#ffffff"},
    "gpu_label": {"x": 155, "y": 255, "size": 19, "color": "#ff8c46"},
    "gpu_value": {"x": 140, "y": 280, "size": 32, "color": "#ffffff"}
}

def find_sensor(driver):
    for name_file in Path("/sys/class/hwmon").glob("hwmon*/name"):
        if name_file.read_text().strip() == driver:
            sensor = name_file.parent / "temp1_input"
            if sensor.exists():
                return sensor
    return None

def read_temp(driver):
    sensor = find_sensor(driver)
    if sensor:
        return float(sensor.read_text().strip()) / 1000
    return None

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

    config = (
        json.loads(CONFIG.read_text())
        if CONFIG.exists()
        else DEFAULT
    )

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
        default=str(Path.home() / "PCCooler-LCD-Linux/preview.png")
    )
    args = parser.parse_args()

    app = QApplication(sys.argv)
    render(Path(args.output))
