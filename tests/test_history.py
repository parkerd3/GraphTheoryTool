import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from GraphTheoryTool.model import Graph, HistoryManager
from GraphTheoryTool.view.main_window import MainWindow
from GraphTheoryTool.view.graph_scene import GraphScene


def get_qapplication() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_history_manager_undoes_and_redoes_graph_edits() -> None:
    graph = Graph()
    history = HistoryManager()

    history.begin_edit(graph)
    graph.add_node(100, 200)
    history.commit_edit(graph)

    assert history.can_undo
    assert not history.can_redo
    assert history.undo(graph)
    assert len(graph.nodes) == 0
    assert history.can_redo
    assert history.redo(graph)
    assert len(graph.nodes) == 1


def test_scene_undo_and_redo_rebuild_graphics() -> None:
    get_qapplication()
    scene = GraphScene()

    scene._handle_pen_click(QPointF(100, 100))
    assert len(scene.graph.nodes) == 1
    assert len(scene.node_items) == 1

    assert scene.undo()
    assert len(scene.graph.nodes) == 0
    assert len(scene.node_items) == 0

    assert scene.redo()
    assert len(scene.graph.nodes) == 1
    assert len(scene.node_items) == 1


def test_eraser_drag_is_one_history_entry() -> None:
    get_qapplication()
    scene = GraphScene()
    first = scene.graph.add_node(100, 100)
    second = scene.graph.add_node(300, 100)
    scene.add_node_visual(first)
    scene.add_node_visual(second)

    scene.history.begin_edit(scene.graph)
    scene._handle_eraser_click(QPointF(100, 100))
    scene._handle_eraser_click(QPointF(300, 100))
    scene.history.commit_edit(scene.graph)

    assert len(scene.graph.nodes) == 0
    assert scene.undo()
    assert len(scene.graph.nodes) == 2
    assert len(scene.node_items) == 2


def test_main_window_registers_requested_shortcuts() -> None:
    get_qapplication()
    window = MainWindow()

    assert window.undo_action.shortcut().toString() == "Ctrl+Z"
    assert window.redo_action.shortcut().toString() == "Ctrl+Shift+Z"
    assert window.undo_button.toolTip().startswith("Undo")
    assert window.redo_button.toolTip().startswith("Redo")
    window.close()


def test_switching_away_from_select_clears_selection() -> None:
    get_qapplication()
    window = MainWindow()
    scene = window.scene
    node = scene.graph.add_node(100, 100)
    scene.add_node_visual(node)

    window.set_canvas_mode("select")
    scene._handle_select_click(QPointF(100, 100), Qt.KeyboardModifier.NoModifier)
    assert scene.selected_nodes == {node.id}

    window.set_canvas_mode("eraser")
    assert scene.selected_nodes == set()
    assert scene.selected_edges == set()
    window.close()


def test_separate_eraser_clicks_undo_separately() -> None:
    app = get_qapplication()
    window = MainWindow()
    window.show()
    scene = window.scene
    first = scene.graph.add_node(100, 100)
    second = scene.graph.add_node(300, 100)
    scene.add_node_visual(first)
    scene.add_node_visual(second)
    window.set_canvas_mode("eraser")
    app.processEvents()

    first_point = window.canvas.mapFromScene(QPointF(100, 100))
    second_point = window.canvas.mapFromScene(QPointF(300, 100))
    QTest.mouseClick(
        window.canvas.viewport(),
        Qt.MouseButton.LeftButton,
        pos=first_point,
    )
    QTest.mouseClick(
        window.canvas.viewport(),
        Qt.MouseButton.LeftButton,
        pos=second_point,
    )

    assert len(scene.graph.nodes) == 0
    assert scene.undo()
    assert [node.id for node in scene.graph.nodes] == [second.id]
    assert scene.undo()
    assert [node.id for node in scene.graph.nodes] == [first.id, second.id]
    window.close()
