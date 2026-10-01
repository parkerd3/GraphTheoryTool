"""Numbered directed arcs for inspecting an undirected graph."""

import math

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QBrush, QFont, QPainterPath, QPalette, QPen, QPolygonF
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsPathItem,
    QGraphicsPolygonItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
)

try:
    from ..matrices import DirectedArc, directed_arcs
    from ..model import Graph
except ImportError:  # Supports launching with ``python main.py``.
    from matrices import DirectedArc, directed_arcs
    from model import Graph

from .graph_items import EDGE_PEN, NodeGraphicsItem


class ArcGraphicsItem(QGraphicsPathItem):
    """Curved arrow with a number matching its matrix row and column."""

    def __init__(self, arc: DirectedArc, graph: Graph) -> None:
        super().__init__()
        self.arc = arc
        self.setPen(EDGE_PEN)
        self.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self.setZValue(-1)
        source = graph.get_node(arc.source)
        target = graph.get_node(arc.target)
        self.setToolTip(f"Arc {arc.index}: {source.label} → {target.label}")

        self.arrowhead = QGraphicsPolygonItem(self)
        self.arrowhead.setPen(QPen(Qt.PenStyle.NoPen))
        self.arrowhead.setBrush(QBrush(EDGE_PEN.color()))
        self.arrowhead.setAcceptedMouseButtons(Qt.MouseButton.NoButton)

        self.label_background = QGraphicsRectItem(self)
        self.label_background.setPen(QPen(Qt.PenStyle.NoPen))
        self.label_background.setBrush(
            QApplication.palette().brush(QPalette.ColorRole.Base)
        )
        self.label_background.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self.label_background.setZValue(1)
        self.label = QGraphicsSimpleTextItem(str(arc.index), self.label_background)
        font = QFont(QApplication.font())
        font.setBold(True)
        font.setPointSize(max(10, font.pointSize() + 1))
        self.label.setFont(font)
        self.label.setBrush(QApplication.palette().brush(QPalette.ColorRole.Text))
        self.label.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self.label.setToolTip(self.toolTip())
        self._set_geometry(QPointF(source.x, source.y), QPointF(target.x, target.y))

    def _set_geometry(self, source: QPointF, target: QPointF) -> None:
        delta = target - source
        distance = math.hypot(delta.x(), delta.y())
        if distance <= 2 * NodeGraphicsItem.RADIUS:
            # Coincident or overlapping nodes have no exposed edge to draw.
            self.label_background.hide()
            return

        normal = QPointF(-delta.y() / distance, delta.x() / distance)
        bend = min(60.0, max(25.0, distance * 0.15))
        control = (source + target) / 2 + normal * bend

        # Clip each end to its node circle. Reversing the endpoints reverses
        # the normal too, placing the reverse arc on the opposite side.
        source_tangent = control - source
        source_length = math.hypot(source_tangent.x(), source_tangent.y())
        target_tangent = target - control
        target_length = math.hypot(target_tangent.x(), target_tangent.y())
        radius = NodeGraphicsItem.RADIUS + 1
        start = source + source_tangent / source_length * radius
        end = target - target_tangent / target_length * radius
        path = QPainterPath(start)
        path.quadTo(control, end)
        self.setPath(path)

        tangent = end - control
        tangent /= math.hypot(tangent.x(), tangent.y())
        sideways = QPointF(-tangent.y(), tangent.x())
        base = end - tangent * 12
        self.arrowhead.setPolygon(
            QPolygonF([end, base + sideways * 6, base - sideways * 6])
        )

        label_center = path.pointAtPercent(0.5) + normal * 12
        bounds = self.label.boundingRect()
        self.label_background.setRect(bounds.adjusted(-3, -2, 3, 2))
        self.label_background.setPos(label_center - bounds.center())


class DirectedArcScene(QGraphicsScene):
    """A read-only arc representation; the graph itself is never changed."""

    def __init__(self, graph: Graph, parent=None) -> None:
        super().__init__(parent)
        self.graph = graph
        self.arcs: tuple[DirectedArc, ...] = ()
        self.arc_items: list[ArcGraphicsItem] = []
        self.node_items: dict[int, NodeGraphicsItem] = {}

    def rebuild_from_graph(self) -> None:
        """Refresh the derived arrows and labels from the current graph."""

        self.clear()
        self.arc_items.clear()
        self.node_items.clear()
        self.arcs = directed_arcs(self.graph)
        for arc in self.arcs:
            item = ArcGraphicsItem(arc, self.graph)
            self.addItem(item)
            self.arc_items.append(item)
        for node in self.graph.nodes:
            circle = NodeGraphicsItem(node.id, node.x, node.y)
            circle.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
            self.addItem(circle)
            self.node_items[node.id] = circle

    def contextMenuEvent(self, event) -> None:
        """Keep editing commands out of the inspection view."""

        event.ignore()
