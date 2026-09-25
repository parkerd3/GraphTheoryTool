"""Initial graph canvas.

The scene is intentionally small for the first milestone.  Node and edge
graphics will be added after the model and window shell are in place.
"""
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtWidgets import (
    QGraphicsScene,
    QGraphicsRectItem,
    QGraphicsTextItem,
    QGraphicsSceneMouseEvent,
)

from .graph_items import (
    EdgeGraphicsItem,
    NodeGraphicsItem,
    NODE_BRUSH,
    SELECTION_RECT_BRUSH,
    SELECTION_RECT_PEN,
)

try:
    from ..model import Graph, HistoryManager
except ImportError:  # Supports launching with ``python main.py``.
    from model import Graph, HistoryManager


class GraphScene(QGraphicsScene):
    """Scene that will display and edit a :class:`Graph`."""

    def __init__(self, graph: Graph | None = None, parent=None) -> None:
        super().__init__(parent)
        self.graph = graph or Graph()
        self.history = HistoryManager()
        self.mode = "pen"
        self.labels_visible = False
        self.selected_node_id: int | None = None
        self.is_erasing = False
        self.selected_nodes: set[int] = set()
        self.selected_edges: set[tuple[int, int]] = set()
        self.manually_deselected_edges: set[tuple[int, int]] = set()
        self.is_selecting_rect = False
        self.selection_start: QPointF | None = None
        self.selection_rect_item: QGraphicsRectItem | None = None
        self.selection_rect_ctrl = False
        self.is_moving_nodes = False
        self.move_last_position: QPointF | None = None
        self.moving_node_ids: set[int] = set()
        self.node_items = {}
        self.edge_items = {}
        self.setSceneRect(0, 0, 1200, 800)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            position = event.scenePos()

            if self.mode == "pen":
                self._handle_pen_click(position)
            elif self.mode == "eraser":
                self.history.begin_edit(self.graph)
                self._handle_eraser_click(position)
                self.is_erasing = True
                event.accept()
                return
            elif self.mode == "select":
                if self._begin_selection_rectangle(position, event.modifiers()):
                    event.accept()
                    return
                if self._begin_node_move(position, event.modifiers()):
                    event.accept()
                    return
                self._handle_select_click(position, event.modifiers())

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        """Erase elements crossed while the left mouse button is held."""

        if self.mode == "select" and self.is_moving_nodes:
            if event.buttons() & Qt.MouseButton.LeftButton:
                self._update_node_move(event.scenePos())
                event.accept()
                return

            self.stop_moving_nodes()

        if self.mode == "select" and self.is_selecting_rect:
            if event.buttons() & Qt.MouseButton.LeftButton:
                self._update_selection_rectangle(event.scenePos())
                event.accept()
                return

        if self.mode == "eraser" and self.is_erasing:
            if event.buttons() & Qt.MouseButton.LeftButton:
                self._handle_eraser_click(event.scenePos())
                event.accept()
                return

            self.is_erasing = False
            self.history.commit_edit(self.graph)

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        """End an erasing gesture when the left button is released."""

        if event.button() == Qt.MouseButton.LeftButton:
            if self.mode == "select" and self.is_moving_nodes:
                self.stop_moving_nodes()
                event.accept()
                return

            if self.mode == "select" and self.is_selecting_rect:
                self._finish_selection_rectangle(event.scenePos())
                event.accept()
                return

            self.is_erasing = False
            self.history.commit_edit(self.graph)

        super().mouseReleaseEvent(event)

    def stop_erasing(self) -> None:
        """Cancel any active erasing gesture."""

        was_erasing = self.is_erasing
        self.is_erasing = False
        if was_erasing:
            self.history.commit_edit(self.graph)

    def _begin_node_move(self, position, modifiers) -> bool:
        """Begin moving the selected node group when a node is pressed."""

        if modifiers & Qt.KeyboardModifier.ControlModifier:
            return False

        node_id = self._node_id_at(position)
        if node_id is None:
            return False

        if node_id not in self.selected_nodes:
            self.selected_nodes = {node_id}
            self.manually_deselected_edges.clear()
            self._synchronize_selected_edges()
            self._refresh_selection_visuals()

        self.is_moving_nodes = True
        self.move_last_position = QPointF(position)
        self.moving_node_ids = set(self.selected_nodes)
        self.history.begin_edit(self.graph)
        return True

    def _update_node_move(self, position) -> None:
        """Move selected nodes by the cursor's scene-coordinate delta."""

        if self.move_last_position is None:
            return

        delta_x = position.x() - self.move_last_position.x()
        delta_y = position.y() - self.move_last_position.y()
        if delta_x == 0 and delta_y == 0:
            return

        for node_id in self.moving_node_ids:
            node = self.graph.get_node(node_id)
            node.x += delta_x
            node.y += delta_y
            items = self.node_items.get(node_id)
            if items is None:
                continue
            items["circle"].set_center(node.x, node.y)
            self._center_label(node, items["label"])

        self._refresh_edge_positions()
        self.move_last_position = QPointF(position)

    def _refresh_edge_positions(self) -> None:
        """Update every edge line from the current model coordinates."""

        for edge_item in self.edge_items.values():
            source = self.graph.get_node(edge_item.source)
            target = self.graph.get_node(edge_item.target)
            edge_item.set_endpoints(
                source.x,
                source.y,
                target.x,
                target.y,
            )

    def stop_moving_nodes(self) -> None:
        """Finish a node movement transaction and preserve its selection."""

        if not self.is_moving_nodes:
            return

        self.is_moving_nodes = False
        self.move_last_position = None
        self.moving_node_ids.clear()
        self.history.commit_edit(self.graph)

    def _begin_selection_rectangle(self, position, modifiers) -> bool:
        """Begin a rectangle only when the press starts on blank canvas."""

        if self._node_id_at(position) is not None:
            return False
        if self._edge_key_at(position) is not None:
            return False

        self.is_selecting_rect = True
        self.selection_start = QPointF(position)
        self.selection_rect_ctrl = bool(
            modifiers & Qt.KeyboardModifier.ControlModifier
        )

        self.selection_rect_item = QGraphicsRectItem(
            QRectF(self.selection_start, self.selection_start)
        )
        self.selection_rect_item.setPen(SELECTION_RECT_PEN)
        self.selection_rect_item.setBrush(SELECTION_RECT_BRUSH)
        self.selection_rect_item.setZValue(10)
        self.addItem(self.selection_rect_item)
        return True

    def _update_selection_rectangle(self, position) -> None:
        """Resize the temporary rectangle to the current mouse position."""

        if self.selection_start is None or self.selection_rect_item is None:
            return

        rectangle = QRectF(self.selection_start, position).normalized()
        self.selection_rect_item.setRect(rectangle)

    def _finish_selection_rectangle(self, position) -> None:
        """Apply the rectangle selection and remove its temporary graphic."""

        if self.selection_start is None:
            self.cancel_selection_rectangle()
            return

        rectangle = QRectF(self.selection_start, position).normalized()
        ctrl_held = self.selection_rect_ctrl
        self.cancel_selection_rectangle()

        if rectangle.width() < 3 and rectangle.height() < 3:
            if not ctrl_held:
                self.clear_selection()
            return

        self._apply_rectangle_selection(rectangle, ctrl_held)

    def _apply_rectangle_selection(self, rectangle: QRectF, ctrl_held: bool) -> None:
        """Select nodes whose small center hitboxes fit inside the rectangle."""

        nodes_in_rectangle = {
            node.id
            for node in self.graph.nodes
            if rectangle.contains(self._node_selection_hitbox(node))
        }

        if ctrl_held:
            for node_id in nodes_in_rectangle:
                if node_id in self.selected_nodes:
                    self.selected_nodes.remove(node_id)
                else:
                    self.selected_nodes.add(node_id)
        else:
            self.selected_nodes = nodes_in_rectangle
            self.manually_deselected_edges.clear()

        self._synchronize_selected_edges()
        self._refresh_selection_visuals()

    @staticmethod
    def _node_selection_hitbox(node) -> QRectF:
        """Return a modest hitbox around a node center for rectangle selection."""

        radius = 12
        return QRectF(
            node.x - radius,
            node.y - radius,
            radius * 2,
            radius * 2,
        )

    def cancel_selection_rectangle(self) -> None:
        """Remove an active selection rectangle without changing selection."""

        if self.selection_rect_item is not None:
            self.removeItem(self.selection_rect_item)
        self.selection_rect_item = None
        self.selection_start = None
        self.selection_rect_ctrl = False
        self.is_selecting_rect = False

    def _handle_pen_click(self, position) -> None:
        """Create nodes or connect two nodes according to the Pen workflow."""

        node_id = self._node_id_at(position)

        if node_id is None:
            if self.selected_node_id is not None:
                self.clear_selected_node()
            else:
                self._execute_edit(lambda: self._create_node(position))
        elif self.selected_node_id is None:
            self.select_node(node_id)
        elif self.selected_node_id == node_id:
            self.clear_selected_node()
        else:
            source_id = self.selected_node_id
            try:
                self._execute_edit(
                    lambda: self._create_edge(source_id, node_id)
                )
            except ValueError as error:
                print(error)
            finally:
                self.clear_selected_node()

    def _execute_edit(self, edit) -> None:
        """Run one graph edit, or join it to an existing edit transaction."""

        started_here = not self.history.has_pending_edit
        if started_here:
            self.history.begin_edit(self.graph)

        try:
            edit()
        except Exception:
            if started_here:
                self.history.cancel_edit()
            raise
        else:
            if started_here:
                self.history.commit_edit(self.graph)

    def _create_node(self, position) -> None:
        node = self.graph.add_node(position.x(), position.y())
        self.add_node_visual(node)
        print(
            f"New node created with ID {node.id}, label {node.label}, "
            f"at position ({node.x}, {node.y})"
        )

    def _create_edge(self, source: int, target: int) -> None:
        edge = self.graph.add_edge(source, target)
        self.add_edge_visual(edge)

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

        self._execute_edit(lambda: self._delete_edge_now(source, target))

    def _delete_edge_now(self, source: int, target: int) -> None:
        """Perform edge deletion without opening a history transaction."""

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

        self._execute_edit(lambda: self._delete_node_now(node_id))

    def _delete_node_now(self, node_id: int) -> None:
        """Perform node deletion without opening a history transaction."""

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

    def delete_selection(self) -> bool:
        """Delete selected nodes, or selected edges when no nodes are selected."""

        if self.selected_nodes:
            return self.delete_selected_nodes()
        return self.delete_selected_edges_only()

    def delete_selected_nodes(self) -> bool:
        """Delete selected nodes and every edge incident to them."""

        node_ids = tuple(self.selected_nodes)
        if not node_ids:
            return False

        def delete_nodes() -> None:
            for node_id in node_ids:
                if node_id in self.node_items:
                    self._delete_node_now(node_id)
            self.clear_selection()

        self._execute_edit(delete_nodes)
        return True

    def delete_selected_edges_only(self) -> bool:
        """Delete selected edges while preserving their endpoint nodes."""

        edge_keys = tuple(self.selected_edges)
        if not edge_keys:
            return False

        def delete_edges() -> None:
            for source, target in edge_keys:
                if self._edge_key(source, target) in self.edge_items:
                    self._delete_edge_now(source, target)
            self.clear_selection()

        self._execute_edit(delete_edges)
        return True

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

    def rebuild_from_graph(self) -> None:
        """Recreate all graphics from the current graph model."""

        self.cancel_selection_rectangle()
        self.clear()
        self.node_items.clear()
        self.edge_items.clear()

        for node in self.graph.nodes:
            self.add_node_visual(node)
        for edge in self.graph.edges:
            self.add_edge_visual(edge)

    def undo(self) -> bool:
        """Undo the most recent graph edit and rebuild the scene."""

        self.stop_erasing()
        self.cancel_selection_rectangle()
        if not self.history.undo(self.graph):
            return False

        self.selected_node_id = None
        self.clear_selection()
        self.rebuild_from_graph()
        return True

    def redo(self) -> bool:
        """Redo the most recently undone graph edit and rebuild the scene."""

        self.stop_erasing()
        self.cancel_selection_rectangle()
        if not self.history.redo(self.graph):
            return False

        self.selected_node_id = None
        self.clear_selection()
        self.rebuild_from_graph()
        return True

    @staticmethod
    def _edge_key(source: int, target: int) -> tuple[int, int]:
        """Return a consistent key for an undirected edge."""

        return tuple(sorted((source, target)))

    def set_labels_visible(self, visible: bool) -> None:
        """Show or hide every node label currently in the scene."""

        self.labels_visible = visible
        for items in self.node_items.values():
            items["label"].setVisible(visible)
