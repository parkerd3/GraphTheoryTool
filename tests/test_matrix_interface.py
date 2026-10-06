import ast
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from GraphTheoryTool.matrices import matrix_to_mathematica, matrix_to_python, matrix_to_text
from GraphTheoryTool.view.main_window import MainWindow
from GraphTheoryTool.view.matrix_preview import MatrixPreviewTable


def get_qapplication() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_matrix_formatters_create_readable_and_nested_list_text() -> None:
    matrix = np.array([[0.0, 1.0], [1.0, 2.5]])

    assert matrix_to_text(matrix) == "0 1\n1 2.5"
    assert matrix_to_mathematica(matrix) == "{{0,1},{1,2.5}}"
    assert matrix_to_python(matrix) == "[[0,1],[1,2.5]]"
    assert ast.literal_eval(matrix_to_python(matrix)) == matrix.tolist()


@pytest.mark.parametrize(
    "matrix, mathematica, python",
    [(np.empty((0, 0)), "{}", "[]"), (np.empty((2, 0)), "{{},{}}", "[[],[]]")],
)
def test_nested_list_formats_preserve_empty_matrix_rows(matrix, mathematica, python) -> None:
    assert matrix_to_mathematica(matrix) == mathematica
    assert matrix_to_python(matrix) == python


@pytest.mark.parametrize("formatter", [matrix_to_mathematica, matrix_to_python])
def test_nested_list_formats_reject_non_matrix_inputs(formatter) -> None:
    with pytest.raises(ValueError, match="two-dimensional"):
        formatter(np.array([1, 2]))


def test_copy_matrix_format_switches_without_regeneration() -> None:
    get_qapplication()
    window = MainWindow()
    assert window.mathematica_radio.isChecked()
    assert not window.python_radio.isChecked()
    assert not window.copy_matrix_button.isEnabled()
    window.graph.add_node(100, 100)
    window.graph.add_node(300, 100)
    window.graph.add_edge(0, 1)
    window.generate_matrix()

    window.copy_matrix_button.click()
    assert QApplication.clipboard().text() == "{{0,1},{1,0}}"
    window.python_radio.click()
    assert window.python_radio.isChecked()
    assert not window.mathematica_radio.isChecked()
    window.copy_matrix_button.click()
    assert QApplication.clipboard().text() == "[[0,1],[1,0]]"

    window.matrix_type_combo.setCurrentIndex(window.matrix_type_combo.findData("degree"))
    window.generate_matrix()
    assert window.python_radio.isChecked()
    window.copy_matrix_button.click()
    assert QApplication.clipboard().text() == "[[1,0],[0,1]]"
    window.mathematica_radio.click()
    assert not window.python_radio.isChecked()
    window.copy_matrix_button.click()
    assert QApplication.clipboard().text() == "{{1,0},{0,1}}"
    window.close()


@pytest.mark.parametrize(
    "base, alternate, text",
    [("#ffffff", "#f0f0f0", "#000000"), ("#252525", "#303030", "#ffffff")],
)
def test_matrix_checkerboard_uses_widget_palette(base, alternate, text) -> None:
    get_qapplication()
    table = MatrixPreviewTable()
    palette = QPalette(table.palette())
    palette.setColor(QPalette.ColorRole.Base, QColor(base))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(alternate))
    palette.setColor(QPalette.ColorRole.Text, QColor(text))
    table.setPalette(palette)
    table.set_matrix(np.ones((6, 6)))

    assert table.item(0, 0).background().color() == QColor(base)
    assert table.item(4, 4).background().color() == QColor(base)
    assert table.item(0, 5).background().color() == QColor(alternate)
    assert table.item(5, 0).background().color() == QColor(alternate)
    assert table.item(5, 5).background().color() == QColor(base)
    assert table.palette().color(QPalette.ColorRole.Text) == QColor(text)
    # Don't override text/selection colors; let Qt's native delegate choose them.
    assert table.item(0, 0).foreground().style() == Qt.BrushStyle.NoBrush
    table.close()


