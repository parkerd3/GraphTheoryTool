"""Graph editing scene and interaction logic.

The scene is intentionally small for the first milestone.  Node and edge
graphics will be added after the model and window shell are in place.
"""
import math
import json

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsEllipseItem,
    QGraphicsLineItem,
    QGraphicsScene,
    QGraphicsRectItem,
    QGraphicsTextItem,
    QMenu,
)

from .graph_items import (
    EdgeGraphicsItem,
    NodeGraphicsItem,
    ROTATION_CONTROL_GUIDE_BRUSH,
    ROTATION_CONTROL_GUIDE_PEN,
    ROTATION_CONTROL_HANDLE_BRUSH,
    ROTATION_CONTROL_HANDLE_PEN,
    ROTATION_CONTROL_STEM_PEN,
    SELECTION_RECT_BRUSH,
    SELECTION_RECT_PEN,
)

try:
    from ..model import Graph, HistoryManager
except ImportError:  # Supports launching with ``python main.py``.
    from model import Graph, HistoryManager


class GraphScene(QGraphicsScene):
    """Scene that will display and edit a :class:`Graph`."""

    CLIPBOARD_FORMAT = "GraphTheoryTool.fragment.v1"
    PASTE_OFFSET = (30.0, 30.0)
    ROTATION_CONTROL_HOVER_RADIUS = 42.0
    ROTATION_HANDLE_HIT_RADIUS = 12.0

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
        self._last_paste_clipboard_text: str | None = None
        self._paste_count = 0
        self.rotation_controls_visible = False
        self.is_rotating = False
        self.rotation_center: QPointF | None = None
        self.rotation_control_radius = 30.0
        self.rotation_handle_distance = 30.0
        self.rotation_handle_angle = -math.pi / 2
        self.rotation_handle_item: QGraphicsEllipseItem | None = None
        self.rotation_guide_item: QGraphicsEllipseItem | None = None
        self.rotation_handle_line_item: QGraphicsLineItem | None = None
        self.rotation_base_positions: dict[int, tuple[float, float]] = {}
        self.rotation_last_angle: float | None = None
        self.rotation_total_angle = 0.0
        self.node_items = {}
        self.edge_items = {}
        self.setSceneRect(0, 0, 1200, 800)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            position = event.scenePos()

            if self.mode == "select" and self.rotation_controls_visible:
                if self._rotation_handle_at(position):
                    self._begin_rotation_drag(position)
                    event.accept()
                    return

                if self._rotation_circle_at(position):
                    self._begin_control_move(position)
                    event.accept()
                    return

                self.hide_rotation_controls()

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

        if self.is_rotating:
            if event.buttons() & Qt.MouseButton.LeftButton:
                self._update_rotation(event.scenePos())
                event.accept()
                return

            self.finish_rotation_drag()

        if self.mode == "select" and self.is_moving_nodes:
            if event.buttons() & Qt.MouseButton.LeftButton:
                self._update_node_move(event.scenePos())
                event.accept()
                return

            self.stop_moving_nodes()
            self.hide_rotation_controls()

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

        if not event.buttons():
            self._update_rotation_controls_hover(event.scenePos())

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        """End an erasing gesture when the left button is released."""

        if event.button() == Qt.MouseButton.LeftButton:
            if self.is_rotating:
                self.finish_rotation_drag()
                event.accept()
                return

            if self.mode == "select" and self.is_moving_nodes:
                self.stop_moving_nodes()
                self.hide_rotation_controls()
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

    def contextMenuEvent(self, event) -> None:
        """Show editing commands for a currently selected graph element."""

        if not self._context_target_is_selected(event.scenePos()):
            event.ignore()
            return

        menu = QMenu()
        deselect_edges_action = menu.addAction("Deselect all edges")
        delete_edges_action = menu.addAction("Delete selected edges")
        delete_connected_action = menu.addAction("Delete all connected edges")
        menu.addSeparator()
        paste_nodes_action = menu.addAction("Paste nodes only")
        paste_nodes_action.setEnabled(self._read_clipboard_fragment() is not None)

        chosen_action = menu.exec(event.screenPos())
        if chosen_action is deselect_edges_action:
            self.deselect_all_edges()
        elif chosen_action is delete_edges_action:
            self.delete_selected_edges_only()
        elif chosen_action is delete_connected_action:
            self.delete_all_connected_edges()
        elif chosen_action is paste_nodes_action:
            self.paste_nodes_only()

        event.accept()

    def _context_target_is_selected(self, position: QPointF) -> bool:
        """Return whether a selected node or edge is under ``position``."""

        node_id = self._node_id_at(position)
        if node_id is not None:
            return node_id in self.selected_nodes

        edge_key = self._edge_key_at(position)
        return edge_key in self.selected_edges if edge_key is not None else False

    def deselect_all_edges(self) -> None:
        """Deselect selected edges without changing the selected nodes."""

        self.manually_deselected_edges.update(self.selected_edges)
        self.selected_edges.clear()
        self._refresh_selection_visuals()

    def delete_all_connected_edges(self) -> bool:
        """Delete every edge incident to at least one selected node."""

        edge_keys = tuple(
            key
            for key in self.edge_items
            if key[0] in self.selected_nodes or key[1] in self.selected_nodes
        )
        if not edge_keys:
            return False

        def delete_edges() -> None:
            for source, target in edge_keys:
                if self._edge_key(source, target) in self.edge_items:
                    self._delete_edge_now(source, target)
            self.selected_edges.clear()
            self.manually_deselected_edges.clear()
            self._refresh_selection_visuals()

        self._execute_edit(delete_edges)
        return True

    def _update_rotation_controls_hover(self, position: QPointF) -> None:
        """Show the rotation controls only while hovering near a group center."""

        if self.is_rotating or self.is_moving_nodes:
            return
        if self.mode != "select" or len(self.selected_nodes) < 2:
            self.hide_rotation_controls()
            return

        center = self._selection_center()
        if center is None:
            self.hide_rotation_controls()
            return

        distance = math.hypot(
            position.x() - center.x(),
            position.y() - center.y(),
        )
        if distance <= self.ROTATION_CONTROL_HOVER_RADIUS:
            self._show_rotation_controls(center)
        else:
            self.hide_rotation_controls()

    def _show_rotation_controls(self, center: QPointF) -> None:
        """Create or reposition the temporary rotation controls."""

        if self.rotation_controls_visible:
            self.rotation_center = center
            self._update_rotation_control_geometry()
            return

        self.rotation_center = center
        self.rotation_handle_angle = -math.pi / 2
        self.rotation_handle_distance = self.rotation_control_radius

        self.rotation_guide_item = QGraphicsEllipseItem(0, 0, 0, 0)
        self.rotation_guide_item.setPen(ROTATION_CONTROL_GUIDE_PEN)
        self.rotation_guide_item.setBrush(ROTATION_CONTROL_GUIDE_BRUSH)
        self.rotation_guide_item.setZValue(20)
        self.addItem(self.rotation_guide_item)

        self.rotation_handle_line_item = QGraphicsLineItem(0, 0, 0, 0)
        self.rotation_handle_line_item.setPen(ROTATION_CONTROL_STEM_PEN)
        self.rotation_handle_line_item.setZValue(20)
        self.addItem(self.rotation_handle_line_item)

        self.rotation_handle_item = QGraphicsEllipseItem(0, 0, 0, 0)
        self.rotation_handle_item.setPen(ROTATION_CONTROL_HANDLE_PEN)
        self.rotation_handle_item.setBrush(ROTATION_CONTROL_HANDLE_BRUSH)
        self.rotation_handle_item.setZValue(21)
        self.addItem(self.rotation_handle_item)

        self.rotation_controls_visible = True
        self._update_rotation_control_geometry()

    def _selection_center(self) -> QPointF | None:
        """Return the bounding-box center of the selected nodes."""

        nodes = [
            node for node in self.graph.nodes if node.id in self.selected_nodes
        ]
        if not nodes:
            return None

        min_x = min(node.x for node in nodes)
        max_x = max(node.x for node in nodes)
        min_y = min(node.y for node in nodes)
        max_y = max(node.y for node in nodes)
        return QPointF((min_x + max_x) / 2, (min_y + max_y) / 2)

    def _rotation_handle_at(self, position: QPointF) -> bool:
        """Return whether a scene position is inside the rotation handle."""

        if self.rotation_handle_item is None:
            return False

        center = self.rotation_handle_item.rect().center()
        return (
            math.hypot(position.x() - center.x(), position.y() - center.y())
            <= self.ROTATION_HANDLE_HIT_RADIUS
        )

    def _rotation_circle_at(self, position: QPointF) -> bool:
        """Return whether a position lies inside the small control circle."""

        if self.rotation_center is None:
            return False

        return (
            math.hypot(
                position.x() - self.rotation_center.x(),
                position.y() - self.rotation_center.y(),
            )
            <= self.rotation_control_radius
        )

    def _begin_control_move(self, position: QPointF) -> None:
        """Begin moving the selected group from the rotation control circle."""

        self.is_moving_nodes = True
        self.move_last_position = QPointF(position)
        self.moving_node_ids = set(self.selected_nodes)
        self.history.begin_edit(self.graph)

    def _begin_rotation_drag(self, position: QPointF) -> None:
        """Begin one undoable rotation gesture from the guide handle."""

        if self.rotation_center is None:
            return

        self.rotation_base_positions = {
            node.id: (node.x, node.y)
            for node in self.graph.nodes
            if node.id in self.selected_nodes
        }
        self.is_rotating = True
        self.rotation_last_angle = math.atan2(
            position.y() - self.rotation_center.y(),
            position.x() - self.rotation_center.x(),
        )
        self.rotation_total_angle = 0.0
        self.history.begin_edit(self.graph)

    def _update_rotation(self, position: QPointF) -> None:
        """Rotate the selected nodes by the cursor's angular movement."""

        if not self.is_rotating or self.rotation_center is None:
            return

        current_angle = math.atan2(
            position.y() - self.rotation_center.y(),
            position.x() - self.rotation_center.x(),
        )
        if self.rotation_last_angle is None:
            self.rotation_last_angle = current_angle
            return

        angle_delta = current_angle - self.rotation_last_angle
        if angle_delta > math.pi:
            angle_delta -= 2 * math.pi
        elif angle_delta < -math.pi:
            angle_delta += 2 * math.pi

        self.rotation_total_angle += angle_delta
        self.rotation_last_angle = current_angle
        cosine = math.cos(self.rotation_total_angle)
        sine = math.sin(self.rotation_total_angle)

        for node_id, (base_x, base_y) in self.rotation_base_positions.items():
            relative_x = base_x - self.rotation_center.x()
            relative_y = base_y - self.rotation_center.y()
            node = self.graph.get_node(node_id)
            node.x = (
                self.rotation_center.x()
                + relative_x * cosine
                - relative_y * sine
            )
            node.y = (
                self.rotation_center.y()
                + relative_x * sine
                + relative_y * cosine
            )
            items = self.node_items.get(node_id)
            if items is not None:
                items["circle"].set_center(node.x, node.y)
                self._center_label(node, items["label"])

        self._refresh_edge_positions()
        handle_distance = math.hypot(
            position.x() - self.rotation_center.x(),
            position.y() - self.rotation_center.y(),
        )
        self.rotation_handle_distance = max(
            self.rotation_control_radius,
            handle_distance,
        )
        self._update_rotation_handle(current_angle)

    def _update_rotation_handle(self, angle: float) -> None:
        """Place the rotation handle and stem at a chosen angle and distance."""

        if self.rotation_center is None or self.rotation_handle_item is None:
            return

        handle_radius = 8.0
        self.rotation_handle_angle = angle
        handle_x = self.rotation_center.x() + self.rotation_handle_distance * math.cos(angle)
        handle_y = self.rotation_center.y() + self.rotation_handle_distance * math.sin(angle)
        self.rotation_handle_item.setRect(
            handle_x - handle_radius,
            handle_y - handle_radius,
            handle_radius * 2,
            handle_radius * 2,
        )

        if self.rotation_handle_line_item is not None:
            self.rotation_handle_line_item.setLine(
                self.rotation_center.x(),
                self.rotation_center.y(),
                handle_x,
                handle_y,
            )

    def _update_rotation_control_geometry(self) -> None:
        """Keep the guide and handle centered on the selected group."""

        if self.rotation_center is None or self.rotation_guide_item is None:
            return

        radius = self.rotation_control_radius
        self.rotation_guide_item.setRect(
            self.rotation_center.x() - radius,
            self.rotation_center.y() - radius,
            radius * 2,
            radius * 2,
        )
        self._update_rotation_handle(self.rotation_handle_angle)

    def finish_rotation_drag(self) -> None:
        """Commit a rotation drag and hide its temporary controls."""

        if self.is_rotating:
            self.history.commit_edit(self.graph)
        self.is_rotating = False
        self.hide_rotation_controls()

    def cancel_rotation_drag(self) -> None:
        """Cancel a rotation drag, restoring its original node positions."""

        if self.is_rotating:
            for node_id, (x, y) in self.rotation_base_positions.items():
                node = self.graph.get_node(node_id)
                node.x = x
                node.y = y
                items = self.node_items.get(node_id)
                if items is not None:
                    items["circle"].set_center(x, y)
                    self._center_label(node, items["label"])
            self._refresh_edge_positions()
            self.history.cancel_edit()

        self.is_rotating = False
        self.hide_rotation_controls()

    def hide_rotation_controls(self) -> None:
        """Remove the temporary controls without changing the graph."""

        for item_name in (
            "rotation_guide_item",
            "rotation_handle_line_item",
            "rotation_handle_item",
        ):
            item = getattr(self, item_name)
            if item is not None:
                self.removeItem(item)
            setattr(self, item_name, None)

        self.rotation_controls_visible = False
        self.rotation_center = None
        self.rotation_handle_distance = self.rotation_control_radius
        self.rotation_handle_angle = -math.pi / 2
        self.rotation_base_positions.clear()
        self.rotation_last_angle = None
        self.rotation_total_angle = 0.0

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
        if self.rotation_controls_visible and not self.is_rotating:
            center = self._selection_center()
            if center is not None:
                self.rotation_center = center
                self._update_rotation_control_geometry()
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

        if len(self.selected_nodes) < 2:
            self.hide_rotation_controls()
        elif self.rotation_controls_visible and not self.is_rotating:
            center = self._selection_center()
            if center is not None:
                self.rotation_center = center
                self._update_rotation_control_geometry()

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

    def copy_selection(self) -> bool:
        """Copy selected nodes and eligible selected edges to the clipboard."""

        if not self.selected_nodes:
            return False

        nodes = [
            {
                "id": node.id,
                "x": node.x,
                "y": node.y,
            }
            for node in self.graph.nodes
            if node.id in self.selected_nodes
        ]

        edges = []
        for key in sorted(self.selected_edges):
            if key[0] not in self.selected_nodes or key[1] not in self.selected_nodes:
                continue
            edge = self._edge_for_key(key)
            if edge is None:
                continue
            edges.append(
                {
                    "source": edge.source,
                    "target": edge.target,
                    "weight": edge.weight,
                    "directed": edge.directed,
                }
            )

        payload = {
            "format": self.CLIPBOARD_FORMAT,
            "nodes": nodes,
            "edges": edges,
        }
        clipboard_text = json.dumps(payload)
        QApplication.clipboard().setText(clipboard_text)
        self._last_paste_clipboard_text = clipboard_text
        self._paste_count = 0
        return True

    def cut_selection(self) -> bool:
        """Copy the selection, then delete it as one undoable edit."""

        if not self.copy_selection():
            return False
        return self.delete_selection()

    def paste_selection(self) -> bool:
        """Paste a graph fragment and include its copied eligible edges."""

        return self._paste_fragment(include_edges=True)

    def paste_nodes_only(self) -> bool:
        """Paste only the nodes from the current graph fragment."""

        return self._paste_fragment(include_edges=False)

    def _paste_fragment(self, *, include_edges: bool) -> bool:
        clipboard_text = QApplication.clipboard().text()
        if clipboard_text != self._last_paste_clipboard_text:
            self._last_paste_clipboard_text = clipboard_text
            self._paste_count = 0

        fragment = self._read_clipboard_fragment(clipboard_text)
        if fragment is None or not fragment.get("nodes"):
            return False

        paste_number = self._paste_count + 1
        offset_x = self.PASTE_OFFSET[0] * paste_number
        offset_y = self.PASTE_OFFSET[1] * paste_number

        def paste() -> None:
            self.clear_selection()
            id_map: dict[int, int] = {}
            new_node_ids: list[int] = []

            for node_data in fragment["nodes"]:
                old_id = int(node_data["id"])
                node = self.graph.add_node(
                    float(node_data["x"]) + offset_x,
                    float(node_data["y"]) + offset_y,
                )
                id_map[old_id] = node.id
                new_node_ids.append(node.id)
                self.add_node_visual(node)

            new_edge_keys: set[tuple[int, int]] = set()
            if include_edges:
                for edge_data in fragment.get("edges", []):
                    source = id_map.get(int(edge_data["source"]))
                    target = id_map.get(int(edge_data["target"]))
                    if source is None or target is None:
                        continue

                    edge = self.graph.add_edge(
                        source,
                        target,
                        weight=float(edge_data.get("weight", 1.0)),
                        directed=bool(edge_data.get("directed", False)),
                    )
                    self.add_edge_visual(edge)
                    new_edge_keys.add(self._edge_key(source, target))

            self.selected_nodes = set(new_node_ids)
            self.selected_edges = new_edge_keys
            self.manually_deselected_edges.clear()
            self._refresh_selection_visuals()

        try:
            self._execute_edit(paste)
        except (KeyError, TypeError, ValueError):
            return False
        self._paste_count = paste_number
        return True

    @classmethod
    def _read_clipboard_fragment(cls, clipboard_text: str | None = None) -> dict | None:
        """Read and validate a GraphTheoryTool clipboard fragment."""

        try:
            if clipboard_text is None:
                clipboard_text = QApplication.clipboard().text()
            payload = json.loads(clipboard_text)
        except (TypeError, json.JSONDecodeError):
            return None

        if not isinstance(payload, dict):
            return None
        if payload.get("format") != cls.CLIPBOARD_FORMAT:
            return None
        if not isinstance(payload.get("nodes"), list):
            return None
        return payload

    def _edge_for_key(self, key: tuple[int, int]):
        """Return the model edge represented by an edge key."""

        return next(
            (
                edge
                for edge in self.graph.edges
                if self._edge_key(edge.source, edge.target) == key
            ),
            None,
        )

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

        self.cancel_rotation_drag()
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
        self.cancel_rotation_drag()
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
        self.cancel_rotation_drag()
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
