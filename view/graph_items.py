"""Graphics-item definitions will live here as the canvas is implemented."""

from PySide6.QtGui import QBrush, QColor, QPen

NODE_BRUSH = QBrush(QColor("#4f86c6"))
SELECTED_NODE_BRUSH = QBrush(QColor("#f28c28"))
NODE_PEN = QPen(QColor("#16324f"), 2)
EDGE_PEN = QPen(QColor("#4f6894"), 4)