def test_matrix_follows_application_palette_without_losing_contents() -> None:
    app = get_qapplication()
    original_palette = QPalette(app.palette())
    table = MatrixPreviewTable()
    matrix = np.arange(36).reshape(6, 6)
    table.set_matrix(matrix)
    table.horizontalHeaderItem(0).setToolTip("Arc 1: 1 -> 2")
    table.setCurrentCell(0, 1)
    table.show()
    try:
        for base, text in (("#ffffff", "#000000"), ("#252525", "#ffffff")):
            palette = QPalette(original_palette)
            palette.setColor(QPalette.ColorRole.Base, QColor(base))
            palette.setColor(QPalette.ColorRole.AlternateBase, QColor(base))
            palette.setColor(QPalette.ColorRole.Text, QColor(text))
            app.setPalette(palette)
            app.processEvents()

            background = table.item(0, 0).background().color()
            alternate = table.item(0, 5).background().color()
            assert background == QColor(base)
            assert alternate != background
            if text == "#000000":
                assert alternate.lightnessF() < background.lightnessF()
            else:
                assert alternate.lightnessF() > background.lightnessF()
            assert table.matrix_shape == (6, 6)
            assert table.toPlainText() == matrix_to_text(matrix)
            assert table.item(5, 5).text() == "35"
            assert table.horizontalHeaderItem(0).text() == "1"
            assert table.verticalHeaderItem(5).text() == "6"
            assert table.horizontalHeaderItem(0).toolTip() == "Arc 1: 1 -> 2"
            assert [(item.row(), item.column()) for item in table.selectedItems()] == [(0, 1)]
            QTest.keyClick(table, Qt.Key.Key_C, Qt.KeyboardModifier.ControlModifier)
            assert QApplication.clipboard().text() == "1"
    finally:
        app.setPalette(original_palette)
        table.close()


def test_main_window_generates_and_copies_adjacency_matrix() -> None:
    get_qapplication()
    window = MainWindow()
    assert [
        window.matrix_type_combo.itemData(index)
        for index in range(window.matrix_type_combo.count())
    ] == ["adjacency", "degree", "laplacian", "ihara", "nonbacktracking"]
    first = window.graph.add_node(100, 100)
    second = window.graph.add_node(300, 100)
    window.scene.add_node_visual(first)
    window.scene.add_node_visual(second)
    edge = window.graph.add_edge(first.id, second.id)
    window.scene.add_edge_visual(edge)

    window.matrix_button.click()

    assert window.matrix_preview.toPlainText() == "0 1\n1 0"
    assert window.matrix_preview.horizontalHeaderItem(0).text() == "1"
    assert window.matrix_preview.horizontalHeaderItem(1).text() == "2"
    assert window.matrix_preview.horizontalHeaderItem(2).text() == ""
    assert window.matrix_preview.verticalHeaderItem(0).text() == "1"
    assert window.matrix_preview.verticalHeaderItem(1).text() == "2"
    assert window.matrix_preview.verticalHeaderItem(2).text() == ""
    assert not window.matrix_preview.showGrid()
    assert window.matrix_preview.verticalHeader().width() == 30
    assert window.matrix_preview.horizontalHeader().height() == 30
    assert window.matrix_preview.sizePolicy().verticalPolicy().name == "Expanding"
    assert window.matrix_preview.item(0, 0).font().pointSize() >= 10
    assert (
        window.matrix_preview.item(0, 0).background().color()
        == window.matrix_preview.item(4, 4).background().color()
    )
    assert (
        window.matrix_preview.item(0, 0).background().color()
        != window.matrix_preview.item(0, 5).background().color()
    )
    assert window.matrix_dimensions_label.text() == "Dimensions: 2 × 2"
    assert window.copy_matrix_button.isEnabled()

    window.copy_matrix_button.click()
    assert QApplication.clipboard().text() == "{{0,1},{1,0}}"

    window.matrix_type_combo.setCurrentIndex(
        window.matrix_type_combo.findData("degree")
    )
    window.matrix_button.click()
    assert window.matrix_preview.toPlainText() == "1 0\n0 1"
    assert window.matrix_dimensions_label.text() == "Dimensions: 2 × 2"

    window.matrix_type_combo.setCurrentIndex(
        window.matrix_type_combo.findData("ihara")
    )
    window.matrix_button.click()
    assert window.matrix_preview.matrix_shape == (4, 4)
    assert window.matrix_dimensions_label.text() == "Dimensions: 4 × 4"

    window.show()
    window.matrix_preview.setCurrentCell(0, 0)
    window.matrix_preview.setFocus()
    QApplication.clipboard().clear()
    QTest.keyClick(
        window.matrix_preview,
        Qt.Key.Key_C,
        Qt.KeyboardModifier.ControlModifier,
    )
    assert QApplication.clipboard().text() == "0"
    window.close()
