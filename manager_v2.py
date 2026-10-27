#!/usr/bin/env python3
"""
PCCooler LCD Manager V2.

Unified display editor.
"""

import sys

from PySide6.QtWidgets import QApplication

from background_editor import BackgroundEditor


def main():
    app = QApplication(sys.argv)

    window = BackgroundEditor()
    window.setWindowTitle(
        "PCCooler LCD Manager — Редактор дисплея"
    )
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
