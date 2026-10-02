"""Numbered directed arcs for inspecting an undirected graph."""

import math

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QFontMetricsF, QPainterPath, QPalette, QPen
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsPathItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
)

try:
    from ..matrices import DirectedEdge, directed_arcs
    from ..model import Graph
except ImportError:  # Supports launching with ``python main.py``.
    from matrices import DirectedEdge, directed_arcs
    from model import Graph

from .graph_items import EDGE_PEN, NodeGraphicsItem


HARPOON_BRUSH = QBrush(EDGE_PEN.color())
HARPOON_OUTLINE_PEN = QPen(QColor("#2d3e5b"), 1.25)


class HarpoonGraphicsItem(QGraphicsPathItem):
    """A right-side straight harpoon representing one numbered edge arc."""

    LANE_OFFSET = 3.5
    SHAFT_HALF_WIDTH = 2.5
    BARB_LENGTH = 25.0
    BARB_HEIGHT = 12.0
    LABEL_PADDING = 2.0

    def __init__(self, harpoon: DirectedEdge, graph: Graph) -> None:
        super().__init__()
        self.harpoon = harpoon
        self.setPen(HARPOON_OUTLINE_PEN)
        self.setBrush(HARPOON_BRUSH)
        self.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self.setZValue(-1)
        source = graph.get_node(harpoon.source)
        target = graph.get_node(harpoon.target)
        self.setToolTip(f"Arc {harpoon.index}: {source.label} → {target.label}")

        # This is deliberately a top-level scene item.  A child label may be
        # painted below a later sibling harpoon where arcs cross.
        self.label = QGraphicsSimpleTextItem(str(harpoon.index))
        font = QFont(QApplication.font())
        font.setBold(True)
        font.setPointSize(max(10, font.pointSize() + 1))
        self.label.setFont(font)
        self.label.setBrush(QApplication.palette().brush(QPalette.ColorRole.Text))
        self.label.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self.label.setToolTip(self.toolTip())
        self.label.setZValue(2)

        self.direction = QPointF()
        self.right_normal = QPointF()
        self.shaft_start = QPointF()
        self.arrow_tip = QPointF()
        self.label_anchor = QPointF()
        self._set_geometry(QPointF(source.x, source.y), QPointF(target.x, target.y))

    def _set_geometry(self, source: QPointF, target: QPointF) -> None:
        delta = target - source
        distance = math.hypot(delta.x(), delta.y())
        node_radius = NodeGraphicsItem.RADIUS + 1
        if distance <= 2 * node_radius + self.BARB_LENGTH:
            # Coincident, overlapping, or very close nodes have no exposed
            # space for a readable harpoon.
            self.hide()
            self.label.hide()
            return

        self.show()
        self.label.show()
        self.direction = delta / distance
        # Qt's positive y-axis points down. This is the clockwise (right-hand)
        # normal in screen space: an eastbound harpoon sits below its edge and
        # a westbound one sits above it.
        self.right_normal = QPointF(-self.direction.y(), self.direction.x())

        lane_offset = self.LANE_OFFSET
        travel = math.sqrt(node_radius**2 - lane_offset**2)
        self.shaft_start = (
            source + self.right_normal * lane_offset + self.direction * travel
        )
        self.arrow_tip = (
            target + self.right_normal * lane_offset - self.direction * travel
        )
        barb_base = self.arrow_tip - self.direction * self.BARB_LENGTH

        # Fit the visible glyphs, excluding the font's unused line spacing.
        # Labels stay upright; project their ink bounds onto the shaft axes
        # so diagonal and vertical bumps still contain the entire number.
        metrics = QFontMetricsF(self.label.font())
        label_bounds = metrics.tightBoundingRect(self.label.text()).translated(
            0, metrics.ascent()
        )
        crown_width = (
            abs(self.direction.x()) * label_bounds.width()
            + abs(self.direction.y()) * label_bounds.height()
            + 2 * self.LABEL_PADDING
        )
        bump_height = (
            abs(self.right_normal.x()) * label_bounds.width()
            + abs(self.right_normal.y()) * label_bounds.height()
            + 2 * self.LABEL_PADDING
        )
        shoulder_width = bump_height * 0.4
        bump_length = crown_width + 2 * shoulder_width
        usable_shaft = math.hypot(
            barb_base.x() - self.shaft_start.x(),
            barb_base.y() - self.shaft_start.y(),
        )
        if usable_shaft <= bump_length + self.SHAFT_HALF_WIDTH * 2:
            self.hide()
            self.label.hide()
            return

        bump_center = (self.shaft_start + barb_base) / 2
        near_edge = self.right_normal * self.SHAFT_HALF_WIDTH
        far_edge = -near_edge

        def bump_point(along: float, outward: float) -> QPointF:
            return (
                bump_center + near_edge
                + self.direction * along + self.right_normal * outward
            )

        half_crown = crown_width / 2
        half_bump = bump_length / 2
        crown_rounding = self.LABEL_PADDING

        # Follow the two parallel sides of the shaft explicitly. Connecting
        # the tail directly to the barb would taper the whole shaft. The tip
        # continues the inner side; a single swept-back barb projects outward,
        # matching a harpoon rather than a symmetric arrowhead.
        path = QPainterPath(self.shaft_start + far_edge)
        path.lineTo(self.arrow_tip + far_edge)
        path.lineTo(
            barb_base + self.right_normal * (self.SHAFT_HALF_WIDTH + self.BARB_HEIGHT)
        )
        path.lineTo(
            self.arrow_tip - self.direction * (self.BARB_LENGTH * 0.9) + near_edge
        )
        # Smooth shoulders and a gently domed crown keep the label integrated
        # into the shaft, with just enough room around the visible digits.
        path.lineTo(bump_point(half_bump, 0))
        path.cubicTo(
            bump_point(half_bump - shoulder_width / 2, 0),
            bump_point(half_crown + shoulder_width / 2, bump_height - crown_rounding),
            bump_point(half_crown, bump_height),
        )
        path.cubicTo(
            bump_point(half_crown - shoulder_width / 2, bump_height + crown_rounding),
            bump_point(-half_crown + shoulder_width / 2, bump_height + crown_rounding),
            bump_point(-half_crown, bump_height),
        )
        path.cubicTo(
            bump_point(-half_crown - shoulder_width / 2, bump_height - crown_rounding),
            bump_point(-half_bump + shoulder_width / 2, 0),
            bump_point(-half_bump, 0),
        )
        path.lineTo(self.shaft_start + near_edge)
        path.closeSubpath()
        self.setPath(path)

        self.label_anchor = bump_center + self.right_normal * (
            self.SHAFT_HALF_WIDTH + bump_height / 2
        )
        self.label.setPos(self.label_anchor - label_bounds.center())


