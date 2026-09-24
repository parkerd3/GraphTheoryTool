"""Application entry point for GraphTheoryTool."""

import sys

from PySide6.QtWidgets import QApplication

try:
    from .view.main_window import MainWindow
except ImportError:  # Allows running this file directly with ``python main.py``.
    from view.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
