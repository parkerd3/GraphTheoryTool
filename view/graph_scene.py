"""Initial graph canvas.

The scene is intentionally small for the first milestone.  Node and edge
graphics will be added after the model and window shell are in place.
"""
from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QPen
from PySide6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsScene,
    QGraphicsTextItem,
    QGraphicsSceneMouseEvent,
)

try:
    from ..model import Graph
except ImportError:  # Supports launching with ``python main.py``.
    from model import Graph


class GraphScene(QGraphicsScene):
    """Scene that will display and edit a :class:`Graph`."""

    def __init__(self, graph: Graph | None = None, parent=None) -> None:
        super().__init__(parent)
        self.graph = graph or Graph()
        self.mode = "select"
        self.labels_visible = False
        self.node_items = {}
        self.edge_items = {}
        self.setSceneRect(0, 0, 1200, 800)
        
    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            position = event.scenePos()

            if self.mode == "add_node":
                current_id = self.graph._next_id
                node = self.graph.add_node(position.x(), position.y())

                self.add_node_visual(node)

                print(f"New node created with the id '{self.graph._nodes[current_id].id}', label '{self.graph._nodes[current_id].label}', and at position ({self.graph._nodes[current_id].x},{self.graph._nodes[current_id].y})")
                self.update()
        
        super().mousePressEvent(event)

    def add_node_visual(self, node) -> None:
        radius = 20

        circle = QGraphicsEllipseItem(
            node.x - radius,
            node.y - radius,
            radius * 2,
            radius * 2,
        )

        circle.setBrush(QBrush(QColor("#4f89c6")))
        circle.setPen(QPen(QColor("#16324f"), 2))

        label = QGraphicsTextItem(str(node.label))
        label.setDefaultTextColor(Qt.GlobalColor.black)
        label.setVisible(self.labels_visible)

        text_width = label.boundingRect().width()
        text_height = label.boundingRect().height()

        label.setPos(
            node.x - text_width / 2,
            node.y - text_height / 2,
        )

        self.addItem(circle)
        self.addItem(label)

        self.node_items[node.id] = {
            "circle": circle,
            "label": label,
        }

    def set_labels_visible(self, visible: bool) -> None:
        """Show or hide every node label currently in the scene."""

        self.labels_visible = visible
        for items in self.node_items.values():
            items["label"].setVisible(visible)

