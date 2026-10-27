import sys
import json
from pathlib import Path
from datetime import datetime

from PySide6.QtCore import Qt, QPointF, QTimer
from PySide6.QtGui import QColor, QFont, QBrush, QPen
from sensors import read_temp

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout,
    QVBoxLayout, QGraphicsView, QGraphicsScene,
    QGraphicsTextItem, QPushButton, QLabel,
    QSpinBox, QColorDialog, QGroupBox, QFormLayout
)

from config import CONFIG, load_config, save_config

TEXT = {
    "clock": "22:41",
    "cpu_label": "CPU",
    "cpu_value": "41°C",
    "gpu_label": "GPU",
    "gpu_value": "53°C"
}

class EditableText(QGraphicsTextItem):
    def __init__(self, key, text, cfg, callback):
        super().__init__(text)
        self.key = key
        self.callback = callback

        font = QFont("Liberation Sans", cfg["size"])
        font.setBold(True)
        self.setFont(font)

        self.setDefaultTextColor(QColor(cfg["color"]))
        self.setPos(cfg["x"], cfg["y"])

        self.setFlags(
            QGraphicsTextItem.GraphicsItemFlag.ItemIsMovable |
            QGraphicsTextItem.GraphicsItemFlag.ItemIsSelectable
        )

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self.callback(self)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("PCCooler LCD Manager")
        self.resize(800, 480)

        self.config = load_config()
        self.items = {}
        self.selected = None

        central = QWidget()
        self.setCentralWidget(central)

        layout = QHBoxLayout(central)

        self.scene = QGraphicsScene(0, 0, 240, 320)
        self.scene.setBackgroundBrush(QBrush(QColor("#202024")))

        self.view = QGraphicsView(self.scene)
        self.view.setFixedSize(290, 370)
        self.view.setRenderHint(
            self.view.renderHints().Antialiasing
        )

        layout.addWidget(self.view)

        panel = QVBoxLayout()
        layout.addLayout(panel)

        panel.addWidget(QLabel("Перетаскивай элементы мышкой"))

        for key, text in TEXT.items():
            item = EditableText(
                key, text, self.config[key], self.item_moved
            )
            self.scene.addItem(item)
            self.items[key] = item

        self.scene.selectionChanged.connect(self.selection_changed)

        group = QGroupBox("Настройки элемента")
        form = QFormLayout(group)

        self.name_label = QLabel("Не выбран")
        form.addRow("Элемент:", self.name_label)

        self.size_spin = QSpinBox()
        self.size_spin.setRange(8, 100)
        self.size_spin.valueChanged.connect(self.change_size)
        form.addRow("Размер:", self.size_spin)

        self.color_button = QPushButton("Выбрать цвет")
        self.color_button.clicked.connect(self.change_color)
        form.addRow("Цвет:", self.color_button)

        panel.addWidget(group)

        save = QPushButton("Сохранить настройки")
        save.clicked.connect(self.save_config)
        panel.addWidget(save)

        panel.addStretch()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_preview)
        self.timer.start(2000)
        self.update_preview()

    def update_preview(self):
        cpu = read_temp("k10temp")
        gpu = read_temp("amdgpu")

        values = {
            "clock": datetime.now().strftime("%H:%M"),
            "cpu_value": f"{cpu:.0f}°C" if cpu is not None else "--°C",
            "gpu_value": f"{gpu:.0f}°C" if gpu is not None else "--°C"
        }

        for key, text in values.items():
            item = self.items[key]

            font = item.font()
            color = QColor(self.config[key]["color"])

            item.setPlainText(text)
            item.setFont(font)
            item.setDefaultTextColor(color)

    def selection_changed(self):
        selected = self.scene.selectedItems()
        self.selected = selected[0] if selected else None

        if self.selected:
            self.name_label.setText(self.selected.key)
            self.size_spin.blockSignals(True)
            self.size_spin.setValue(
                self.config[self.selected.key]["size"]
            )
            self.size_spin.blockSignals(False)
        else:
            self.name_label.setText("Не выбран")

    def item_moved(self, item):
        self.config[item.key]["x"] = round(item.pos().x())
        self.config[item.key]["y"] = round(item.pos().y())

    def change_size(self, value):
        if not self.selected:
            return

        key = self.selected.key
        self.config[key]["size"] = value

        font = self.selected.font()
        font.setPointSize(value)
        self.selected.setFont(font)

    def change_color(self):
        if not self.selected:
            return

        color = QColorDialog.getColor(
            self.selected.defaultTextColor(), self
        )

        if color.isValid():
            key = self.selected.key
            self.config[key]["color"] = color.name()
            self.selected.setDefaultTextColor(color)

    def save_config(self):
        save_config(self.config)
        self.statusBar().showMessage(
            f"Сохранено: {CONFIG}", 5000
        )

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