class DirectedArcScene(QGraphicsScene):
    """A read-only arc representation; the graph itself is never changed."""

    def __init__(self, graph: Graph, parent=None) -> None:
        super().__init__(parent)
        self.graph = graph
        self.arcs: tuple[DirectedEdge, ...] = ()
        self.arc_items: list[HarpoonGraphicsItem] = []
        self.label_items: list[QGraphicsSimpleTextItem] = []
        self.node_items: dict[int, NodeGraphicsItem] = {}

    def rebuild_from_graph(self) -> None:
        """Refresh the derived arrows and labels from the current graph."""

        self.clear()
        self.arc_items.clear()
        self.label_items.clear()
        self.node_items.clear()
        self.arcs = directed_arcs(self.graph)
        for arc in self.arcs:
            item = HarpoonGraphicsItem(arc, self.graph)
            self.addItem(item)
            self.arc_items.append(item)
        for node in self.graph.nodes:
            circle = NodeGraphicsItem(node.id, node.x, node.y)
            circle.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
            self.addItem(circle)
            self.node_items[node.id] = circle
        for item in self.arc_items:
            self.addItem(item.label)
            self.label_items.append(item.label)

    def contextMenuEvent(self, event) -> None:
        """Keep editing commands out of the inspection view."""

        event.ignore()
