#!/usr/bin/env python3
"""
PCCooler LCD Manager - Background Editor

Standalone image crop/scale/rotate editor.
Target display resolution: 240x320.

No USB communication.
"""

import sys
from pathlib import Path

from PySide6.QtCore import Qt, QPointF, Signal, QTimer
from PySide6.QtGui import (
    QImage,
    QPainter,
    QPixmap,
    QTransform,
    QMovie,
    QFont,
    QColor,
)
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
    QComboBox,
    QCheckBox,
    QSpinBox,
    QColorDialog,
)


from renderer import render
from gif_exporter import export_gif
from video_preview import VideoPreview
from background_jobs import (
    create_background_job,
    get_current_background,
)
from main import EditableText, TEXT
from config import load_config, save_config
from sensors import read_temp
from datetime import datetime

WIDTH = 240
HEIGHT = 320


class ImageView(QGraphicsView):
    scale_requested = Signal(float)
    position_changed = Signal()

    def __init__(self):
        super().__init__()

        self.scene_obj = QGraphicsScene(self)
        self.scene_obj.setSceneRect(0, 0, WIDTH, HEIGHT)

        self.setScene(self.scene_obj)
        self.setFixedSize(WIDTH * 2 + 4, HEIGHT * 2 + 4)

        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)

        self.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        self.setTransformationAnchor(
            QGraphicsView.ViewportAnchor.AnchorUnderMouse
        )

        self.setBackgroundBrush(Qt.GlobalColor.black)

        self.image_item = QGraphicsPixmapItem()
        self.image_item.setTransformationMode(
            Qt.TransformationMode.SmoothTransformation
        )
        self.image_item.setFlag(
            QGraphicsPixmapItem.GraphicsItemFlag.ItemIsMovable,
            True,
        )

        self.scene_obj.addItem(self.image_item)

        self.osd_item = QGraphicsPixmapItem()
        self.osd_item.setZValue(100)
        self.osd_item.setAcceptedMouseButtons(
            Qt.MouseButton.NoButton
        )
        self.scene_obj.addItem(self.osd_item)

        self.osd_text_items = {}

        self.scale(2, 2)

    def wheelEvent(self, event):
        factor = 1.1 if event.angleDelta().y() > 0 else 1 / 1.1
        self.scale_requested.emit(factor)
        event.accept()

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self.position_changed.emit()


