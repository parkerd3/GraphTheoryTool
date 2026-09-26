import math
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF, Qt
from PySide6.QtWidgets import QApplication

from GraphTheoryTool.view.graph_scene import GraphScene
from GraphTheoryTool.view.main_window import MainWindow


def get_qapplication() -> QApplication:
    return QApplication.instance() or QApplication([])


def add_nodes(scene: GraphScene, positions: list[tuple[float, float]]):
    nodes = []
    for x, y in positions:
        node = scene.graph.add_node(x, y)
        scene.add_node_visual(node)
        nodes.append(node)
    return nodes


def test_edit_tool_replaces_the_separate_pen_button() -> None:
    get_qapplication()
    window = MainWindow()

    assert set(window.tool_buttons) == {"select", "eraser", "hand"}
    assert window.scene.mode == "select"
    assert "create nodes" in window.tool_buttons["select"].toolTip()
    window.close()


def test_shift_hover_shows_translucent_node_preview_and_releases_cleanly() -> None:
    get_qapplication()
    scene = GraphScene()
    scene.set_labels_visible(True)
    preview_position = QPointF(240, 180)

    scene.handle_hover_position(
        preview_position,
        Qt.KeyboardModifier.ShiftModifier,
    )

    assert scene.shift_creation_preview_visible
    assert scene.shift_creation_preview_node is not None
    assert scene.shift_creation_preview_label is not None
    assert scene.shift_creation_preview_label.toPlainText() == "1"
    assert not scene.shift_creation_preview_edges
    assert math.isclose(scene.shift_creation_preview_node.opacity(), 0.45)
    assert math.isclose(scene.shift_creation_preview_label.opacity(), 0.45)
    assert scene.shift_creation_preview_node.rect().center() == preview_position
    assert not scene.node_items

    scene.handle_modifier_change(Qt.KeyboardModifier.NoModifier)

    assert not scene.shift_creation_preview_visible
    assert scene.shift_creation_preview_node is None
    assert scene.shift_creation_preview_label is None
    assert not scene.shift_creation_preview_edges


def test_shift_click_blank_creates_node_and_connects_all_selected_nodes() -> None:
    get_qapplication()
    scene = GraphScene()
    source_nodes = add_nodes(
        scene,
        [(100, 100), (100, 300), (300, 100), (300, 300)],
    )
    scene.selected_nodes = {node.id for node in source_nodes}
    scene._refresh_selection_visuals()
    new_position = QPointF(500, 200)

    scene.handle_hover_position(new_position, Qt.KeyboardModifier.ShiftModifier)

    assert scene.shift_creation_preview_node is not None
    assert len(scene.shift_creation_preview_edges) == len(source_nodes)
    assert all(math.isclose(item.opacity(), 0.45) for item in scene.shift_creation_preview_edges)

    assert scene._commit_shift_creation(new_position)

    assert len(scene.graph.nodes) == 5
    assert len(scene.graph.edges) == 4
    new_node = scene.graph.nodes[-1]
    assert (new_node.x, new_node.y) == (500, 200)
    assert scene.selected_nodes == {node.id for node in scene.graph.nodes}
    assert scene.selected_edges == {
        scene._edge_key(node.id, new_node.id) for node in source_nodes
    }
    assert not scene.shift_creation_preview_visible

    assert scene.undo()
    assert len(scene.graph.nodes) == 4
    assert len(scene.graph.edges) == 0


def test_shift_click_existing_node_skips_duplicate_edges() -> None:
    get_qapplication()
    scene = GraphScene()
    first, second, target = add_nodes(
        scene,
        [(100, 100), (100, 300), (400, 200)],
    )
    existing_edge = scene.graph.add_edge(first.id, target.id)
    scene.add_edge_visual(existing_edge)
    scene.selected_nodes = {first.id, second.id}
    scene._synchronize_selected_edges()
    scene._refresh_selection_visuals()

    scene.handle_hover_position(
        QPointF(target.x, target.y),
        Qt.KeyboardModifier.ShiftModifier,
    )

    assert len(scene.shift_creation_preview_edges) == 1
    preview_edge = scene.shift_creation_preview_edges[0]
    assert (preview_edge.source, preview_edge.target) == (second.id, target.id)

    assert scene._commit_shift_creation(QPointF(target.x, target.y))

    assert len(scene.graph.edges) == 2
    assert scene.graph.has_edge(first.id, target.id)
    assert scene.graph.has_edge(second.id, target.id)
    assert scene.selected_nodes == {first.id, second.id, target.id}
    assert scene.selected_edges == {
        scene._edge_key(first.id, target.id),
        scene._edge_key(second.id, target.id),
    }
    assert len({scene._edge_key(edge.source, edge.target) for edge in scene.graph.edges}) == 2

    assert scene.undo()
    assert len(scene.graph.edges) == 1
    assert scene.redo()
    assert len(scene.graph.edges) == 2
