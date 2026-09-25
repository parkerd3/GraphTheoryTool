import json
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF, Qt
from PySide6.QtWidgets import QApplication

from GraphTheoryTool.view.graph_scene import GraphScene
from GraphTheoryTool.view.main_window import MainWindow


def get_qapplication() -> QApplication:
    return QApplication.instance() or QApplication([])


def make_scene_with_edges() -> GraphScene:
    get_qapplication()
    scene = GraphScene()
    first = scene.graph.add_node(100, 100)
    second = scene.graph.add_node(300, 100)
    third = scene.graph.add_node(500, 100)
    for node in (first, second, third):
        scene.add_node_visual(node)

    first_edge = scene.graph.add_edge(first.id, second.id)
    second_edge = scene.graph.add_edge(second.id, third.id)
    scene.add_edge_visual(first_edge)
    scene.add_edge_visual(second_edge)
    return scene


def select_first_two_nodes(scene: GraphScene) -> None:
    scene._handle_select_click(
        QPointF(100, 100),
        Qt.KeyboardModifier.NoModifier,
    )
    scene._handle_select_click(
        QPointF(300, 100),
        Qt.KeyboardModifier.ControlModifier,
    )


def test_copy_serializes_nodes_and_only_eligible_edges() -> None:
    scene = make_scene_with_edges()
    select_first_two_nodes(scene)

    assert scene.copy_selection()
    payload = json.loads(QApplication.clipboard().text())

    assert payload["format"] == scene.CLIPBOARD_FORMAT
    assert [node["id"] for node in payload["nodes"]] == [0, 1]
    assert len(payload["edges"]) == 1
    assert {
        payload["edges"][0]["source"],
        payload["edges"][0]["target"],
    } == {0, 1}


def test_paste_creates_offset_nodes_and_reselects_new_fragment() -> None:
    scene = make_scene_with_edges()
    select_first_two_nodes(scene)
    assert scene.copy_selection()

    assert scene.paste_selection()

    assert len(scene.graph.nodes) == 5
    assert len(scene.graph.edges) == 3
    assert scene.selected_nodes == {3, 4}
    assert scene.selected_edges == {(3, 4)}

    pasted_first = scene.graph.get_node(3)
    pasted_second = scene.graph.get_node(4)
    assert (pasted_first.x, pasted_first.y) == (130, 130)
    assert (pasted_second.x, pasted_second.y) == (330, 130)

    assert scene.undo()
    assert len(scene.graph.nodes) == 3
    assert len(scene.graph.edges) == 2

    assert scene.redo()
    assert len(scene.graph.nodes) == 5
    assert len(scene.graph.edges) == 3


def test_consecutive_pastes_use_progressively_larger_offsets() -> None:
    scene = make_scene_with_edges()
    select_first_two_nodes(scene)
    assert scene.copy_selection()

    assert scene.paste_selection()
    assert scene.paste_selection()

    second_paste_first = scene.graph.get_node(5)
    second_paste_second = scene.graph.get_node(6)
    assert (second_paste_first.x, second_paste_first.y) == (160, 160)
    assert (second_paste_second.x, second_paste_second.y) == (360, 160)


def test_paste_nodes_only_does_not_recreate_edges() -> None:
    scene = make_scene_with_edges()
    select_first_two_nodes(scene)
    assert scene.copy_selection()

    assert scene.paste_nodes_only()

    assert len(scene.graph.nodes) == 5
    assert len(scene.graph.edges) == 2
    assert scene.selected_nodes == {3, 4}
    assert scene.selected_edges == set()


def test_cut_is_undoable_and_restores_the_deleted_fragment() -> None:
    scene = make_scene_with_edges()
    select_first_two_nodes(scene)

    assert scene.cut_selection()
    assert len(scene.graph.nodes) == 1
    assert len(scene.graph.edges) == 0
    assert scene.selected_nodes == set()

    assert scene.undo()
    assert len(scene.graph.nodes) == 3
    assert len(scene.graph.edges) == 2


def test_copy_cut_and_paste_actions_have_keyboard_shortcuts() -> None:
    get_qapplication()
    window = MainWindow()

    assert window.copy_action.shortcut().toString() == "Ctrl+C"
    assert window.cut_action.shortcut().toString() == "Ctrl+X"
    assert window.paste_action.shortcut().toString() == "Ctrl+V"

    window.close()
