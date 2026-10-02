import math
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtTest import QTest
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
    scene.set_creation_mode("web")
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
    scene.set_creation_mode("web")
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


@pytest.mark.parametrize("mode", ["loop", "web", "points", "append"])
@pytest.mark.parametrize("existing_target", [False, True])
def test_creation_modes_connect_before_updating_selection(mode, existing_target) -> None:
    get_qapplication()
    scene = GraphScene()
    scene.set_creation_mode(mode)
    first, second = add_nodes(scene, [(100, 100), (100, 300)])
    scene.add_edge_visual(scene.graph.add_edge(first.id, second.id))
    sources = {first.id, second.id}
    scene.selected_nodes = sources.copy()
    scene._synchronize_selected_edges()
    target_position = QPointF(400, 200)
    if existing_target:
        target = add_nodes(scene, [(400, 200)])[0]
        scene.add_edge_visual(scene.graph.add_edge(first.id, target.id))
    before = scene.graph.to_dict()

    scene.handle_hover_position(target_position, Qt.KeyboardModifier.ShiftModifier)
    assert len(scene.shift_creation_preview_edges) == (1 if existing_target else 2)
    assert scene._commit_shift_creation(target_position)
    target = scene.graph.nodes[-1]
    assert all(scene.graph.has_edge(source_id, target.id) for source_id in sources)
    assert len(scene.graph.edges) == 3
    expected_selection = {
        "loop": {target.id},
        "web": sources | {target.id},
        "points": set(),
        "append": sources,
    }[mode]
    assert scene.selected_nodes == expected_selection
    expected_edges = {
        scene._edge_key(edge.source, edge.target) for edge in scene.graph.edges
        if edge.source in expected_selection and edge.target in expected_selection
    }
    assert scene.selected_edges == expected_edges
    assert not scene.shift_creation_preview_visible

    after = scene.graph.to_dict()
    assert scene.undo()
    assert scene.graph.to_dict() == before
    assert scene.redo()
    assert scene.graph.to_dict() == after
    assert scene.creation_mode == mode


@pytest.mark.parametrize("mode", ["loop", "web", "points", "append"])
@pytest.mark.parametrize("initial_selection", ["empty", "connected", "target_selected"])
def test_existing_targets_apply_mode_even_without_missing_connections(mode, initial_selection) -> None:
    get_qapplication()
    scene = GraphScene()
    scene.set_creation_mode(mode)
    source, target = add_nodes(scene, [(100, 100), (300, 100)])
    scene.add_edge_visual(scene.graph.add_edge(source.id, target.id))
    previous = {
        "empty": set(), "connected": {source.id},
        "target_selected": {source.id, target.id},
    }[initial_selection]
    scene.selected_nodes = previous.copy()
    scene._synchronize_selected_edges()
    before = scene.graph.to_dict()

    assert scene._commit_shift_creation(QPointF(target.x, target.y))
    assert scene.selected_nodes == {
        "loop": {target.id}, "web": previous | {target.id},
        "points": set(), "append": previous,
    }[mode]
    assert scene.graph.to_dict() == before
    assert not scene.history.can_undo
    assert not scene.history.has_pending_edit


def test_default_loop_mode_draws_a_cycle_without_accumulating_selection() -> None:
    get_qapplication()
    scene = GraphScene()
    assert scene.creation_mode == "loop"
    for x, y in [(100, 100), (300, 100), (300, 300), (100, 300)]:
        assert scene._commit_shift_creation(QPointF(x, y))
        assert scene.selected_nodes == {scene.graph.nodes[-1].id}
        assert not scene.selected_edges
    first = scene.graph.nodes[0]
    assert scene._commit_shift_creation(QPointF(first.x, first.y))
    assert len(scene.graph.nodes) == 4
    assert len(scene.graph.edges) == 4
    assert scene.selected_nodes == {first.id}
    assert not scene.selected_edges


