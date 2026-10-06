import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from GraphTheoryTool.view.main_window import MainWindow


def test_canvas_controls_stay_at_their_anchors_when_resizing_and_panning() -> None:
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.show()
    panels = [
        window.label_controls, window.tool_controls,
        window.history_controls, window.creation_controls,
    ]

    for width, height in [(1100, 700), (850, 550)]:
        window.resize(width, height)
        app.processEvents()
        viewport = window.canvas.viewport()
        assert all(panel.parentWidget() is viewport for panel in panels)
        labels = window.label_controls.geometry()
        tools = window.tool_controls.geometry()
        history = window.history_controls.geometry()
        assert labels.topLeft() == QPoint(10, 10)
        assert tools.top() == 10
        assert abs(tools.center().x() - viewport.rect().center().x()) <= 1
        assert history.top() == 10
        assert history.right() == viewport.width() - 11
        assert not labels.intersects(tools)
        assert not tools.intersects(history)

        positions = [panel.pos() for panel in panels]
        window.canvas.horizontalScrollBar().setValue(150)
        window.canvas.verticalScrollBar().setValue(100)
        app.processEvents()
        assert [panel.pos() for panel in panels] == positions
    window.close()


def test_overlay_clicks_operate_controls_without_creating_graph_elements() -> None:
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.show()
    window.activateWindow()
    window.canvas.setFocus()
    app.processEvents()
    scene = window.scene
    assert scene._commit_shift_creation(QPointF(400, 300))
    snapshot = scene.graph.to_dict()
    selection = scene.selected_nodes.copy()

    # Even with creation armed, empty panel margins consume the click.
    for panel in (
        window.label_controls, window.tool_controls,
        window.history_controls, window.creation_controls,
    ):
        QTest.mouseClick(
            panel, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ShiftModifier,
            QPoint(1, 1),
        )
        assert scene.graph.to_dict() == snapshot
        assert scene.selected_nodes == selection

    QTest.mouseClick(
        window.show_labels_checkbox, Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.ShiftModifier,
    )
    assert window.show_labels_checkbox.isChecked()
    assert all(items["label"].isVisible() for items in scene.node_items.values())
    assert scene.graph.to_dict() == snapshot
    assert scene.selected_nodes == selection
    assert window.canvas.hasFocus()

    QTest.mouseClick(window.undo_button, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ShiftModifier)
    assert not scene.graph.nodes
    QTest.mouseClick(window.redo_button, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ShiftModifier)
    assert scene.graph.to_dict() == snapshot

    for mode in ("eraser", "hand", "select"):
        QTest.mouseClick(
            window.tool_buttons[mode], Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.ShiftModifier,
        )
        assert scene.mode == mode
        assert scene.graph.to_dict() == snapshot

    window.matrix_type_combo.setCurrentIndex(window.matrix_type_combo.findData("nonbacktracking"))
    window.show_arc_view_checkbox.setChecked(True)
    for control in (window.undo_button, window.redo_button, window.show_labels_checkbox):
        assert not control.isEnabled()
        QTest.mouseClick(control, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ShiftModifier)
        assert scene.graph.to_dict() == snapshot
    assert window.show_labels_checkbox.isChecked()
    window.close()


def test_empty_canvas_hint_is_centered_and_does_not_block_creation() -> None:
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.show()
    window.activateWindow()
    app.processEvents()
    hint = window.canvas.creation_hint
    assert hint.text() == "Hold Shift to create"
    assert hint.isVisible()
    assert hint.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    for width, height in [(1100, 700), (850, 550)]:
        window.resize(width, height)
        app.processEvents()
        center = window.canvas.viewport().rect().center()
        assert abs(hint.geometry().center().x() - center.x()) <= 1
        assert abs(hint.geometry().center().y() - center.y()) <= 1
        position = hint.pos()
        window.canvas.horizontalScrollBar().setValue(150)
        window.canvas.verticalScrollBar().setValue(100)
        app.processEvents()
        assert hint.pos() == position

    # A Shift hover preview is not a real node; the hint should remain visible.
    center = hint.geometry().center()
    window.scene.handle_hover_position(
        window.canvas.mapToScene(center), Qt.KeyboardModifier.ShiftModifier,
        Qt.MouseButton.NoButton,
    )
    app.processEvents()
    assert window.scene.shift_creation_preview_visible
    assert hint.isVisible()
    assert window.canvas.viewport().childAt(center) is not hint
    QTest.mouseClick(
        window.canvas.viewport(), Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.ShiftModifier, center,
    )
    app.processEvents()
    assert len(window.graph) == 1
    assert not hint.isVisible()

    window.undo()
    app.processEvents()
    assert len(window.graph) == 0
    assert hint.isVisible()
    window.redo()
    app.processEvents()
    assert not hint.isVisible()
    window.scene.select_all()
    window.delete_selected()
    app.processEvents()
    assert not window.graph.nodes
    assert hint.isVisible()
    window.close()


def test_empty_canvas_hint_is_hidden_in_read_only_arc_view() -> None:
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.show()
    app.processEvents()
    assert window.canvas.creation_hint.isVisible()
    window.matrix_type_combo.setCurrentIndex(window.matrix_type_combo.findData("nonbacktracking"))
    window.show_arc_view_checkbox.setChecked(True)
    app.processEvents()
    assert not window.canvas.creation_hint.isVisible()
    window.show_arc_view_checkbox.setChecked(False)
    app.processEvents()
    assert window.canvas.creation_hint.isVisible()
    window.close()
