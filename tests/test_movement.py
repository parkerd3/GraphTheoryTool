import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF, Qt
from PySide6.QtWidgets import QApplication

from GraphTheoryTool.view.graph_scene import GraphScene


def get_qapplication() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_group_move_updates_nodes_edges_and_preserves_selection() -> None:
    get_qapplication()
    scene = GraphScene()
    first = scene.graph.add_node(100, 100)
    second = scene.graph.add_node(300, 100)
    stationary = scene.graph.add_node(500, 100)
    for node in (first, second, stationary):
        scene.add_node_visual(node)

    first_edge = scene.graph.add_edge(first.id, second.id)
    second_edge = scene.graph.add_edge(second.id, stationary.id)
    scene.add_edge_visual(first_edge)
    scene.add_edge_visual(second_edge)

    scene.selected_nodes = {first.id, second.id}
    scene._synchronize_selected_edges()
    scene._refresh_selection_visuals()

    assert scene._begin_node_move(
        QPointF(first.x, first.y),
        Qt.KeyboardModifier.NoModifier,
    )
    scene._update_node_move(QPointF(150, 130))
    scene.stop_moving_nodes()

    assert (first.x, first.y) == (150, 130)
    assert (second.x, second.y) == (350, 130)
    assert (stationary.x, stationary.y) == (500, 100)
    assert scene.selected_nodes == {first.id, second.id}

    moved_edge = scene.edge_items[(second.id, stationary.id)].line()
    assert moved_edge.p1() == QPointF(350, 130)
    assert moved_edge.p2() == QPointF(500, 100)


def test_movement_is_one_undoable_edit() -> None:
    get_qapplication()
    scene = GraphScene()
    node = scene.graph.add_node(100, 100)
    scene.add_node_visual(node)
    scene.selected_nodes = {node.id}
    scene._refresh_selection_visuals()

    assert scene._begin_node_move(
        QPointF(100, 100),
        Qt.KeyboardModifier.NoModifier,
    )
    scene._update_node_move(QPointF(150, 175))
    scene.stop_moving_nodes()
    assert (node.x, node.y) == (150, 175)

    assert scene.undo()
    restored = scene.graph.get_node(node.id)
    assert (restored.x, restored.y) == (100, 100)
