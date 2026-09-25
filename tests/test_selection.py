import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF, Qt
from PySide6.QtWidgets import QApplication

from GraphTheoryTool.view.graph_scene import GraphScene


def get_qapplication() -> QApplication:
    """Return the shared Qt application used by the scene tests."""

    return QApplication.instance() or QApplication([])


def test_node_selection_and_ctrl_toggle() -> None:
    get_qapplication()
    scene = GraphScene()
    first = scene.graph.add_node(100, 100)
    second = scene.graph.add_node(300, 100)
    scene.add_node_visual(first)
    scene.add_node_visual(second)

    scene._handle_select_click(QPointF(100, 100), Qt.KeyboardModifier.NoModifier)
    assert scene.selected_nodes == {first.id}

    scene._handle_select_click(
        QPointF(300, 100),
        Qt.KeyboardModifier.ControlModifier,
    )
    assert scene.selected_nodes == {first.id, second.id}

    scene._handle_select_click(
        QPointF(100, 100),
        Qt.KeyboardModifier.ControlModifier,
    )
    assert scene.selected_nodes == {second.id}


def test_edges_follow_selected_endpoints() -> None:
    get_qapplication()
    scene = GraphScene()
    first = scene.graph.add_node(100, 100)
    second = scene.graph.add_node(300, 100)
    scene.add_node_visual(first)
    scene.add_node_visual(second)
    edge = scene.graph.add_edge(first.id, second.id)
    scene.add_edge_visual(edge)

    scene._handle_select_click(QPointF(100, 100), Qt.KeyboardModifier.NoModifier)
    scene._handle_select_click(
        QPointF(300, 100),
        Qt.KeyboardModifier.ControlModifier,
    )
    assert scene.selected_edges == {(first.id, second.id)}

    scene._handle_select_click(
        QPointF(100, 100),
        Qt.KeyboardModifier.ControlModifier,
    )
    assert scene.selected_edges == set()


def test_blank_click_clears_selection() -> None:
    get_qapplication()
    scene = GraphScene()
    node = scene.graph.add_node(100, 100)
    scene.add_node_visual(node)
    scene._handle_select_click(QPointF(100, 100), Qt.KeyboardModifier.NoModifier)

    scene._handle_select_click(QPointF(600, 600), Qt.KeyboardModifier.NoModifier)

    assert scene.selected_nodes == set()
    assert scene.selected_edges == set()
