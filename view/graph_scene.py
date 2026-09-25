"""Initial graph canvas.

The scene is intentionally small for the first milestone.  Node and edge
graphics will be added after the model and window shell are in place.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGraphicsScene,
    QGraphicsTextItem,
    QGraphicsSceneMouseEvent,
)

from .graph_items import (
    EdgeGraphicsItem,
    NodeGraphicsItem,
    NODE_BRUSH,
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
        self.mode = "pen"
        self.labels_visible = False
        self.selected_node_id: int | None = None
        self.is_erasing = False
        self.selected_nodes: set[int] = set()
        self.selected_edges: set[tuple[int, int]] = set()
        self.manually_deselected_edges: set[tuple[int, int]] = set()
        self.node_items = {}
        self.edge_items = {}
        self.setSceneRect(0, 0, 1200, 800)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            position = event.scenePos()

            if self.mode == "pen":
                self._handle_pen_click(position)
            elif self.mode == "eraser":
                self._handle_eraser_click(position)
                self.is_erasing = True
                event.accept()
                return
            elif self.mode == "select":
                self._handle_select_click(position, event.modifiers())

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        """Erase elements crossed while the left mouse button is held."""

        if self.mode == "eraser" and self.is_erasing:
            if event.buttons() & Qt.MouseButton.LeftButton:
                self._handle_eraser_click(event.scenePos())
                event.accept()
                return

            self.is_erasing = False

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        """End an erasing gesture when the left button is released."""

        if event.button() == Qt.MouseButton.LeftButton:
            self.is_erasing = False

        super().mouseReleaseEvent(event)

    def stop_erasing(self) -> None:
        """Cancel any active erasing gesture."""

        self.is_erasing = False

    def _handle_pen_click(self, position) -> None:
        """Create nodes or connect two nodes according to the Pen workflow."""

        node_id = self._node_id_at(position)

        if node_id is None:
            if self.selected_node_id is not None:
                self.clear_selected_node()
            else:
                node = self.graph.add_node(position.x(), position.y())
                self.add_node_visual(node)
                print(
                    f"New node created with ID {node.id}, label {node.label}, "
                    f"at position ({node.x}, {node.y})"
                )
        elif self.selected_node_id is None:
            self.select_node(node_id)
        elif self.selected_node_id == node_id:
            self.clear_selected_node()
        else:
            try:
                edge = self.graph.add_edge(self.selected_node_id, node_id)
            except ValueError as error:
                print(error)
            else:
                self.add_edge_visual(edge)
            finally:
                self.clear_selected_node()

    def _handle_eraser_click(self, position) -> None:
        """Delete the node or edge under the cursor."""

        node_id = self._node_id_at(position)
        if node_id is not None:
            self.delete_node(node_id)
            return

        edge_key = self._edge_key_at(position)
        if edge_key is not None:
            self.delete_edge(*edge_key)

    def _handle_select_click(self, position, modifiers) -> None:
        """Select or toggle a node with a normal or Ctrl-click."""

        node_id = self._node_id_at(position)
        ctrl_held = bool(modifiers & Qt.KeyboardModifier.ControlModifier)

        if node_id is None:
            edge_key = self._edge_key_at(position)
            if edge_key is not None:
                self._handle_edge_selection(edge_key, ctrl_held)
                return

            if not ctrl_held:
                self.clear_selection()
            return

        if ctrl_held and node_id in self.selected_nodes:
            self.selected_nodes.remove(node_id)
        elif ctrl_held:
            self.selected_nodes.add(node_id)
        else:
            self.selected_nodes = {node_id}
            self.manually_deselected_edges.clear()

        self._synchronize_selected_edges()
        self._refresh_selection_visuals()

    def _handle_edge_selection(
        self,
        edge_key: tuple[int, int],
        ctrl_held: bool,
    ) -> None:
        """Select an edge only when both of its endpoints are selected."""

        source, target = edge_key
        endpoints_selected = (
            source in self.selected_nodes and target in self.selected_nodes
        )
        if not endpoints_selected:
            return

        if ctrl_held:
            if edge_key in self.selected_edges:
                self.selected_edges.remove(edge_key)
                self.manually_deselected_edges.add(edge_key)
            else:
                self.selected_edges.add(edge_key)
                self.manually_deselected_edges.discard(edge_key)
        else:
            self.selected_nodes = {source, target}
            self.manually_deselected_edges.clear()
            self.selected_edges = {edge_key}

        self._refresh_selection_visuals()

    def clear_selection(self) -> None:
        """Deselect every node and edge."""

        self.selected_nodes.clear()
        self.selected_edges.clear()
        self.manually_deselected_edges.clear()
        self._refresh_selection_visuals()

    def _synchronize_selected_edges(self) -> None:
        """Select every edge whose two endpoints are selected."""

        eligible_edges = {
            key
            for key in self.edge_items
            if key[0] in self.selected_nodes and key[1] in self.selected_nodes
        }
        self.manually_deselected_edges.intersection_update(eligible_edges)
        self.selected_edges = eligible_edges - self.manually_deselected_edges

    def _refresh_selection_visuals(self) -> None:
        """Apply the current selection sets to all graphics items."""

        for node_id, items in self.node_items.items():
            items["circle"].set_selected(node_id in self.selected_nodes)

        for key, edge_item in self.edge_items.items():
            edge_item.set_selected(key in self.selected_edges)

    def _node_id_at(self, position) -> int | None:
        """Return the node ID under a scene position, if there is one."""

        for item in self.items(position):
            for node_id, items in self.node_items.items():
                if item is items["circle"] or item is items["label"]:
                    return node_id
        return None

    def _edge_key_at(self, position) -> tuple[int, int] | None:
        """Return the edge key under a scene position, if there is one."""

        for item in self.items(position):
            for key, edge_item in self.edge_items.items():
                if item is edge_item:
                    return key
        return None

    def select_node(self, node_id: int) -> None:
        """Highlight a node as the first endpoint of a new edge."""

        self.clear_selected_node()
        self.selected_node_id = node_id
        self.node_items[node_id]["circle"].set_selected(True)

    def clear_selected_node(self) -> None:
        """Remove the pending edge selection, if one exists."""

        if self.selected_node_id is None:
            return

        items = self.node_items.get(self.selected_node_id)
        if items is not None:
            items["circle"].set_selected(
                self.selected_node_id in self.selected_nodes
            )
        self.selected_node_id = None

    def add_node_visual(self, node) -> None:
        circle = NodeGraphicsItem(node.id, node.x, node.y)

        label = QGraphicsTextItem(str(node.label))
        label.setDefaultTextColor(Qt.GlobalColor.black)
        label.setVisible(self.labels_visible)
        label.setData(0, node.id)

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

    def add_edge_visual(self, edge) -> None:
        """Draw an edge between the positions of its endpoint nodes."""

        source = self.graph.get_node(edge.source)
        target = self.graph.get_node(edge.target)

        line = EdgeGraphicsItem(
            edge.source,
            edge.target,
            source.x,
            source.y,
            target.x,
            target.y,
        )
        self.addItem(line)

        self.edge_items[self._edge_key(edge.source, edge.target)] = line

    def delete_edge(self, source: int, target: int) -> None:
        """Remove an edge from both the model and the scene."""

        key = self._edge_key(source, target)
        line = self.edge_items.pop(key, None)
        if line is None:
            return

        self.graph.remove_edge(source, target)
        self.selected_edges.discard(key)
        self.manually_deselected_edges.discard(key)
        self.removeItem(line)
        self._refresh_selection_visuals()

    def delete_node(self, node_id: int) -> None:
        """Remove a node, its incident edges, and its graphics."""

        if self.selected_node_id == node_id:
            self.clear_selected_node()

        incident_edges = [
            key for key in self.edge_items if node_id in key
        ]
        for source, target in incident_edges:
            self.delete_edge(source, target)

        self.graph.remove_node(node_id)
        self.selected_nodes.discard(node_id)
        items = self.node_items.pop(node_id)
        self.removeItem(items["circle"])
        self.removeItem(items["label"])
        self.refresh_node_labels()
        self._synchronize_selected_edges()
        self._refresh_selection_visuals()

    def refresh_node_labels(self) -> None:
        """Update visible label text and center labels after renumbering."""

        for node in self.graph.nodes:
            items = self.node_items.get(node.id)
            if items is None:
                continue

            label = items["label"]
            label.setPlainText(str(node.label))
            self._center_label(node, label)

    @staticmethod
    def _center_label(node, label) -> None:
        text_width = label.boundingRect().width()
        text_height = label.boundingRect().height()
        label.setPos(
            node.x - text_width / 2,
            node.y - text_height / 2,
        )

    @staticmethod
    def _edge_key(source: int, target: int) -> tuple[int, int]:
        """Return a consistent key for an undirected edge."""

        return tuple(sorted((source, target)))

    def set_labels_visible(self, visible: bool) -> None:
        """Show or hide every node label currently in the scene."""

        self.labels_visible = visible
        for items in self.node_items.values():
            items["label"].setVisible(visible)