class BackgroundEditor(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle(
            "PCCooler LCD Manager — Редактор дисплея"
        )

        self.original = None
        self.movie = None
        self.animated = False
        self.gif_path = None
        self.video_player = None
        self.rotation = 0
        self.zoom_percent = 100
        self.base_scale = 1.0

        self.view = ImageView()

        self.open_button = QPushButton("Открыть изображение")
        self.save_button = QPushButton("Сохранить фон в PNG")
        self.apply_button = QPushButton("Применить к дисплею")
        self.center_button = QPushButton("По центру")
        self.rotate_left_button = QPushButton("Повернуть влево")
        self.rotate_right_button = QPushButton("Повернуть вправо")

        self.mode = QComboBox()
        self.mode.addItem("Заполнить", "fill")
        self.mode.addItem("Вместить", "fit")

        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(10, 500)
        self.zoom_slider.setValue(100)

        self.osd_checkbox = QCheckBox("Показать часы и температуры")
        self.osd_checkbox.setChecked(False)

        self.edit_mode = QComboBox()
        self.edit_mode.addItem("Редактировать фон", "background")
        self.edit_mode.addItem("Редактировать показатели", "osd")

        self.selected_osd = None

        self.osd_element_label = QLabel("Элемент не выбран")

        self.osd_size = QSpinBox()
        self.osd_size.setRange(8, 100)
        self.osd_size.setEnabled(False)

        self.osd_color = QPushButton("Выбрать цвет")
        self.osd_color.setEnabled(False)

        self.osd_save = QPushButton("Сохранить настройки показателей")

        self.zoom_label = QLabel("Масштаб: 100%")
        self.status_label = QLabel(
            "Откройте изображение для редактирования."
        )

        controls = QVBoxLayout()

        controls.addWidget(self.open_button)
        controls.addWidget(self.save_button)
        controls.addWidget(self.apply_button)
        controls.addWidget(self.osd_checkbox)
        controls.addWidget(QLabel("Режим редактирования"))
        controls.addWidget(self.edit_mode)

        controls.addSpacing(12)
        controls.addWidget(self.osd_element_label)
        controls.addWidget(QLabel("Размер шрифта"))
        controls.addWidget(self.osd_size)
        controls.addWidget(self.osd_color)
        controls.addWidget(self.osd_save)

        controls.addSpacing(12)
        controls.addWidget(QLabel("Режим масштабирования"))
        controls.addWidget(self.mode)

        controls.addSpacing(12)
        controls.addWidget(self.zoom_label)
        controls.addWidget(self.zoom_slider)

        controls.addSpacing(12)
        controls.addWidget(self.center_button)
        controls.addWidget(self.rotate_left_button)
        controls.addWidget(self.rotate_right_button)

        controls.addStretch()

        layout = QHBoxLayout()
        layout.addWidget(self.view)
        layout.addLayout(controls)

        root_layout = QVBoxLayout()
        root_layout.addLayout(layout)
        root_layout.addWidget(self.status_label)

        container = QWidget()
        container.setLayout(root_layout)
        self.setCentralWidget(container)

        self.open_button.clicked.connect(self.open_image)
        self.save_button.clicked.connect(self.save_image)
        self.apply_button.clicked.connect(self.apply_background)
        self.center_button.clicked.connect(self.center_image)
        self.rotate_left_button.clicked.connect(
            lambda: self.rotate_image(-90)
        )
        self.rotate_right_button.clicked.connect(
            lambda: self.rotate_image(90)
        )

        self.mode.currentIndexChanged.connect(
            self.reset_scaling
        )

        self.zoom_slider.valueChanged.connect(
            self.update_zoom
        )

        self.osd_checkbox.toggled.connect(
            self.toggle_osd
        )

        self.edit_mode.currentIndexChanged.connect(
            self.update_edit_mode
        )

        self.view.scene_obj.selectionChanged.connect(
            self.osd_selection_changed
        )

        self.osd_size.valueChanged.connect(
            self.change_osd_size
        )

        self.osd_color.clicked.connect(
            self.change_osd_color
        )

        self.osd_save.clicked.connect(
            self.save_osd_settings
        )

        self.osd_timer = QTimer(self)
        self.osd_timer.timeout.connect(self.update_osd)
        self.osd_timer.start(2000)

        self.view.scale_requested.connect(
            self.zoom_by_factor
        )

        self.resize(760, 710)

        self.load_last_background()

    def toggle_osd(self, enabled):
        self.view.osd_item.setVisible(False)

        if enabled:
            self.create_osd_items()
            self.update_osd()

        for item in self.view.osd_text_items.values():
            item.setVisible(enabled)

        self.update_edit_mode()

    def create_osd_items(self):
        if self.view.osd_text_items:
            return

        config = load_config()

        for key, text in TEXT.items():
            item = EditableText(
                key,
                text,
                config[key],
                self.osd_item_moved,
            )
            item.setZValue(200)
            self.view.scene_obj.addItem(item)
            self.view.osd_text_items[key] = item

    def osd_selection_changed(self):
        selected = [
            item
            for item in self.view.scene_obj.selectedItems()
            if isinstance(item, EditableText)
        ]

        self.selected_osd = selected[0] if selected else None

        enabled = self.selected_osd is not None

        self.osd_size.setEnabled(enabled)
        self.osd_color.setEnabled(enabled)

        if enabled:
            item = self.selected_osd
            config = load_config()

            self.osd_element_label.setText(
                f"Элемент: {item.key}"
            )

            self.osd_size.blockSignals(True)
            self.osd_size.setValue(
                config[item.key]["size"]
            )
            self.osd_size.blockSignals(False)

        else:
            self.osd_element_label.setText(
                "Элемент не выбран"
            )

    def change_osd_size(self, value):
        if self.selected_osd is None:
            return

        config = load_config()
        key = self.selected_osd.key

        config[key]["size"] = value
        save_config(config)

        font = self.selected_osd.font()
        font.setPointSize(value)
        self.selected_osd.setFont(font)

    def change_osd_color(self):
        if self.selected_osd is None:
            return

        color = QColorDialog.getColor(
            self.selected_osd.defaultTextColor(),
            self,
        )

        if not color.isValid():
            return

        config = load_config()
        key = self.selected_osd.key

        config[key]["color"] = color.name()
        save_config(config)

        self.selected_osd.setDefaultTextColor(color)

    def save_osd_settings(self):
        config = load_config()

        for key, item in self.view.osd_text_items.items():
            config[key]["x"] = round(item.pos().x())
            config[key]["y"] = round(item.pos().y())

        save_config(config)

        self.status_label.setText(
            "Настройки показателей сохранены."
        )

    def osd_item_moved(self, item):
        config = load_config()
        config[item.key]["x"] = round(item.pos().x())
        config[item.key]["y"] = round(item.pos().y())
        save_config(config)

    def update_edit_mode(self):
        editing_osd = (
            self.edit_mode.currentData() == "osd"
        )

        self.view.image_item.setFlag(
            QGraphicsPixmapItem.GraphicsItemFlag.ItemIsMovable,
            not editing_osd,
        )

        for item in self.view.osd_text_items.values():
            item.setFlag(
                QGraphicsPixmapItem.GraphicsItemFlag.ItemIsMovable,
                editing_osd,
            )

    def reload_osd_positions(self):
        config = load_config()

        for key, item in self.view.osd_text_items.items():
            cfg = config[key]
            item.setPos(cfg["x"], cfg["y"])

    def update_osd(self):
        if not self.osd_checkbox.isChecked():
            return

        self.create_osd_items()

        cpu = read_temp("k10temp")
        gpu = read_temp("amdgpu")

        values = {
            "clock": datetime.now().strftime("%H:%M"),
            "cpu_label": "CPU",
            "cpu_value": (
                f"{cpu:.0f}°C" if cpu is not None else "--°C"
            ),
            "gpu_label": "GPU",
            "gpu_value": (
                f"{gpu:.0f}°C" if gpu is not None else "--°C"
            ),
        }

        config = load_config()

        for key, text in values.items():
            item = self.view.osd_text_items[key]
            item.setPlainText(text)

            font = QFont(
                "Liberation Sans",
                config[key]["size"],
            )
            font.setBold(True)

            item.setFont(font)
            item.setDefaultTextColor(
                QColor(config[key]["color"])
            )

    def stop_video_preview(self):
        player = self.video_player

        if player is None:
            return

        self.video_player = None

        player.stop()

        if not player.wait(5000):
            raise RuntimeError(
                "Video decoder did not stop."
            )

        player.deleteLater()

    def start_video_preview(self, path):
        self.stop_video_preview()

        if self.movie is not None:
            self.stop_animation()

        self.animated = True

        self.save_button.setEnabled(False)
        self.apply_button.setEnabled(False)

        self.original = QImage(
            WIDTH,
            HEIGHT,
            QImage.Format.Format_RGB32,
        )
        self.original.fill(Qt.GlobalColor.black)

        self.rotation = 0
        self.reset_scaling()

        self.video_player = VideoPreview(path, self)

        self.video_player.frame_ready.connect(
            self.video_frame_received
        )

        self.video_player.error.connect(
            self.video_error
        )

        self.video_player.start()

        self.status_label.setText(
            f"Воспроизводится фон: {Path(path).name}"
        )

    def video_frame_received(self, image):
        self.original = image
        self.update_pixmap()

    def video_error(self, message):
        self.status_label.setText(
            f"Ошибка воспроизведения: {message}"
        )

    def load_last_background(self):
        path = get_current_background()

        if path is None:
            return

        if path.suffix.lower() == ".mp4":
            self.start_video_preview(path)
            return

        image = QImage(str(path))

        if image.isNull():
            self.status_label.setText(
                "Не удалось открыть последний фон."
            )
            return

        self.original = image
        self.rotation = 0
        self.reset_scaling()

        self.status_label.setText(
            f"Загружен последний фон: {path.name}"
        )

    def closeEvent(self, event):
        self.stop_video_preview()
        self.stop_animation()
        super().closeEvent(event)

    def open_image(self):
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Открыть фоновое изображение",
            str(Path.home()),
            "Изображения (*.png *.jpg *.jpeg *.webp *.bmp *.gif)",
        )

        if not filename:
            return

        image = QImage(filename)

        if image.isNull():
            QMessageBox.warning(
                self,
                "Error",
                "Cannot open image.",
            )
            return

        self.stop_video_preview()
        self.stop_animation()

        self.original = image
        self.rotation = 0
        self.reset_scaling()

        if Path(filename).suffix.lower() == ".gif":
            self.start_animation(filename)

        self.status_label.setText(
            f"Loaded: {Path(filename).name} "
            f"({image.width()}x{image.height()})"
        )

    def stop_animation(self):
        if self.movie is not None:
            self.movie.stop()
            self.movie.deleteLater()
            self.movie = None

        self.animated = False
        self.gif_path = None

        self.save_button.setEnabled(True)
        self.apply_button.setEnabled(True)

    def start_animation(self, filename):
        movie = QMovie(str(filename))
        movie.setCacheMode(QMovie.CacheMode.CacheNone)

        if not movie.isValid():
            movie.deleteLater()
            self.status_label.setText(
                "Ошибка: невозможно открыть GIF."
            )
            return

        self.movie = movie
        self.animated = True
        self.gif_path = Path(filename)

        self.save_button.setEnabled(False)
        self.apply_button.setEnabled(True)

        movie.frameChanged.connect(self.animation_frame_changed)
        movie.start()

        self.status_label.setText(
            "GIF воспроизводится. "
            "Сохранение анимации добавим следующим этапом."
        )

    def animation_frame_changed(self, frame_number):
        if self.movie is None:
            return

        frame = self.movie.currentImage()

        if frame.isNull():
            return

        self.original = frame
        self.update_pixmap()

    def rotated_image(self):
        if self.original is None:
            return None

        transform = QTransform()
        transform.rotate(self.rotation)

        return self.original.transformed(
            transform,
            Qt.TransformationMode.SmoothTransformation,
        )

    def reset_scaling(self):
        if self.original is None:
            return

        image = self.rotated_image()

        iw = image.width()
        ih = image.height()

        if not iw or not ih:
            return

        sx = WIDTH / iw
        sy = HEIGHT / ih

        if self.mode.currentData() == "fill":
            self.base_scale = max(sx, sy)
        else:
            self.base_scale = min(sx, sy)

        self.zoom_slider.setValue(100)
        self.update_pixmap()
        self.center_image()

    def update_pixmap(self):
        if self.original is None:
            return

        image = self.rotated_image()
        pixmap = QPixmap.fromImage(image)

        item = self.view.image_item

        old_center = item.mapToScene(
            item.boundingRect().center()
        )

        item.setPixmap(pixmap)

        scale = (
            self.base_scale
            * self.zoom_percent
            / 100.0
        )

        item.setScale(scale)

        new_center = item.mapToScene(
            item.boundingRect().center()
        )

        delta = old_center - new_center
        item.moveBy(delta.x(), delta.y())

    def center_image(self):
        if self.original is None:
            return

        item = self.view.image_item

        bounds = item.mapRectToScene(
            item.boundingRect()
        )

        x = (WIDTH - bounds.width()) / 2
        y = (HEIGHT - bounds.height()) / 2

        item.setPos(x, y)

    def update_zoom(self, value=None):
        self.zoom_percent = self.zoom_slider.value()

        self.zoom_label.setText(
            f"Масштаб: {self.zoom_percent}%"
        )

        self.update_pixmap()

    def zoom_by_factor(self, factor):
        value = round(
            self.zoom_slider.value() * factor
        )

        value = max(10, min(500, value))
        self.zoom_slider.setValue(value)

    def rotate_image(self, degrees):
        if self.original is None:
            return

        self.rotation = (
            self.rotation + degrees
        ) % 360

        self.reset_scaling()

    def apply_background(self):
        if self.animated:
            return self.apply_animated_background()

        if self.original is None:
            QMessageBox.information(
                self,
                "Нет изображения",
                "Сначала откройте изображение.",
            )
            return

        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "background.png"

            if not self.export_background(path):
                QMessageBox.warning(
                    self,
                    "Ошибка",
                    "Не удалось подготовить изображение.",
                )
                return

            image_data = path.read_bytes()

        job_id = create_background_job(
            image_data,
            extension=".png",
        )

        self.status_label.setText(
            f"Фон поставлен в очередь: {job_id[:8]}"
        )

        QMessageBox.information(
            self,
            "Фон подготовлен",
            "Изображение сохранено и поставлено "
            "в очередь загрузки.\\n"
            "USB Worker выполнит задание при запуске.",
        )

    def apply_animated_background(self):
        if self.gif_path is None:
            return

        import tempfile

        item = self.view.image_item
        position = item.pos()

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "background.mp4"

            try:
                export_gif(
                    source=self.gif_path,
                    destination=output,
                    x=position.x(),
                    y=position.y(),
                    scale=item.scale(),
                    rotation=self.rotation,
                )

                data = output.read_bytes()

                job_id = create_background_job(
                    data,
                    extension=".mp4",
                )

            except Exception as exc:
                QMessageBox.critical(
                    self,
                    "Ошибка анимации",
                    str(exc),
                )
                return

        self.status_label.setText(
            f"Анимация поставлена в очередь: {job_id[:8]}"
        )

        QMessageBox.information(
            self,
            "Анимация подготовлена",
            "MP4 успешно создан и поставлен "
            "в очередь загрузки.",
        )

    def export_background(self, filename):
        if self.original is None:
            return False

        result = QImage(
            WIDTH,
            HEIGHT,
            QImage.Format.Format_RGB32,
        )

        result.fill(Qt.GlobalColor.black)

        painter = QPainter(result)
        painter.setRenderHint(
            QPainter.RenderHint.SmoothPixmapTransform
        )

        item = self.view.image_item
        image = self.rotated_image()

        painter.translate(item.pos())
        painter.scale(item.scale(), item.scale())
        painter.drawImage(0, 0, image)
        painter.end()

        return result.save(str(filename), "PNG")

    def save_image(self):
        if self.original is None:
            QMessageBox.information(
                self,
                "Изображение не выбрано",
                "Сначала откройте изображение.",
            )
            return

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить фоновое изображение",
            str(Path.home() / "pccooler-background.png"),
            "PNG images (*.png)",
        )

        if not filename:
            return

        if not filename.lower().endswith(".png"):
            filename += ".png"

        result = QImage(
            WIDTH,
            HEIGHT,
            QImage.Format.Format_RGB32,
        )

        result.fill(Qt.GlobalColor.black)

        painter = QPainter(result)
        painter.setRenderHint(
            QPainter.RenderHint.SmoothPixmapTransform
        )

        item = self.view.image_item
        image = self.rotated_image()

        scale = item.scale()

        painter.translate(item.pos())
        painter.scale(scale, scale)
        painter.drawImage(0, 0, image)
        painter.end()

        if result.save(filename, "PNG"):
            self.status_label.setText(
                f"Saved: {filename} ({WIDTH}x{HEIGHT})"
            )
        else:
            QMessageBox.warning(
                self,
                "Ошибка сохранения",
                "Не удалось сохранить PNG.",
            )


if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = BackgroundEditor()
    window.show()

    sys.exit(app.exec())
