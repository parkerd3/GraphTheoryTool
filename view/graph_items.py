"""Graphics items and their shared visual styles."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QPen
from PySide6.QtWidgets import QGraphicsEllipseItem, QGraphicsLineItem

NODE_BRUSH = QBrush(QColor("#4f86c6"))
SELECTED_NODE_BRUSH = QBrush(QColor("#f28c28"))
NODE_PEN = QPen(QColor("#16324f"), 2)
EDGE_PEN = QPen(QColor("#4f6894"), 4)
SELECTED_EDGE_PEN = QPen(QColor("#f28c28"), 4)
SELECTION_RECT_PEN = QPen(QColor("#f28c28"), 1, Qt.PenStyle.DashLine)
SELECTION_RECT_BRUSH = QBrush(QColor(242, 140, 40, 45))


class NodeGraphicsItem(QGraphicsEllipseItem):
    """Visual circle representing one node in the graph model."""

    RADIUS = 20

    def __init__(self, node_id: int, x: float, y: float) -> None:
        super().__init__(
            x - self.RADIUS,
            y - self.RADIUS,
            self.RADIUS * 2,
            self.RADIUS * 2,
        )
        self.node_id = node_id
        self.setBrush(NODE_BRUSH)
        self.setPen(NODE_PEN)
        self.setData(0, node_id)

    def set_center(self, x: float, y: float) -> None:
        """Move the visual circle so its center is at ``(x, y)``."""

        self.setRect(
            x - self.RADIUS,
            y - self.RADIUS,
            self.RADIUS * 2,
            self.RADIUS * 2,
        )

    def set_selected(self, selected: bool) -> None:
        """Update the node's selection appearance."""

        self.setBrush(SELECTED_NODE_BRUSH if selected else NODE_BRUSH)


class EdgeGraphicsItem(QGraphicsLineItem):
    """Visual line representing one edge in the graph model."""

    def __init__(
        self,
        source: int,
        target: int,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
    ) -> None:
        super().__init__(x1, y1, x2, y2)
        self.source = source
        self.target = target
        self.setPen(EDGE_PEN)
        self.setZValue(-1)

    def set_endpoints(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
    ) -> None:
        """Update the line while its endpoint nodes move."""

        self.setLine(x1, y1, x2, y2)

    def set_selected(self, selected: bool) -> None:
        """Update the edge's selection appearance."""

        self.setPen(SELECTED_EDGE_PEN if selected else EDGE_PEN)
