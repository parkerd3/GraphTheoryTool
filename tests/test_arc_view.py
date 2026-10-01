import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QGraphicsView

from GraphTheoryTool.view.main_window import MainWindow


def test_arc_view_toggle_is_gated_restores_editor_and_cannot_edit_graph() -> None:
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    scene = window.scene
    first = scene.graph.add_node(100, 100)
    middle = scene.graph.add_node(350, 100)
    last = scene.graph.add_node(600, 100)
    for node in (first, middle, last):
        scene.add_node_visual(node)
    scene.add_edge_visual(scene.graph.add_edge(first.id, middle.id))
    scene.add_edge_visual(scene.graph.add_edge(middle.id, last.id))
    scene.select_all()
    window.show_labels_checkbox.setChecked(True)
    snapshot = scene.graph.to_dict()
    selected_nodes = set(scene.selected_nodes)
    selected_edges = set(scene.selected_edges)

    assert not window.show_arc_view_checkbox.isEnabled()
    window.matrix_type_combo.setCurrentIndex(window.matrix_type_combo.findData("nonbacktracking"))
    assert window.show_arc_view_checkbox.isEnabled()
    window.show_arc_view_checkbox.setChecked(True)

    assert window.canvas.scene() is window.arc_scene
    assert window.canvas.dragMode() == QGraphicsView.DragMode.ScrollHandDrag
    assert not window.tool_buttons["select"].isEnabled()
    assert not window.tool_buttons["eraser"].isEnabled()
    assert not window.show_labels_checkbox.isEnabled()
    assert not window.delete_action.isEnabled()
    assert not window.paste_action.isEnabled()
    assert not window.undo_action.isEnabled()
    assert len(window.arc_scene.arc_items) == 4
    assert [item.label.text() for item in window.arc_scene.arc_items] == ["1", "2", "3", "4"]
    assert window.arc_scene.arc_items[0].path().pointAtPercent(0.5).y() > 100
    assert window.arc_scene.arc_items[1].path().pointAtPercent(0.5).y() < 100
    assert len(window.arc_scene.arc_items[0].arrowhead.polygon()) == 3
    assert window.matrix_preview.matrix_shape == (4, 4)
    assert window.matrix_preview.horizontalHeaderItem(0).toolTip() == "Arc 1: 1 → 2"
    assert window.matrix_preview.verticalHeaderItem(1).toolTip() == "Arc 2: 2 → 1"
    window.copy_matrix_button.click()
    assert QApplication.clipboard().text() == "{{0,0,1,0},{0,0,0,0},{0,0,0,0},{0,1,0,0}}"

    window.show()
    window.canvas.setFocus()
    app.processEvents()
    QTest.mouseClick(
        window.canvas.viewport(), Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.ShiftModifier,
        window.canvas.mapFromScene(QPointF(200, 200)),
    )
    QTest.keyClick(window.canvas, Qt.Key.Key_Delete)
    QTest.keyClick(window.canvas, Qt.Key.Key_V, Qt.KeyboardModifier.ControlModifier)
    assert scene.graph.to_dict() == snapshot

    window.matrix_type_combo.setCurrentIndex(window.matrix_type_combo.findData("degree"))
    assert not window.show_arc_view_checkbox.isEnabled()
    assert not window.show_arc_view_checkbox.isChecked()
    assert window.canvas.scene() is scene
    assert window.canvas.dragMode() == QGraphicsView.DragMode.NoDrag
    assert window.show_labels_checkbox.isChecked()
    assert window.show_labels_checkbox.isEnabled()
    assert all(items["label"].isVisible() for items in scene.node_items.values())
    assert scene.selected_nodes == selected_nodes
    assert scene.selected_edges == selected_edges
    assert scene.graph.to_dict() == snapshot
    assert window.delete_action.isEnabled()
    window.matrix_button.click()
    assert window.matrix_preview.horizontalHeaderItem(0).toolTip() == ""
    window.close()


def test_arc_view_rebuild_after_deletion_uses_current_ids_and_labels() -> None:
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    deleted = window.scene.graph.add_node(0, 0)
    first = window.scene.graph.add_node(100, 100)
    second = window.scene.graph.add_node(300, 100)
    window.scene.graph.remove_node(deleted.id)
    window.scene.graph.add_edge(first.id, second.id)
    window.scene.rebuild_from_graph()
    window.matrix_type_combo.setCurrentIndex(window.matrix_type_combo.findData("nonbacktracking"))
    window.show_arc_view_checkbox.setChecked(True)
    assert window.arc_scene.arcs[0].source == first.id
    assert window.arc_scene.arcs[0].target == second.id
    assert window.arc_scene.arc_items[0].toolTip() == "Arc 1: 1 → 2"
    window.show_arc_view_checkbox.setChecked(False)
    window.scene.delete_edge(first.id, second.id)
    window.show_arc_view_checkbox.setChecked(True)
    assert not window.arc_scene.arc_items
    assert window.matrix_preview.matrix_shape == (0, 0)
    assert window.matrix_preview.horizontalHeaderItem(0).text() == ""
    assert window.matrix_preview.horizontalHeaderItem(0).toolTip() == ""
    window.copy_matrix_button.click()
    assert QApplication.clipboard().text() == "{}"
    window.close()