@pytest.mark.parametrize("mode, edge_count", [("web", 6), ("points", 0), ("append", 3)])
def test_repeated_creation_uses_the_mode_selection(mode, edge_count) -> None:
    get_qapplication()
    scene = GraphScene()
    scene.set_creation_mode(mode)
    if mode == "append":
        hub = add_nodes(scene, [(100, 100)])[0]
        scene.selected_nodes = {hub.id}
        positions = [(300, 100), (300, 300), (100, 300)]
    else:
        positions = [(100, 100), (300, 100), (300, 300), (100, 300)]
    for x, y in positions:
        assert scene._commit_shift_creation(QPointF(x, y))
    assert len(scene.graph.nodes) == 4
    assert len(scene.graph.edges) == edge_count


def test_append_preserves_manual_edge_deselection() -> None:
    get_qapplication()
    scene = GraphScene()
    scene.set_creation_mode("append")
    first, second = add_nodes(scene, [(100, 100), (100, 300)])
    scene.add_edge_visual(scene.graph.add_edge(first.id, second.id))
    scene.select_all()
    scene._handle_edge_selection(scene._edge_key(first.id, second.id), True)
    excluded_edges = scene.manually_deselected_edges.copy()

    assert scene._commit_shift_creation(QPointF(400, 200))
    assert scene.selected_nodes == {first.id, second.id}
    assert not scene.selected_edges
    assert scene.manually_deselected_edges == excluded_edges


def test_creation_buttons_switch_modes_without_creating_or_deselecting_nodes() -> None:
    app = get_qapplication()
    window = MainWindow()
    window.show()
    window.activateWindow()
    app.processEvents()
    assert [button.text() for button in window.creation_mode_buttons.values()] == [
        "Loop", "Web", "Points", "Append",
    ]
    assert window.creation_mode_buttons["loop"].isChecked()
    source = add_nodes(window.scene, [(100, 100)])[0]
    window.scene.selected_nodes = {source.id}
    before = window.graph.to_dict()

    for mode in ("web", "points", "append", "loop"):
        window.scene.handle_hover_position(QPointF(400, 200), Qt.KeyboardModifier.ShiftModifier)
        assert window.scene.shift_creation_preview_visible
        QTest.mouseClick(
            window.creation_mode_buttons[mode], Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.ShiftModifier,
        )
        assert window.scene.creation_mode == mode
        assert window.creation_mode_buttons[mode].isChecked()
        assert sum(button.isChecked() for button in window.creation_mode_buttons.values()) == 1
        assert window.scene.selected_nodes == {source.id}
        assert window.graph.to_dict() == before
        assert not window.scene.shift_creation_preview_visible
        assert window.canvas.hasFocus()

    window.scene.handle_hover_position(QPointF(400, 200), Qt.KeyboardModifier.ShiftModifier)
    QApplication.sendEvent(window.creation_controls, QEvent(QEvent.Type.Enter))
    assert not window.scene.shift_creation_preview_visible
    assert window.scene.last_cursor_position is None
    window.close()


def test_creation_controls_stay_anchored_and_remember_mode_when_disabled() -> None:
    app = get_qapplication()
    window = MainWindow()
    window.show()
    app.processEvents()
    window.creation_mode_buttons["append"].click()
    for width, height in [(1100, 700), (850, 550)]:
        window.resize(width, height)
        app.processEvents()
        position = window.creation_controls.pos()
        assert position.x() == 10
        assert window.creation_controls.geometry().bottom() == window.canvas.viewport().height() - 11
        window.canvas.horizontalScrollBar().setValue(120)
        window.canvas.verticalScrollBar().setValue(100)
        app.processEvents()
        assert window.creation_controls.pos() == position

    for tool in ("hand", "eraser"):
        window.set_canvas_mode(tool)
        assert not window.creation_controls.isEnabled()
        window.set_canvas_mode("select")
        assert window.creation_controls.isEnabled()
        assert window.scene.creation_mode == "append"

    window.matrix_type_combo.setCurrentIndex(window.matrix_type_combo.findData("nonbacktracking"))
    window.show_arc_view_checkbox.setChecked(True)
    assert not window.creation_controls.isEnabled()
    window.show_arc_view_checkbox.setChecked(False)
    assert window.creation_controls.isEnabled()
    assert window.creation_mode_buttons["append"].isChecked()
    window.close()
