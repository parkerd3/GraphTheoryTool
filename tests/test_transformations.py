import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from GraphTheoryTool.view.graph_scene import GraphScene


def get_qapplication() -> QApplication:
    return QApplication.instance() or QApplication([])


def make_selected_pair() -> GraphScene:
    get_qapplication()
    scene = GraphScene()
    first = scene.graph.add_node(100, 100)
    second = scene.graph.add_node(300, 100)
    scene.add_node_visual(first)
    scene.add_node_visual(second)
    edge = scene.graph.add_edge(first.id, second.id)
    scene.add_edge_visual(edge)

    scene.selected_nodes = {first.id, second.id}
    scene._synchronize_selected_edges()
    scene._refresh_selection_visuals()
    scene.mode = "select"
    return scene


def test_rotation_overlay_rotates_selected_nodes_and_updates_edges() -> None:
    scene = make_selected_pair()

    scene._update_rotation_controls_hover(QPointF(200, 100))
    assert scene.rotation_controls_visible
    assert scene.rotation_guide_item is not None
    assert scene.rotation_handle_item is not None

    handle_position = scene.rotation_handle_item.rect().center()
    assert scene._rotation_handle_at(handle_position)
    scene._begin_rotation_drag(handle_position)

    # The initial handle is above the center. Moving it to the right rotates
    # the selected pair a quarter turn clockwise.
    scene._update_rotation(QPointF(340, 100))
    scene.finish_rotation_drag()

    first = scene.graph.get_node(0)
    second = scene.graph.get_node(1)
    assert first.x == 200
    assert first.y == 0
    assert second.x == 200
    assert second.y == 200
    assert scene.edge_items[(0, 1)].line().p1() == QPointF(200, 0)
    assert scene.edge_items[(0, 1)].line().p2() == QPointF(200, 200)
    assert not scene.rotation_controls_visible
    assert not scene.is_rotating


def test_rotation_is_one_undoable_edit() -> None:
    scene = make_selected_pair()
    scene._update_rotation_controls_hover(QPointF(200, 100))
    handle_position = scene.rotation_handle_item.rect().center()
    scene._begin_rotation_drag(handle_position)
    scene._update_rotation(QPointF(340, 100))
    scene.finish_rotation_drag()

    assert scene.undo()
    first = scene.graph.get_node(0)
    second = scene.graph.get_node(1)
    assert (first.x, first.y) == (100, 100)
    assert (second.x, second.y) == (300, 100)


def test_clicking_the_rotation_circle_moves_the_selected_group() -> None:
    scene = make_selected_pair()
    scene._update_rotation_controls_hover(QPointF(200, 100))
    scene._begin_control_move(QPointF(200, 100))
    scene._update_node_move(QPointF(240, 130))
    scene.stop_moving_nodes()
    scene.hide_rotation_controls()

    first = scene.graph.get_node(0)
    second = scene.graph.get_node(1)
    assert (first.x, first.y) == (140, 130)
    assert (second.x, second.y) == (340, 130)


def test_single_node_selection_does_not_show_rotation_controls() -> None:
    scene = GraphScene()
    node = scene.graph.add_node(100, 100)
    scene.add_node_visual(node)
    scene.mode = "select"
    scene.selected_nodes = {node.id}

    scene._update_rotation_controls_hover(QPointF(100, 100))

    assert not scene.rotation_controls_visible


def test_context_menu_requires_a_selected_target() -> None:
    scene = make_selected_pair()

    assert scene._context_target_is_selected(QPointF(100, 100))
    assert scene._context_target_is_selected(QPointF(200, 100))
    assert not scene._context_target_is_selected(QPointF(700, 700))

    scene.clear_selection()
    assert not scene._context_target_is_selected(QPointF(100, 100))


def test_hovering_over_a_real_selection_center_reveals_controls() -> None:
    app = get_qapplication()
    from GraphTheoryTool.view.main_window import MainWindow

    window = MainWindow()
    window.show()
    scene = window.scene
    first = scene.graph.add_node(500, 500)
    second = scene.graph.add_node(700, 500)
    scene.add_node_visual(first)
    scene.add_node_visual(second)
    window.set_canvas_mode("select")
    scene.selected_nodes = {first.id, second.id}
    scene._refresh_selection_visuals()
    app.processEvents()

    center = window.canvas.mapFromScene(QPointF(600, 500))
    QTest.mouseMove(window.canvas.viewport(), center, 100)

    assert scene.rotation_controls_visible
    window.close()
